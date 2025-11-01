# Paths
APP_BUILT="dist/Scaffold.app"
APP_DMG="/Volumes/Scaffold Installer/Scaffold.app"   # mount your latest DMG first

# Compare bundle ids + usage strings
plutil -p "$APP_BUILT/Contents/Info.plist" | egrep 'CFBundleIdentifier|CFBundleVersion|CFBundleShortVersionString|NSMicrophone'
plutil -p "$APP_DMG/Contents/Info.plist"   | egrep 'CFBundleIdentifier|CFBundleVersion|CFBundleShortVersionString|NSMicrophone'

# Compare signatures + entitlements
codesign -dvv --requirements :- "$APP_BUILT" 2>/dev/null
codesign -dvv --requirements :- "$APP_DMG"   2>/dev/null

codesign -d --entitlements :- "$APP_BUILT" 2>/dev/null
codesign -d --entitlements :- "$APP_DMG"   2>/dev/null

# Compare the actual main binary bytes
shasum "$APP_BUILT/Contents/MacOS/Scaffold"
shasum "$APP_DMG/Contents/MacOS/Scaffold"
