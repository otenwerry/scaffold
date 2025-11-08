#!/usr/bin/env bash
set -euo pipefail
APP="dist/Scaffold.app"
KEYCHAIN_PROFILE="AC_NOTARY"
VOL="Scaffold Installer (dev2)"
DMG="Scaffold.dmg"
OUTDIR="."
# 1) Notarize & staple the .app (submit a ZIP of the app)
/usr/bin/ditto -c -k --keepParent "$APP" "Scaffold-app.zip"
/usr/bin/xcrun notarytool submit "Scaffold-app.zip" --keychain-profile "$KEYCHAIN_PROFILE" --wait
/usr/bin/xcrun stapler staple "$APP"
/usr/bin/xcrun stapler validate "$APP"
# 2) Build DMG from the already-stapled app
TMPDIR="$(/usr/bin/mktemp -d)"
/bin/mkdir -p "$TMPDIR/$VOL"
/bin/ln -s /Applications "$TMPDIR/$VOL/Applications"
/usr/bin/ditto "$APP" "$TMPDIR/$VOL/Scaffold.app"
/usr/bin/hdiutil create -volname "$VOL" -srcfolder "$TMPDIR/$VOL" -ov -format UDZO "$OUTDIR/$DMG"
/bin/rm -rf "$TMPDIR"
# 3) Notarize & staple the DMG
/usr/bin/xcrun notarytool submit "$OUTDIR/$DMG" --keychain-profile "$KEYCHAIN_PROFILE" --wait
/usr/bin/xcrun stapler staple "$OUTDIR/$DMG"
/usr/bin/xcrun stapler validate "$OUTDIR/$DMG"
echo "Notarized & stapled: $APP and $DMG"
