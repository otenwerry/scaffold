#!/usr/bin/env bash
set -euo pipefail
APP="dist/Scaffold.app"
KEYCHAIN_PROFILE="AC_NOTARY"
VOL="Scaffold Installer 2"
DMG="Scaffold.dmg"
OUTDIR="."
# 1) Notarize & staple the .app (submit a ZIP of the app)
/usr/bin/ditto -c -k --keepParent "$APP" "Scaffold-app.zip"
/usr/bin/xcrun notarytool submit "Scaffold-app.zip" --keychain-profile "$KEYCHAIN_PROFILE" --wait
/usr/bin/xcrun stapler staple "$APP"
/usr/bin/xcrun stapler validate "$APP"
# 2) Build DMG from the already-stapled app
TMPDIR="$(/usr/bin/mktemp -d)"
VOL="Scaffold Installer"
/bin/mkdir -p "$TMPDIR/$VOL"
/bin/ln -s /Applications "$TMPDIR/$VOL/Applications"

/usr/bin/ditto "$APP" "$TMPDIR/$VOL/Scaffold.app"

# sanity check before sealing the DMG:
codesign --verify --deep --strict --verbose=2 "$TMPDIR/$VOL/Scaffold.app"
codesign -d --entitlements - "$TMPDIR/$VOL/Scaffold.app/Contents/MacOS/Scaffold"

# create the DMG
/usr/bin/hdiutil create -volname "$VOL" -srcfolder "$TMPDIR/$VOL" -ov -format UDZO "$OUTDIR/$DMG"
/bin/rm -rf "$TMPDIR"
