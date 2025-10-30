APP="dist/Scaffold.app"
BIN="$APP/Contents/MacOS/Scaffold"
ENT="$(pwd)/entitlements.plist"

# sanity checks
echo "BIN points to:" "$(readlink "$BIN" || echo '(not a symlink)')"
plutil -lint "$ENT"                     # should say "OK"
file "$BIN"                             # should say: Mach-O ... executable (arm64/universal)
plutil -p "$APP/Contents/Info.plist" | grep -A1 CFBundleExecutable
# Confirm CFBundleExecutable is "Scaffold" and matches the filename

# nuke existing signatures
codesign --remove-signature "$BIN" 2>/dev/null || true

# sign just the main executable with entitlements (no other files yet)
codesign --force --options runtime --timestamp \
  --entitlements "$ENT" \
  -s 'Developer ID Application: Caroline Smyth (AF38K5WH45)' \
  "$BIN"

# immediately print entitlements from the main exe
codesign -dv --verbose=4 "$BIN"
echo "----- Embedded entitlements on main exe:"
codesign -d --entitlements - "$BIN"

# sign nested code (Frameworks/PlugIns/Resources .so), no entitlements:
find "$APP/Contents/Frameworks" -type f \( -name "*.dylib" -o -perm -111 \) -print0 2>/dev/null \
| xargs -0 -I{} codesign --force --options runtime --timestamp -s 'Developer ID Application: Caroline Smyth (AF38K5WH45)' "{}" 2>/dev/null || true

find "$APP/Contents/PlugIns" -type f -perm -111 -print0 2>/dev/null \
| xargs -0 -I{} codesign --force --options runtime --timestamp -s 'Developer ID Application: Caroline Smyth (AF38K5WH45)' "{}" 2>/dev/null || true

find "$APP/Contents/Resources" -type f -name "*.so" -print0 2>/dev/null \
| xargs -0 -I{} codesign --force --options runtime --timestamp -s 'Developer ID Application: Caroline Smyth (AF38K5WH45)' "{}" 2>/dev/null || true

# re-apply entitlements to the main exe last, in case anything touched it:
codesign --force --options runtime --timestamp \
  --entitlements "$ENT" \
  -s 'Developer ID Application: Caroline Smyth (AF38K5WH45)' \
  "$BIN"

# sign the outer bundle (no entitlements):
codesign --force --options runtime --timestamp \
  -s 'Developer ID Application: Caroline Smyth (AF38K5WH45)' \
  "$APP"

# verify
codesign --verify --deep --strict --verbose=4 "$APP"
codesign -d --entitlements - "$BIN"