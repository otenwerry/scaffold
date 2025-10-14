APP_PATH="dist/Tutor.app"
IDENTITY="Developer ID Application: Caroline Smyth (AF38K5WH45)"
ENTITLEMENTS="entitlements.plist"

# Remove quarantine attributes
xattr -cr "$APP_PATH"

# Sign each component individually, from inside out
codesign --force --sign "$IDENTITY" --timestamp \
  --options runtime \
  "$APP_PATH/Contents/MacOS/Tutor"

# Sign the app bundle
codesign --force --sign "$IDENTITY" --timestamp \
  --options runtime \
  --entitlements "$ENTITLEMENTS" \
  "$APP_PATH"

# Verify
codesign --verify --deep --strict --verbose=2 "$APP_PATH"