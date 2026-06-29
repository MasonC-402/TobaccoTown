#!/usr/bin/env bash
# Creates TobaccoTown.app so Finder / Spotlight can launch it.
# The launcher script resolves paths at runtime, so no binary copy is needed.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
MACOS="$SCRIPT_DIR/TobaccoTown.app/Contents/MacOS"
LAUNCHER="$MACOS/TobaccoTown"
PLIST="$SCRIPT_DIR/TobaccoTown.app/Contents/Info.plist"

mkdir -p "$MACOS"

cat > "$LAUNCHER" << 'EOF'
#!/bin/bash
# Resolve absolute path to this script's directory (MacOS/)
MACOS="$(cd "$(dirname "$0")" && pwd -P)"
# MacOS -> Contents -> TobaccoTown.app -> project root
PROJECT="$(dirname "$(dirname "$(dirname "$MACOS")")")"
exec "$PROJECT/.venv/bin/python3" "$PROJECT/app.py"
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
