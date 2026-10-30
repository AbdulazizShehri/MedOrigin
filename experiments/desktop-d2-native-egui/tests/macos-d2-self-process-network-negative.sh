#!/usr/bin/env bash
# Nonpublishing real Mac only. Build the test-only examples/ network wrapper.
# Reuses real D2 GUI components, but is NOT the default product executable.
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" || "$#" -ne 1 ]]; then
  echo "D2_SELF_EGRESS_NO_GO: expected Mac and absolute test-enabled D2 binary" >&2
  exit 2
fi
binary="$1"
if [[ "$binary" != /* || ! -f "$binary" || -L "$binary" ||
      "$(basename "$binary")" != "medorigin_d2_self_sandbox_probe" ]]; then
  echo "D2_SELF_EGRESS_NO_GO: wrong binary path" >&2
  exit 2
fi
source_dir="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d "/tmp/medorigin-d2-self-egress.XXXXXX")"
work="$(cd "$work" && pwd -P)"
pid=""
control_pid=""
listener_pid=""
cleanup() {
  [[ -z "$pid" ]] || kill "$pid" >/dev/null 2>&1 || true
  [[ -z "$control_pid" ]] || kill "$control_pid" >/dev/null 2>&1 || true
  [[ -z "$listener_pid" ]] || kill "$listener_pid" >/dev/null 2>&1 || true
  rm -rf -- "$work"
}
trap cleanup EXIT

# Positive network control on EXACT same live localhost port as the app's probe.
python3 -u - "$work/port.txt" <<'PY' >"$work/listener.log" 2>&1 &
import socket
import sys
import time
from pathlib import Path

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)
    Path(sys.argv[1]).write_text(str(listener.getsockname()[1]), encoding="ascii")
    time.sleep(50)
PY
listener_pid="$!"
for _ in {1..60}; do
  [[ -s "$work/port.txt" ]] && break
  sleep 0.1
done
if [[ ! -s "$work/port.txt" ]]; then
  echo "D2_SELF_EGRESS_NO_GO: control listener absent" >&2
  exit 1
fi
port="$(cat "$work/port.txt")"
clang -std=c11 -Wall -Wextra -Werror \
  "$source_dir/macos-loopback-sandbox-probe.c" -o "$work/control"
control="$("$work/control" "$port")" || {
  echo "D2_SELF_EGRESS_NO_GO: unrestricted control connect failed" >&2
  exit 1
}
if [[ "$control" != "LOOPBACK_CONTROL_CONNECT_ALLOWED" ]]; then
  echo "D2_SELF_EGRESS_NO_GO: invalid unrestricted control response" >&2
  exit 1
fi

# The SAME opt-in D2 executable must actually connect when not sandboxed;
# otherwise a hardcoded "denied" label would produce a false success.
MEDORIGIN_D2_SYNTHETIC_LOOPBACK_PORT="$port" \
  "$binary" > "$work/unconfined.log" 2>&1 &
control_pid="$!"
sleep 0.5
if ! kill -0 "$control_pid" 2>/dev/null; then
  echo "D2_SELF_EGRESS_NO_GO: unsigned GUI crashed before positive control" >&2
  exit 1
fi
swift "$source_dir/macos-native-d2-self-egress-qualification.swift" \
  "$control_pid" --expect-unconfined-allowed
kill "$control_pid" >/dev/null 2>&1 || true
wait "$control_pid" 2>/dev/null || true
control_pid=""

bundle="$work/MedOriginD2SelfSandboxLocal.app"
mkdir -p "$bundle/Contents/MacOS"
cp "$binary" "$bundle/Contents/MacOS/medorigin_d2_self_sandbox_probe"
cat >"$bundle/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>si.medorigin.d2.synthetic.selfegress.localtest</string>
  <key>CFBundleExecutable</key><string>medorigin_d2_self_sandbox_probe</string>
  <key>CFBundleName</key><string>MedOrigin D2 Self Sandbox Test</string>
  <key>CFBundlePackageType</key><string>APPL</string>
</dict></plist>
PLIST
plutil -lint "$bundle/Contents/Info.plist"
codesign --force --sign - --timestamp=none \
  --entitlements "$source_dir/macos-d2-no-network.entitlements" "$bundle"
codesign --verify --strict "$bundle"

# Direct execution preserves the test-only loopback port environment while
# running the ACTUAL signed D2 GUI process. No LaunchServices-wide env change.
MEDORIGIN_D2_SYNTHETIC_LOOPBACK_PORT="$port" \
  "$bundle/Contents/MacOS/medorigin_d2_self_sandbox_probe" \
  > "$work/app.log" 2>&1 &
pid="$!"
sleep 0.7
if ! kill -0 "$pid" 2>/dev/null; then
  echo "D2_SELF_EGRESS_NO_GO: signed D2 GUI crashed" >&2
  cat "$work/app.log" >&2
  exit 1
fi

swift "$source_dir/macos-native-d2-self-egress-qualification.swift" "$pid"
swift "$source_dir/macos-native-ax-qualification.swift" "$pid"
swift "$source_dir/macos-native-keyboard-qualification.swift" "$pid"
echo "D2_SIGNED_TEST_WRAPPER_LOOPBACK_DENIAL_AND_REAL_D2_GUI_4OF4_PASS_NOT_RELEASE"
