#!/usr/bin/env bash
# Local macOS-only synthetic test. No installer, publish, PHI or network claim.
set -euo pipefail
if [[ $# -ne 3 ]]; then
  echo "D2_MAC_AX_USAGE: <native-d2-exe> <pinned-sha256> <fresh-audit-folder>" >&2
  exit 2
fi
exe="$1"
pinned="$2"
audit="$3"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "D2_MAC_AX_NO_GO: macOS required" >&2; exit 2
fi
if [[ "$exe" != /* || "$audit" != /* || -e "$audit" ]]; then
  echo "D2_MAC_AX_NO_GO: absolute source and fresh audit required" >&2; exit 2
fi
if [[ ! -f "$exe" || -L "$exe" || "${exe##*/}" != "medorigin-desktop-d2-native-egui" ]]; then
  echo "D2_MAC_AX_NO_GO: expected exact non-symlink D2 executable" >&2; exit 2
fi
if [[ ! "$pinned" =~ ^[0-9A-Fa-f]{64}$ ]]; then
  echo "D2_MAC_AX_NO_GO: caller must pin full SHA-256" >&2; exit 2
fi
actual="$(shasum -a 256 "$exe" | cut -d ' ' -f 1)"
expected="$(printf '%s' "$pinned" | tr '[:upper:]' '[:lower:]')"
if [[ "$actual" != "$expected" ]]; then
  echo "D2_MAC_AX_NO_GO: source executable digest mismatch" >&2; exit 2
fi
scriptdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
swift_probe="$scriptdir/macos-native-ax-smoke.swift"
[[ -f "$swift_probe" ]] || { echo "D2_MAC_AX_NO_GO: missing source probe" >&2; exit 2; }
swiftc -typecheck "$swift_probe"
bundle="$audit/MedOriginSyntheticD2.app"
mkdir -p "$bundle/Contents/MacOS"
staged="$bundle/Contents/MacOS/medorigin-desktop-d2-native-egui"
cp "$exe" "$staged"
if [[ "$(shasum -a 256 "$staged" | cut -d ' ' -f 1)" != "$expected" ]]; then
  echo "D2_MAC_AX_NO_GO: staged digest mismatch" >&2; exit 2
fi
cat > "$bundle/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>org.medorigin.d2.synthetic.localqualification</string>
  <key>CFBundleName</key><string>MedOrigin D2 Synthetic Local Qualification</string>
  <key>CFBundleExecutable</key><string>medorigin-desktop-d2-native-egui</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>0.0.0</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
plutil -lint "$bundle/Contents/Info.plist" > /dev/null
pid=""
cleanup() {
  if [[ -n "$pid" ]] && ps -p "$pid" -o command= 2>/dev/null | grep -Fq "$staged"; then
    kill "$pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
open -n -a "$bundle"
for i in {1..40}; do
  pid="$(pgrep -f "$staged" | head -n 1 || true)"
  [[ -n "$pid" ]] && break
  sleep 0.25
done
[[ -n "$pid" ]] || { echo "D2_MAC_AX_NO_GO: Launch Services process absent" >&2; exit 2; }
if ! swift "$swift_probe" "$pid" > "$audit/interactive-macos-ax.txt" 2>&1; then
  cat "$audit/interactive-macos-ax.txt" >&2
  echo "D2_MAC_AX_NO_GO: interactive controls or synthetic digest failed" >&2
  exit 2
fi
if ! grep -Fqx "D2_MAC_NATIVE_AX_4_OF_4_PASS (fictional fixtures; packet isolation unqualified)" "$audit/interactive-macos-ax.txt"; then
  echo "D2_MAC_AX_NO_GO: acceptance marker missing" >&2; exit 2
fi
printf '%s\n' '{"schema":"medorigin-native-d2-macos-ax-v1","executing_verified_copy":true,"interactive_macos_ax_4_of_4_pass":true,"network_isolation_qualified":false,"clinical_qualified":false,"release_qualified":false}' > "$audit/qualification.json"
echo "D2_MAC_AX_VERIFIED_STAGED_BINARY_SHA256=$actual"
cat "$audit/interactive-macos-ax.txt"
echo "D2_MAC_AX_LOCAL_QUALIFICATION_PASS (synthetic only; NO RELEASE)"
