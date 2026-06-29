#!/usr/bin/env bash
# Creates TobaccoTown.app so Finder / Spotlight can launch it.
# The launcher script resolves paths at runtime, so no binary copy is needed.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
MACOS="$SCRIPT_DIR/TobaccoTown.app/Contents/MacOS"
LAUNCHER="$MACOS/TobaccoTown"
PLIST="$SCRIPT_DIR/TobaccoTown.app/Contents/Info.plist"

# --- ensure uv is available ----------------------------------------------
if ! command -v uv &>/dev/null; then
    echo "Error: uv is not installed. Install it first, then re-run this script."
    echo "  brew install uv   or   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# --- set up the Python environment ---------------------------------------
echo "Setting up Python environment..."
cd "$SCRIPT_DIR"
uv sync

# --- build the .app bundle -----------------------------------------------
mkdir -p "$MACOS"

cat > "$LAUNCHER" << 'EOF'
#!/bin/bash
MACOS="$(cd "$(dirname "$0")" && pwd -P)"
PROJECT="$(dirname "$(dirname "$(dirname "$MACOS")")")"
PYTHON="$PROJECT/.venv/bin/python3"

if [[ ! -x "$PYTHON" ]]; then
    osascript -e 'display alert "TobaccoTown" message "Python environment not found.\n\nRun build_app.sh in Terminal to set up the app." as critical'
    exit 1
fi

exec "$PYTHON" "$PROJECT/app.py"
EOF

cat > "$PLIST" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>TobaccoTown</string>
    <key>CFBundleIdentifier</key>
    <string>com.tobaccotown.app</string>
    <key>CFBundleName</key>
    <string>TobaccoTown</string>
    <key>CFBundleDisplayName</key>
    <string>TobaccoTown</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
EOF

chmod +x "$LAUNCHER"
xattr -cr "$SCRIPT_DIR/TobaccoTown.app"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
    -f "$SCRIPT_DIR/TobaccoTown.app" 2>/dev/null || true

echo "Done. Double-click TobaccoTown.app to launch."
