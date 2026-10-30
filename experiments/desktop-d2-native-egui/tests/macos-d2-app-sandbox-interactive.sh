#!/usr/bin/env bash
# Real authorized Mac-only D2 app sandbox + AX/keyboard reproducibility.
# Accepts a locally built, unpublished binary and never uploads artifacts.
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" || "$#" -ne 1 ]]; then
  echo "MACOS_D2_SANDBOX_NO_GO: expected Mac and absolute D2 binary path" >&2
  exit 2
fi
binary="$1"
if [[ "$binary" != /* || ! -f "$binary" || -L "$binary" ||
      "$(basename "$binary")" != "medorigin-desktop-d2-native-egui" ]]; then
  echo "MACOS_D2_SANDBOX_NO_GO: invalid native binary" >&2
  exit 2
fi
source_dir="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d "/tmp/medorigin-d2-sandbox-gui.XXXXXX")"
# Resolve /tmp -> /private/tmp on macOS so exact PID matching survives LaunchServices.
work="$(cd "$work" && pwd -P)"
bundle="$work/D2SandboxLocal.app"
executable="$bundle/Contents/MacOS/medorigin-desktop-d2-native-egui"
pid=""
cleanup() {
  if [[ -n "$pid" ]]; then
    kill "$pid" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$work"
}
trap cleanup EXIT
mkdir -p "$bundle/Contents/MacOS"
cp "$binary" "$executable"
cat > "$bundle/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>si.medorigin.d2.synthetic.sandbox.localtest</string>
  <key>CFBundleExecutable</key><string>medorigin-desktop-d2-native-egui</string>
  <key>CFBundleName</key><string>MedOrigin D2 Synthetic No Network Test</string>
  <key>CFBundlePackageType</key><string>APPL</string>
</dict></plist>
PLIST
plutil -lint "$bundle/Contents/Info.plist"
codesign --force --sign - --timestamp=none \
  --entitlements "$source_dir/macos-d2-no-network.entitlements" "$bundle"
codesign --verify --strict "$bundle"
open -n "$bundle"
for _ in {1..30}; do
  pid="$(pgrep -f -x "$executable" || true)"
  [[ -n "$pid" ]] && break
  sleep 0.2
done
if [[ -z "$pid" || "$pid" == *$'\n'* ]]; then
  echo "MACOS_D2_SANDBOX_NO_GO: signed app did not start uniquely" >&2
  exit 1
fi
# Both tests drive the actual GUI and verify four real displayed SHA digests.
swift "$source_dir/macos-native-ax-qualification.swift" "$pid"
swift "$source_dir/macos-native-keyboard-qualification.swift" "$pid"
echo "MACOS_D2_SIGNED_SANDBOX_AX_AND_KEYBOARD_4OF4_PASS_NOT_RELEASE_AUTHORITY"
