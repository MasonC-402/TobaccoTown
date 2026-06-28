#!/usr/bin/env bash
# Copies the uv-managed Python 3.12 binary into TobaccoTown.app so Finder
# can launch the app with the correct menu bar name.
set -e

PYTHON=$(uv run python -c "import sys; print(sys.executable)")
DEST="TobaccoTown.app/Contents/MacOS/TobaccoTown"

echo "Using Python: $PYTHON"
cp "$PYTHON" "$DEST"
chmod +x "$DEST"
xattr -cr TobaccoTown.app
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
    -f TobaccoTown.app 2>/dev/null || true

echo "Done. Double-click TobaccoTown.app to launch."
