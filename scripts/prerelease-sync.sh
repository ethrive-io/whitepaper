#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# prerelease-sync.sh — merge THIS repo's `main` into THIS repo's `next` preview
# branch, and prove that main's release-please state did not overwrite next's
# on the way in.
#
# ONE REPO, NO WORKSPACE. Every ethrive repo that carries a `next` branch also
# carries this script, exactly the way it carries its own `build.sh`,
# `test.sh` and `coverage.sh` — so a standalone clone can sync its own preview
# lane with no workspace checked out anywhere on the machine. Without it the
# only thing a standalone clone could do is `git checkout next && git merge
# main`, which is the one operation that silently breaks the RC line (see
# below). The workspace's `scripts/prerelease-sync.sh` is a thin loop over
# these per-repo scripts; the workspace keeps its own copy under the name
# `scripts/prerelease-sync-repo.sh`, because in that one repo the plain name
# belongs to the sweep. Every copy is byte-identical.
#
# THE BUG CLASS. `next` differs from `main` in exactly ONE tracked file:
# release-please-config.json, where `next` additionally carries
#
#     "versioning": "prerelease",  "prerelease": true,  "prerelease-type": "rc"
#
# Those keys are the ONLY thing that makes a cut on `next` an RC. Lose them and
# release-please does not error, does not warn and does not skip — it computes a
# PLAIN STABLE VERSION from the preview branch and publishes the tag. Verified
# against release-please 17.11.1: with `versioning` unset the numbers `next`
# proposes are byte-identical to main's, because `"prerelease": true` alone only
# ticks the GitHub Release's "pre-release" checkbox; the version ARITHMETIC is
# selected by `versioning`. So the failure is a wrong release with a green run
# and nothing anywhere to read — the same "reports success while doing nothing"
# shape the verification audit kept finding, and the reason this is a gate.
#
# `main` tracks release-please-config.json too, so an ordinary `git merge main`
# can carry main's copy over next's and erase all three keys. The same applies
# to every other file release-please WRITES per-branch: the manifest is next's
# anchor for "which RC came last", and if main's `0.1.0` lands on top of next's
# `0.1.0-rc1` the rc counter restarts from the wrong base. This script therefore
# pins that set to next's side on every merge (see RELEASE_STATE_FILES), then
# re-asserts the config keys and FAILS LOUDLY if it cannot restore them.
#
# NEVER REBASE `next`. release-please anchors the RC line on tags cut from this
# branch. Rebasing rewrites every SHA, so those tags point at commits no longer
# in the branch's history and release-please loses the anchor — it then proposes
# a version computed from the wrong base. It would also mean force-pushing a
# branch that carries published tags, which invariant #5 forbids outright. This
# script only ever runs `git merge --no-ff`; it passes no `--force` and no
# `--rebase`, it proves after the merge that next's previous tip is still an
# ancestor of the new tip (append-only), and it REFUSES a repo whose local
# `next` has already been rewritten relative to `origin/next`, because syncing
# that one could only be completed by a force-push.
#
# THE MODEL IS TRUNK-AND-PREVIEW, NOT MERGE-BACK. `main` is the trunk; work
# lands there and stable releases are cut there. `next` is a permanent
# DOWNSTREAM preview lane that only ever RECEIVES merges. It never merges back,
# so there is no promote step and no expectation that the branches converge —
# their manifests are SUPPOSED to diverge. See the workspace CLAUDE.md
# "The `next` prerelease lane" subsection.
#
# This script never pushes. It prints the push command and leaves it to you.
#
# Usage:
#   bash scripts/prerelease-sync.sh              # sync this repo
#   bash scripts/prerelease-sync.sh --preflight  # only check that it COULD sync
#   bash scripts/prerelease-sync.sh --help
#
# Exit codes:
#   0  synced, or already up to date
#   1  refused, conflicted, or could not restore the prerelease config
#   2  bad arguments
#   3  nothing to sync (this repo has no `next` — or no `main` — branch)
set -euo pipefail

# SELF-PROTECTION. This script checks out `next` in the very repo it lives in,
# so the file on disk changes underneath the running interpreter — and bash
# reads a script INCREMENTALLY from disk. The moment the two branches hold
# different versions of this file (they will, the first time someone edits it on
# `main` and syncs before pushing) it would execute a spliced hybrid of both
# versions; on the first sync of a repo that has this script only on `main` the
# file vanishes from the working tree entirely. Re-exec from a private copy so
# the file on disk is free to change or disappear.
if [[ -z "${ETHRIVE_PRERELEASE_SYNC_REEXEC:-}" ]]; then
    _here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if ! _root="$(git -C "${_here}" rev-parse --show-toplevel 2>/dev/null)"; then
        printf 'error: %s is not inside a git work tree — nothing to sync.\n' "${_here}" >&2
        exit 1
    fi
    ETHRIVE_PRERELEASE_SYNC_ROOT="${_root}"
    export ETHRIVE_PRERELEASE_SYNC_ROOT
    export ETHRIVE_PRERELEASE_SYNC_REEXEC=1
    _self_copy="$(mktemp "${TMPDIR:-/tmp}/prerelease-sync.XXXXXX")"
    cp "${BASH_SOURCE[0]}" "${_self_copy}"
    _status=0
    bash "${_self_copy}" "$@" || _status=$?
    rm -f "${_self_copy}"
    exit "${_status}"
fi

REPO_ROOT="${ETHRIVE_PRERELEASE_SYNC_ROOT}"
REPO_NAME="$(basename "${REPO_ROOT}")"

TRUNK_BRANCH="main"
PREVIEW_BRANCH="next"

# Files release-please WRITES, per branch. Each is branch-owned STATE, not
# shared source: next's manifest says which RC came last and main's says which
# stable release came last, so main's copy must never win a merge into next. If
# main's `0.1.0` landed on top of next's `0.1.0-rc1`, next's rc counter would
# restart from the wrong base. Pinning them is a DELIBERATE, ANNOUNCED
# resolution — every pin is printed — not the script quietly resolving a source
# conflict, which it refuses to do. Without it, every sync after a stable
# release would raise the same mechanical conflict in the same files with the
# same correct answer every time.
RELEASE_STATE_FILES=(
    ".release-please-manifest.json"
    "CHANGELOG.md"
    "version.txt"
)

# release-please-config.json is deliberately NOT in that list. It is mostly
# SHARED configuration — changelog sections, the pre-v1 flags, the PR title
# pattern — that should keep flowing from main to next, and only a handful of
# keys are branch-specific. So it merges normally, and if it conflicts the
# resolution is main's side, because assert_prerelease_config() below then
# re-derives every next-specific key from scratch. That function IS the
# definition of how next's config differs; nothing branch-specific is left to
# survive a merge on its own.
CONFIG_FILE="release-please-config.json"

# ---------------------------------------------------------------------------
# Self-contained plumbing. A standalone clone has no workspace, so this script
# sources nothing: the log helpers and the work-count line are inlined, and it
# stays bash-3.2-clean so a stock macOS shell can run it.
# ---------------------------------------------------------------------------
if [[ -t 1 ]]; then
    _C_RED=$'\033[0;31m'
    _C_GREEN=$'\033[0;32m'
    _C_YELLOW=$'\033[0;33m'
    _C_BLUE=$'\033[0;34m'
    _C_RESET=$'\033[0m'
else
    _C_RED=""
    _C_GREEN=""
    _C_YELLOW=""
    _C_BLUE=""
    _C_RESET=""
fi

log_info()    { printf '%s[info]%s %s\n'     "${_C_BLUE}"   "${_C_RESET}" "$*"; }
log_success() { printf '%s[ok]%s %s\n'       "${_C_GREEN}"  "${_C_RESET}" "$*"; }
log_warn()    { printf '%s[warn]%s %s\n' >&2 "${_C_YELLOW}" "${_C_RESET}" "$*"; }
log_error()   { printf '%s[error]%s %s\n' >&2 "${_C_RED}"   "${_C_RESET}" "$*"; }

# The work-count contract (scripts/gate_report.sh in the workspace, inlined
# here). A gate that checked nothing and exited 0 is indistinguishable from a
# gate that checked everything and found nothing wrong, so the run ends with
#
#   GATE: <name> checked=<n> required=<m> skipped=<k> filtered=<f> total_on_disk=<t>
#
# as its LAST line on stdout, and checked=0 is ALWAYS a failure. The
# denominator here is 1: this script's whole scope is one repo.
GATE_CHECKED=0
GATE_SKIPPED=0
GATE_REASONS=""

gate_check() { GATE_CHECKED=$((GATE_CHECKED + 1)); }

gate_skip() {
    GATE_SKIPPED=$((GATE_SKIPPED + 1))
    if [[ -n "${GATE_REASONS}" ]]; then
        GATE_REASONS="${GATE_REASONS},$1:1"
    else
        GATE_REASONS="$1:1"
    fi
    printf '[skip] %s — %s\n' "$1" "$2" >&2
}

gate_finish() {
    local line status=0
    line="GATE: prerelease_sync checked=${GATE_CHECKED} required=1"
    line="${line} skipped=${GATE_SKIPPED} filtered=0 total_on_disk=1"
    if [[ -n "${GATE_REASONS}" ]]; then
        line="${line} reasons=${GATE_REASONS}"
    fi
    if (( GATE_CHECKED == 0 )); then
        printf 'GATE FAILURE prerelease_sync: checked=0 — %s was not asserted against, so a green exit would mean nothing\n' \
            "${REPO_NAME}" >&2
        status=1
    fi
    # In sweep mode the workspace loop emits the aggregate GATE line; a second
    # one per repo would make the LAST-line contract ambiguous.
    if [[ -z "${RESULT_FILE}" ]]; then
        printf '%s\n' "${line}"
    fi
    return "${status}"
}

usage() {
    # Print the header comment block (from line 3 to the first non-comment
    # line) with its leading '# ' stripped. Marker-free, so it cannot drift.
    awk 'NR < 3 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "${BASH_SOURCE[0]}"
}

# ---------------------------------------------------------------------------
# Arguments.
# ---------------------------------------------------------------------------
PREFLIGHT_ONLY=0
# Set by the workspace sweep: a file to record this repo's outcome in, and the
# signal that an outer loop owns the summary, the push hints and the GATE line.
RESULT_FILE=""

while (( $# > 0 )); do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --preflight)
            PREFLIGHT_ONLY=1
            ;;
        --result-file)
            if (( $# < 2 )); then
                log_error "--result-file needs a path"
                exit 2
            fi
            RESULT_FILE="$2"
            shift
            ;;
        *)
            log_error "unknown argument: $1"
            usage >&2
            exit 2
            ;;
    esac
    shift
done

# record_result <key> <value> — append one field to the sweep's result file.
record_result() {
    [[ -n "${RESULT_FILE}" ]] || return 0
    printf '%s=%s\n' "$1" "$2" >>"${RESULT_FILE}"
}

# ---------------------------------------------------------------------------
# The config assertion. Reads this repo's release-please-config.json plus its
# .release-please-manifest.json, repairs the prerelease keys if a merge dropped
# them, and reports what it did.
#
# Exit 0 = already correct, 10 = repaired, 1 = cannot repair (fail loudly).
# ---------------------------------------------------------------------------
assert_prerelease_config() {
    local repo_dir="$1"
    python3 - "${repo_dir}" <<'PYEOF'
import json
import os
import sys

repo = sys.argv[1]
config_path = os.path.join(repo, "release-please-config.json")
manifest_path = os.path.join(repo, ".release-please-manifest.json")

# The three keys that make a cut on `next` an RC instead of a stable release.
# `versioning` selects the arithmetic, `prerelease` keeps the suffix on the
# computed version AND flags the GitHub Release, `prerelease-type` supplies the
# suffix when the base version has none.
REQUIRED = {
    "versioning": "prerelease",
    "prerelease": True,
    "prerelease-type": "rc",
}
# Pinned bootstrap for the very first RC. `release-type: simple` inherits the
# base strategy's initial version of 1.0.0, so a first cut with nothing released
# and no `initial-version` would tag v1.0.0 off the preview branch. Unlike
# `release-as` this is NOT sticky: it applies only while nothing has been
# released, which is exactly the condition below.
INITIAL_VERSION = "0.1.0-rc1"

try:
    with open(config_path) as fh:
        raw = fh.read()
    config = json.loads(raw)
except FileNotFoundError:
    print("cannot: release-please-config.json not found", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as exc:
    print("cannot: release-please-config.json is not valid JSON: %s" % exc, file=sys.stderr)
    sys.exit(1)

repaired = []

for key, want in REQUIRED.items():
    if config.get(key) != want:
        config[key] = want
        repaired.append("%s=%s" % (key, json.dumps(want)))

packages = config.get("packages")
if not isinstance(packages, dict) or "." not in packages:
    print("cannot: config has no packages['.'] entry to correct", file=sys.stderr)
    sys.exit(1)
root = packages["."]

# `release-as` short-circuits the versioning strategy entirely (it is returned
# before the strategy is ever consulted), so main's bootstrap pin arriving here
# would freeze every RC at one version. It must not exist on this branch.
if "release-as" in root:
    del root["release-as"]
    repaired.append("packages['.'].release-as removed")

released = None
try:
    with open(manifest_path) as fh:
        released = json.load(fh).get(".")
except (OSError, json.JSONDecodeError):
    released = None

# Self-retiring: once this branch has actually released something, the manifest
# is the anchor and the bootstrap is irrelevant.
if released in (None, "0.0.0") and "initial-version" not in root:
    root["initial-version"] = INITIAL_VERSION
    repaired.append("packages['.'].initial-version=%s" % INITIAL_VERSION)

if not repaired:
    sys.exit(0)

out = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
try:
    with open(config_path, "w") as fh:
        fh.write(out)
except OSError as exc:
    print("cannot: could not write release-please-config.json: %s" % exc, file=sys.stderr)
    sys.exit(1)

for item in repaired:
    print(item)
sys.exit(10)
PYEOF
}

# ---------------------------------------------------------------------------
# Pre-flight. Every problem that should stop this repo is found BEFORE the
# merge starts, so a refusal never leaves a half-merged tree. The workspace
# sweep runs this over EVERY repo before it merges ANY of them, which is what
# keeps a dirty repo #9 from stranding repos #1-8 mid-sweep.
#
# Prints its reason on stderr. Returns 0 = ready, 1 = blocked, 3 = nothing to
# sync (no `next`, or no `main`).
# ---------------------------------------------------------------------------
preflight() {
    # The prerelease-key assertion below is python3. Without it the merge could
    # still run but the keys could not be verified — which is the one thing
    # this script exists to guarantee, so it is a refusal, not a warning.
    if ! command -v python3 >/dev/null 2>&1; then
        printf '%s: python3 is required to verify the prerelease config and is not installed\n' \
            "${REPO_NAME}" >&2
        return 1
    fi
    if ! git -C "${REPO_ROOT}" show-ref --verify --quiet "refs/heads/${PREVIEW_BRANCH}"; then
        printf '%s: no local %s branch — nothing to sync\n' "${REPO_NAME}" "${PREVIEW_BRANCH}" >&2
        return 3
    fi
    if ! git -C "${REPO_ROOT}" show-ref --verify --quiet "refs/heads/${TRUNK_BRANCH}"; then
        printf '%s: no local %s branch — nothing to sync from\n' "${REPO_NAME}" "${TRUNK_BRANCH}" >&2
        return 3
    fi
    if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]]; then
        printf '%s: working tree is dirty — commit or stash first (git -C %s status)\n' \
            "${REPO_NAME}" "${REPO_ROOT}" >&2
        return 1
    fi
    if [[ -e "${REPO_ROOT}/.git/MERGE_HEAD" || -d "${REPO_ROOT}/.git/rebase-merge" \
        || -d "${REPO_ROOT}/.git/rebase-apply" ]]; then
        printf '%s: a merge or rebase is already in progress — finish or abort it first\n' \
            "${REPO_NAME}" >&2
        return 1
    fi
    if ! git -C "${REPO_ROOT}" symbolic-ref --quiet HEAD >/dev/null 2>&1; then
        printf '%s: HEAD is detached — check out a branch first\n' "${REPO_NAME}" >&2
        return 1
    fi
    # A local `next` that is not a descendant of its own remote has been
    # rewritten. Continuing would produce a branch that can only be published
    # with a force-push, which invariant #5 forbids and which would strand every
    # RC tag already cut from the old history.
    if git -C "${REPO_ROOT}" show-ref --verify --quiet "refs/remotes/origin/${PREVIEW_BRANCH}"; then
        if ! git -C "${REPO_ROOT}" merge-base --is-ancestor \
            "origin/${PREVIEW_BRANCH}" "${PREVIEW_BRANCH}" 2>/dev/null; then
            printf "%s: local '%s' is not a descendant of 'origin/%s' — it looks REBASED or reset. Syncing it would require a force-push, which is forbidden. Recover the original branch instead; never rebase '%s'.\n" \
                "${REPO_NAME}" "${PREVIEW_BRANCH}" "${PREVIEW_BRANCH}" "${PREVIEW_BRANCH}" >&2
            return 1
        fi
    fi
    return 0
}

preflight_status=0
preflight || preflight_status=$?

if (( PREFLIGHT_ONLY == 1 )); then
    # A silent 0 would be the same "reports success while checking nothing"
    # shape this script exists to prevent, so say what passed.
    if (( preflight_status == 0 )); then
        log_info "${REPO_NAME}: ready to sync ${TRUNK_BRANCH} -> ${PREVIEW_BRANCH}"
    fi
    exit "${preflight_status}"
fi

if (( preflight_status == 3 )); then
    gate_skip no-preview-branch "${REPO_NAME} — no local '${PREVIEW_BRANCH}'/'${TRUNK_BRANCH}' branch pair"
    record_result status skipped
    gate_finish || true
    exit 3
fi
if (( preflight_status != 0 )); then
    log_error "${REPO_NAME}: refusing to sync — see the reason above. Nothing was merged."
    record_result status blocked
    gate_finish || true
    exit 1
fi

# ---------------------------------------------------------------------------
# The sync.
# ---------------------------------------------------------------------------
gate_check 1

original_branch="$(git -C "${REPO_ROOT}" symbolic-ref --short HEAD)"
before_next="$(git -C "${REPO_ROOT}" rev-parse "${PREVIEW_BRANCH}")"
trunk_sha="$(git -C "${REPO_ROOT}" rev-parse "${TRUNK_BRANCH}")"

git -C "${REPO_ROOT}" checkout --quiet "${PREVIEW_BRANCH}"

merged_anything=0
if git -C "${REPO_ROOT}" merge-base --is-ancestor "${trunk_sha}" "${before_next}"; then
    # Idempotent path: `main` is already contained in `next`. Still fall
    # through to the config assertion — a run that verifies nothing is worse
    # than no run at all.
    :
else
    merged_anything=1
    merge_status=0
    # --no-ff keeps every sync a visible, revertible merge commit and keeps
    # the history append-only. --no-commit hands us the index so the
    # release-state pin lands INSIDE the merge commit rather than as a
    # follow-up that a bisect could land between.
    git -C "${REPO_ROOT}" merge --no-ff --no-commit "${TRUNK_BRANCH}" >/dev/null 2>&1 || merge_status=$?

    # Pin the branch-owned release-state files back to next's side.
    pinned=()
    for f in "${RELEASE_STATE_FILES[@]}"; do
        if git -C "${REPO_ROOT}" cat-file -e "${before_next}:${f}" 2>/dev/null; then
            if ! git -C "${REPO_ROOT}" diff --quiet "${before_next}" -- "${f}" 2>/dev/null \
                || git -C "${REPO_ROOT}" ls-files --unmerged -- "${f}" | grep -q .; then
                git -C "${REPO_ROOT}" checkout "${before_next}" -- "${f}"
                git -C "${REPO_ROOT}" add -- "${f}"
                pinned+=("${f}")
            fi
        fi
    done
    if (( ${#pinned[@]} > 0 )); then
        log_info "${REPO_NAME}: kept ${PREVIEW_BRANCH}'s copy of ${pinned[*]}"
    fi

    # A conflict in the shared config resolves to main's side; the assertion
    # below re-derives next's keys, so nothing branch-specific is lost.
    if git -C "${REPO_ROOT}" ls-files --unmerged -- "${CONFIG_FILE}" | grep -q .; then
        git -C "${REPO_ROOT}" checkout --theirs -- "${CONFIG_FILE}"
        git -C "${REPO_ROOT}" add -- "${CONFIG_FILE}"
        log_info "${REPO_NAME}: took ${TRUNK_BRANCH}'s ${CONFIG_FILE} (prerelease keys are re-derived below)"
    fi

    # Any conflict that is NOT release-state is a real source conflict. Stop
    # here and leave the tree exactly as it is for a human to resolve.
    unmerged="$(git -C "${REPO_ROOT}" diff --name-only --diff-filter=U)"
    if [[ -n "${unmerged}" ]]; then
        log_error "${REPO_NAME}: CONFLICT merging ${TRUNK_BRANCH} into ${PREVIEW_BRANCH}"
        while IFS= read -r path; do
            printf '    %s\n' "${path}" >&2
        done <<<"${unmerged}"
        log_error "${REPO_NAME}: left mid-merge in ${REPO_ROOT} (on branch ${PREVIEW_BRANCH}) — resolve it by hand."
        record_result status conflict
        record_result conflicts "${unmerged//$'\n'/, }"
        if [[ -z "${RESULT_FILE}" ]]; then
            echo >&2
            log_error "Resolve the paths above, then finish the merge with 'git commit -s'."
            log_error "Do NOT resolve a conflict by rebasing '${PREVIEW_BRANCH}'."
        fi
        gate_finish || true
        exit 1
    fi

    if (( merge_status != 0 )) && [[ ! -e "${REPO_ROOT}/.git/MERGE_HEAD" ]]; then
        log_error "${REPO_NAME}: git merge failed and left no merge to finish"
        record_result status conflict
        record_result conflicts "<merge failed>"
        gate_finish || true
        exit 1
    fi
fi

# Re-assert the prerelease keys. This runs on EVERY run, including the
# already-up-to-date path, so the guarantee holds even when there was nothing
# to merge.
assert_status=0
assert_output="$(assert_prerelease_config "${REPO_ROOT}" 2>&1)" || assert_status=$?

repaired=0
if (( assert_status == 1 )); then
    log_error "${REPO_NAME}: CANNOT restore the prerelease config — ${assert_output}"
    log_error "${REPO_NAME}: refusing to leave '${PREVIEW_BRANCH}' in a state that would cut a STABLE release."
    record_result status error
    gate_finish || true
    exit 1
fi
if (( assert_status == 10 )); then
    repaired=1
    log_warn "${REPO_NAME}: the merge dropped prerelease settings — RESTORED: ${assert_output//$'\n'/; }"
    git -C "${REPO_ROOT}" add -- "${CONFIG_FILE}"
fi

synced=0
if (( merged_anything == 1 )); then
    git -C "${REPO_ROOT}" commit --quiet -s -F - <<EOF
chore(release): merge ${TRUNK_BRANCH} into ${PREVIEW_BRANCH}

Downstream sync of the ${PREVIEW_BRANCH} preview lane. Release-please state
files stay at ${PREVIEW_BRANCH}'s version; the RC line's anchor is this
branch's own manifest.
EOF
    # Append-only proof: the pre-merge tip must still be reachable. If this
    # ever fails, something rewrote history and the RC tags are stranded.
    after_next="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
    if ! git -C "${REPO_ROOT}" merge-base --is-ancestor "${before_next}" "${after_next}"; then
        log_error "${REPO_NAME}: post-merge HEAD does not contain the pre-merge '${PREVIEW_BRANCH}' tip — history was rewritten. Refusing to continue."
        record_result status error
        gate_finish || true
        exit 1
    fi
    synced=1
    log_success "${REPO_NAME}: merged ${TRUNK_BRANCH} into ${PREVIEW_BRANCH}"
else
    if (( repaired == 1 )); then
        git -C "${REPO_ROOT}" commit --quiet -s -m \
            "fix(release): restore the ${PREVIEW_BRANCH} prerelease config"
        synced=1
        log_success "${REPO_NAME}: nothing to merge, but the prerelease config needed repair"
    else
        log_info "${REPO_NAME}: already up to date"
    fi
fi

git -C "${REPO_ROOT}" checkout --quiet "${original_branch}"

if (( synced == 1 )); then
    record_result status synced
else
    record_result status already
fi
record_result merged "${merged_anything}"
record_result repaired "${repaired}"

# ---------------------------------------------------------------------------
# Summary. Owned by the workspace sweep when it is driving.
# ---------------------------------------------------------------------------
if [[ -z "${RESULT_FILE}" ]]; then
    echo
    printf '%s\n' "----- prerelease-sync summary (${REPO_NAME}) -----"
    printf '  %-22s %s\n' "synced:" "${synced}"
    printf '  %-22s %s\n' "already up to date:" "$(( 1 - synced ))"
    printf '  %-22s %s\n' "conflicted:" "0"
    if (( repaired == 1 )); then
        printf '  %-22s %s\n' "config repaired:" "1"
    fi

    if (( synced == 1 )); then
        echo
        printf '%s\n' "This script does not push. Publish the synced branch with:"
        printf '  git -C %s push -u origin %s\n' "${REPO_ROOT}" "${PREVIEW_BRANCH}"
        echo
        printf '%s\n' "Pushing is what starts the RC: release-please then opens the RC pull"
        printf '%s\n' "request on '${PREVIEW_BRANCH}', and MERGING that PR is what cuts the tag."
    fi
    echo
fi

status=0
gate_finish || status=$?
exit "${status}"
