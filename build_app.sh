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
RESOURCES="$SCRIPT_DIR/TobaccoTown.app/Contents/Resources"
mkdir -p "$MACOS" "$RESOURCES"

# --- build the icon ------------------------------------------------------
if [[ -f "$SCRIPT_DIR/assets/icon.png" ]]; then
    echo "Building icon..."
    ICONSET="/tmp/TobaccoTown_$$.iconset"
    mkdir -p "$ICONSET"
    for size in 16 32 128 256 512; do
        sips -z $size $size "$SCRIPT_DIR/assets/icon.png" \
            --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
        double=$((size * 2))
        sips -z $double $double "$SCRIPT_DIR/assets/icon.png" \
            --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
    done
    iconutil -c icns "$ICONSET" -o "$RESOURCES/AppIcon.icns"
    rm -rf "$ICONSET"
fi

cat > "$LAUNCHER" << 'EOF'
#!/bin/bash
MACOS="$(cd "$(dirname "$0")" && pwd -P)"
PROJECT="$(dirname "$(dirname "$(dirname "$MACOS")")")"
PYTHON="$PROJECT/.venv/bin/python3"
LOG="$PROJECT/tobaccotown.log"

if [[ ! -x "$PYTHON" ]]; then
    osascript -e 'display alert "TobaccoTown" message "Python environment not found.\n\nRun build_app.sh in Terminal to set up the app." as critical'
    exit 1
fi

# uv's standalone Python hardcodes Tcl/Tk paths to the build machine.
# Derive the real location from the Python base prefix at runtime.
PYTHON_BASE=$("$PYTHON" -c "import sys; print(sys.base_prefix)")
export TCL_LIBRARY="$PYTHON_BASE/lib/tcl8.6"
export TK_LIBRARY="$PYTHON_BASE/lib/tk8.6"

"$PYTHON" "$PROJECT/app.py" > "$LOG" 2>&1
EXIT=$?
if [[ $EXIT -ne 0 ]]; then
    ERROR=$(cat "$LOG")
    osascript -e "display alert \"TobaccoTown failed to start\" message \"$ERROR\" as critical"
fi
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
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
EOF

chmod +x "$LAUNCHER"
xattr -cr "$SCRIPT_DIR/TobaccoTown.app"

# Register with Launch Services and flush the icon cache so macOS
# picks up any updated icon immediately (no stale cached version).
LSREGISTER=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
"$LSREGISTER" -f "$SCRIPT_DIR/TobaccoTown.app" 2>/dev/null || true
"$LSREGISTER" -kill -r -domain local -domain user 2>/dev/null || true
touch "$SCRIPT_DIR/TobaccoTown.app"
killall Dock 2>/dev/null || true

echo "Done. Double-click TobaccoTown.app to launch."
