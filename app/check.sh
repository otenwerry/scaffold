# allow inline comments in zsh (optional)
setopt interactivecomments

APP_BUILT="dist/Scaffold.app"
APP_DMG="/Volumes/Scaffold Installer/Scaffold.app"

# Identity / hardened runtime / team / ticket (both should match)
codesign -dvv --requirements :- "$APP_BUILT" 2>&1 | sed -n '1,200p'
codesign -dvv --requirements :- "$APP_DMG"   2>&1 | sed -n '1,200p'

# Entitlements (confirm audio-input = true)
echo "--- Built entitlements ---"
codesign -d --entitlements :- "$APP_BUILT" 2>/dev/null | plutil -p -
echo "--- DMG entitlements ---"
codesign -d --entitlements :- "$APP_DMG"   2>/dev/null | plutil -p -

# Quick grep just for the mic entitlement
for A in "$APP_BUILT" "$APP_DMG"; do
  echo "audio-input in: $A"
  codesign -d --entitlements :- "$A" 2>/dev/null | plutil -p - | grep 'com.apple.security.device.audio-input' || true
done
