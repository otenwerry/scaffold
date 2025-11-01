APP="dist/Scaffold.app"

# 1) Dump entitlements to a temp file (don’t pipe directly)
TMP=$(mktemp -t scaffold_ent.plist)
codesign -d --entitlements :- "$APP" > "$TMP" 2>/dev/null || true

# 2) See what we actually got
wc -c "$TMP"
file "$TMP"
plutil -lint "$TMP" || true

# 3) If it’s a plist, print it; otherwise show raw
if plutil -lint "$TMP" >/dev/null 2>&1; then
  echo "Parsed entitlements:"
  plutil -p "$TMP"
else
  echo "Raw entitlements dump (not a plist or empty):"
  sed -n '1,80p' "$TMP"
fi
