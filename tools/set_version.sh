#!/usr/bin/env bash
# set_version.sh — apply a version string to the local manifest.
#
# The whitepaper repo has no language manifest field (the git tag IS
# the canonical version for this repo type). This script is a
# no-op kept for uniformity with the rest of the ecosystem.
#
# Usage:
#   ./tools/set_version.sh "$(./tools/compute_version.sh)"
set -euo pipefail
if [ $# -ne 1 ]; then
    echo "usage: $0 <version>" >&2
    exit 2
fi
echo "[whitepaper] no manifest to update; version '$1' is used only for the artefact filename."
