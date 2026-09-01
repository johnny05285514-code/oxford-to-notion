#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_PATH="dist/Oxford to Notion.app"
STAGE_DIR="work/macos/dmg-stage"
DMG_PATH="release/Oxford-to-Notion-macOS-arm64.dmg"
CHECKSUM_PATH="$DMG_PATH.sha256"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing $APP_PATH. Run scripts/build_macos_app.sh first." >&2
  exit 1
fi

rm -rf "$STAGE_DIR"
rm -f "$DMG_PATH" "$CHECKSUM_PATH"
mkdir -p "$STAGE_DIR" release

ditto "$APP_PATH" "$STAGE_DIR/Oxford to Notion.app"
ln -s /Applications "$STAGE_DIR/Applications"
hdiutil create \
  -volname "Oxford to Notion" \
  -srcfolder "$STAGE_DIR" \
  -format UDZO \
  -ov \
  "$DMG_PATH"
shasum -a 256 "$DMG_PATH" > "$CHECKSUM_PATH"
