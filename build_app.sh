#!/usr/bin/env bash
# Sets up TobaccoTown.app so Finder / Spotlight can launch it.
# The launcher script resolves paths at runtime, so no binary copy is needed.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
LAUNCHER="$SCRIPT_DIR/TobaccoTown.app/Contents/MacOS/TobaccoTown"

chmod +x "$LAUNCHER"
xattr -cr "$SCRIPT_DIR/TobaccoTown.app"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
    -f "$SCRIPT_DIR/TobaccoTown.app" 2>/dev/null || true

echo "Done. Double-click TobaccoTown.app to launch."
