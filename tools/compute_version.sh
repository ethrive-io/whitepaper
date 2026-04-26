#!/usr/bin/env bash
# compute_version.sh — emit the canonical version string for the
# current build context. Called by CI workflows before any package
# step; runnable locally to find out what version a checkout would
# build to right now.
#
# Output forms (per WS-0005 in ethrive-io/workspace):
#   - On a release tag (refs/tags/v…):     <tag>          e.g. 0.2.0
#   - Past a tag:                          <next-patch>-dev.<commits>+<sha>
#   - No tags exist yet (implicit v0.0.0): 0.0.1-dev.<commits>+<sha>
#
# Workflows calling this script must check out with `fetch-depth: 0`
# so `git describe` and `git rev-list` see the full history.
set -euo pipefail

if [[ "${GITHUB_REF:-}" =~ ^refs/tags/v ]]; then
    echo "${GITHUB_REF#refs/tags/v}"
    exit 0
fi

if LATEST=$(git describe --tags --abbrev=0 --match 'v*' 2>/dev/null); then
    BASE="${LATEST#v}"
    COMMITS=$(git rev-list "${LATEST}..HEAD" --count)
else
    # No tags yet — treat the implicit prior release as v0.0.0.
    BASE="0.0.0"
    COMMITS=$(git rev-list HEAD --count)
fi

SHA=$(git rev-parse --short HEAD)
NEXT=$(awk -F. -v OFS=. '{$3++; print}' <<< "$BASE")
echo "${NEXT}-dev.${COMMITS}+${SHA}"
