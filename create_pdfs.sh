#!/usr/bin/env bash
#
# Build the ethrive whitepaper PDFs from TECHNICAL.md and NON_TECHNICAL.md.
#
# Usage:
#   ./create_pdfs.sh                        # both PDFs to /tmp
#   ./create_pdfs.sh OUTPUT_DIR             # both PDFs to OUTPUT_DIR
#   ./create_pdfs.sh --only TECHNICAL       # build one
#   ./create_pdfs.sh --version v0.1.0 --date "April 2026"
#                                           # stamp the cover
#
# All flags after the optional output dir are forwarded to
# tools/pdf/create_pdfs.py.
#
# On first run, sets up a Python virtualenv in .venv-pdf/ and
# installs WeasyPrint. Subsequent runs reuse it.
#
# External dependencies:
#   - python3 (any 3.10+)
#   - pandoc  (apt: pandoc; brew: pandoc)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/tools/pdf/create_pdfs.py"
VENV="$HERE/.venv-pdf"
MARKER="$VENV/.deps-installed"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: '$1' is required but not found on PATH." >&2
    echo "Install it and retry. (Homebrew: 'brew install $1'; apt: 'sudo apt-get install $1'.)" >&2
    exit 1
  fi
}
need python3
need pandoc

if [ ! -d "$VENV" ]; then
  echo "Creating Python virtualenv at $VENV ..."
  python3 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

if [ ! -f "$MARKER" ]; then
  echo "Installing Python dependencies into virtualenv ..."
  pip install --quiet --upgrade pip
  pip install --quiet weasyprint
  touch "$MARKER"
fi

exec python3 "$SCRIPT" "$@"
