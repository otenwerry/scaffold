#!/usr/bin/env bash
set -euo pipefail
APP="dist/Scaffold.app"
APP_BIN="$APP/Contents/MacOS/Scaffold"
ENT="entitlements.plist"
SIGN="Developer ID Application: Caroline Smyth (AF38K5WH45)"
# Clear quarantine
/usr/bin/xattr -r -d com.apple.quarantine "$APP" || true

# Sign nested code first (frameworks, dylibs, .so, helpers)
# (Exclude the main executable; sign it separately with entitlements)
while IFS= read -r -d '' f; do
  echo "Signing nested: $f"
  /usr/bin/codesign --force --options runtime --timestamp -s "$SIGN" "$f"
done < <(/usr/bin/find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" -o -path "*/Frameworks/*" -o -path "*/MacOS/*" \) ! -path "$APP_BIN" -print0)
# Sign main executable with entitlements
echo "Signing main executable: $APP_BIN"
/usr/bin/codesign --force --options runtime --timestamp --entitlements "$ENT" -s "$SIGN" "$APP_BIN"
# Verify the audio-input entitlement is actually present on the main EXE
/usr/bin/codesign -d --entitlements :- "$APP_BIN" 2>/dev/null | /usr/bin/grep -q "com.apple.security.device.audio-input" \
  || { echo "ERROR: audio-input entitlement missing on $APP_BIN"; exit 1; }
# Sign the bundle
/usr/bin/codesign --force --options runtime --timestamp --entitlements "$ENT" -s "$SIGN" "$APP"
# Local verification
/usr/bin/codesign --verify --deep --strict --verbose=2 "$APP"
#/usr/sbin/spctl --assess --type execute --verbose "$APP"
echo "Signed and locally verified: $APP"
