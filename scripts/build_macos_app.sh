#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ICONSET_DIR="work/macos/AppIcon.iconset"
ICNS_PATH="work/macos/app-icon.icns"
APP_PATH="dist/Oxford to Notion.app"
APP_EXECUTABLE="$APP_PATH/Contents/MacOS/Oxford to Notion"

rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

sips -z 16 16 assets/app-icon.png --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32 assets/app-icon.png --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32 assets/app-icon.png --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64 assets/app-icon.png --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 assets/app-icon.png --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 assets/app-icon.png --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 assets/app-icon.png --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 assets/app-icon.png --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 assets/app-icon.png --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -z 1024 1024 assets/app-icon.png --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET_DIR" -o "$ICNS_PATH"

rm -rf "build/Oxford to Notion" "$APP_PATH"
python -m PyInstaller \
  --noconfirm \
  --clean \
  --onedir \
  --windowed \
  --icon "$ICNS_PATH" \
  --add-data "assets/app-icon.png:assets" \
  --add-data "version.json:." \
  --name "Oxford to Notion" \
  gui.py

python scripts/package_version.py macos "$APP_PATH/Contents/Info.plist"
"$APP_EXECUTABLE" --smoke-test
codesign --force --deep --sign - "$APP_PATH"
codesign --verify --deep --strict "$APP_PATH"
