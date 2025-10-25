#!/usr/bin/env bash
set -euo pipefail
APP="dist/Tutor.app"
APP_BIN="$APP/Contents/MacOS/Tutor"
ENT="entitlements.plist"
SIGN="Developer ID Application: Caroline Smyth (AF38K5WH45)"
# Clear quarantine
/usr/bin/xattr -r -d com.apple.quarantine "$APP" || true
# Sign nested code first (frameworks, dylibs, .so, helpers)
# (Exclude the main executable; sign it separately with entitlements)
while IFS= read -r -d '' f; do
  /usr/bin/codesign --force --options runtime --timestamp -s "$SIGN" "$f"
done < <(/usr/bin/find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" -o -path "*/Frameworks/*" -o -path "*/MacOS/*" \) ! -path "$APP_BIN" -print0)
# Sign main executable with entitlements
/usr/bin/codesign --force --options runtime --timestamp --entitlements "$ENT" -s "$SIGN" "$APP_BIN"
# Sign the bundle
/usr/bin/codesign --force --options runtime --timestamp -s "$SIGN" "$APP"
# Local verification
/usr/bin/codesign --verify --deep --strict --verbose=2 "$APP"
#/usr/sbin/spctl --assess --type execute --verbose "$APP"
echo "Signed and locally verified: $APP"
