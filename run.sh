#!/bin/bash
# ****************************
# *** AUTHOR/MAINTAINER ***
#    MASON CLEMONS | 2026
#
# *** ABOUT ***
# Runs the Cigar Scanner humidor export inside the uv-managed environment,
# making sure uv, the playwright package, and the Chromium browser binary are
# all present first.
#
# NOTE: This intentionally does NOT delete .cs_profile on every run. That
# directory keeps you logged in between runs so you don't have to clear a
# Cloudflare challenge and log in each time. Only wipe it when the session is
# actually broken: run with  ./run.sh --reset
# ****************************

set -euo pipefail

# Run from this script's own directory, so it works no matter where you invoke
# it from. Handles spaces in the path (e.g. "Tobacco Town/get-humidor").
cd "$(dirname "${BASH_SOURCE[0]}")"

SCRIPT="main.py"

# --- optional reset flag -------------------------------------------------
RESET=0
if [[ "${1:-}" == "--reset" ]]; then
  RESET=1
  shift
fi

# --- ensure uv is available ----------------------------------------------
if ! command -v uv &> /dev/null; then
  echo "uv is not installed. Install it from https://docs.astral.sh/uv/ then re-run."
  echo "  (e.g.  brew install uv   or   curl -LsSf https://astral.sh/uv/install.sh | sh )"
  exit 1
fi

# --- ensure the python source exists -------------------------------------
if [[ ! -f "$SCRIPT" ]]; then
  echo "Error: $SCRIPT not found in the current directory."
  exit 1
fi

# --- ensure playwright (package) is installed in the project -------------
if ! uv run python -c "import playwright" &> /dev/null; then
  echo "Installing playwright package..."
  uv add playwright
fi

# --- ensure the Chromium browser binary is installed ---------------------
# This is a separate step from the pip package. It's cheap to re-run; if the
# browser is already present it just confirms and exits.
echo "Ensuring Chromium browser is installed..."
uv run playwright install chromium

# --- only delete the saved profile when explicitly asked -----------------
if [[ "$RESET" -eq 1 ]]; then
  if [[ -d ".cs_profile" ]]; then
    echo "Reset requested: deleting .cs_profile (you'll log in again)..."
    rm -rf .cs_profile
  fi
fi

# --- run the exporter ----------------------------------------------------
echo "RUNNING CIGARSCANNER.COM HUMIDOR EXPORT..."
if uv run "$SCRIPT" export --dump-json; then
  echo "Done."
else
  echo "Error: $SCRIPT failed to run."
  exit 1
fi
