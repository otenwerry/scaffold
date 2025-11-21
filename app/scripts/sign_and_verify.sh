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
SPARKLE="$APP/Contents/Frameworks/Sparkle.framework"
if [ -d "$SPARKLE" ]; then
  echo "Cleaning Sparkle xattrs..."
  /usr/bin/xattr -cr "$SPARKLE"
  /usr/bin/dot_clean -m "$SPARKLE" 2>/dev/null || true
  echo "Signing Sparkle inner items..."
  # XPC services (preserve entitlements if present)
  for xpc in "$SPARKLE"/Versions/*/XPCServices/*.xpc; do
    [ -d "$xpc" ] || continue
    echo "  Signing XPC: $xpc"
    /usr/bin/codesign --force --options runtime --timestamp \
      --preserve-metadata=entitlements \
      -s "$SIGN" "$xpc"
  done
  # Autoupdate + Updater.app if they exist
  for item in \
      "$SPARKLE"/Versions/*/Autoupdate \
      "$SPARKLE"/Versions/*/Updater.app; do
    [ -e "$item" ] || continue
    echo "  Signing Sparkle helper: $item"
    /usr/bin/codesign --force --options runtime --timestamp -s "$SIGN" "$item"
  done
  echo "Signing Sparkle.framework bundle..."
  /usr/bin/codesign --force --options runtime --timestamp -s "$SIGN" "$SPARKLE"
fi
while IFS= read -r -d '' f; do
  echo "Signing nested: $f"
  /usr/bin/codesign --force --options runtime --timestamp -s "$SIGN" "$f"
done < <(/usr/bin/find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" -o -path "*/MacOS/*" \) ! -path "$APP_BIN" -print0)
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
