#!/usr/bin/env bash
# Real macOS App Sandbox OS-denial test, synthetic loopback only.
# This qualifies the entitlement mechanism, NOT the full D2 product egress.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "MACOS_SANDBOX_NO_GO: Apple macOS required" >&2
  exit 2
fi

source_dir="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d "/tmp/medorigin-sandbox-negative.XXXXXX")"
listener_pid=""
cleanup() {
  if [[ -n "$listener_pid" ]]; then
    kill "$listener_pid" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$work"
}
trap cleanup EXIT

# Static contract: only the app sandbox entitlement, NO network.client/server.
python3 - "$source_dir/macos-d2-no-network.entitlements" <<'PY'
import plistlib
import sys

with open(sys.argv[1], "rb") as stream:
    data = plistlib.load(stream)
assert data == {"com.apple.security.app-sandbox": True}, data
print("MACOS_SANDBOX_ENTITLEMENTS_NETWORK_DENY_SOURCE_PASS")
PY

clang -std=c11 -Wall -Wextra -Werror \
  "$source_dir/macos-loopback-sandbox-probe.c" -o "$work/unsigned-probe"

bundle="$work/MedOriginSyntheticNetworkProbe.app"
mkdir -p "$bundle/Contents/MacOS"
cp "$work/unsigned-probe" "$bundle/Contents/MacOS/sandbox-probe"
cat > "$bundle/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>si.medorigin.d2.synthetic.sandbox.probe</string>
  <key>CFBundleExecutable</key><string>sandbox-probe</string>
  <key>CFBundleName</key><string>MedOrigin Local Network Deny Test</string>
  <key>CFBundlePackageType</key><string>APPL</string>
</dict></plist>
PLIST

plutil -lint "$bundle/Contents/Info.plist"
codesign --force --sign - --timestamp=none \
  --entitlements "$source_dir/macos-d2-no-network.entitlements" "$bundle"
codesign --verify --strict "$bundle"

# Host a temporary listener ONLY on 127.0.0.1. An unconfined control must
# connect successfully, while the exact same probe in the signed sandbox
# must be rejected by macOS (EPERM/EACCES). No external packet is sent.
python3 -u - "$work/port.txt" <<'PY' > "$work/listener.log" 2>&1 &
import socket
import sys
import time
from pathlib import Path

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.bind(("127.0.0.1", 0))
    server.listen(2)
    Path(sys.argv[1]).write_text(str(server.getsockname()[1]), encoding="ascii")
    time.sleep(20)
PY
listener_pid="$!"

for _ in {1..50}; do
  [[ -s "$work/port.txt" ]] && break
  sleep 0.1
done
if [[ ! -s "$work/port.txt" ]]; then
  echo "MACOS_SANDBOX_NO_GO: loopback listener could not start" >&2
  exit 1
fi
port="$(cat "$work/port.txt")"
"$work/unsigned-probe" "$port" > "$work/control.txt" 2>&1 || {
  echo "MACOS_SANDBOX_NO_GO: unrestricted loopback control failed" >&2
  exit 1
}
grep -Fqx "LOOPBACK_CONTROL_CONNECT_ALLOWED" "$work/control.txt" || {
  echo "MACOS_SANDBOX_NO_GO: unrestricted control not observed" >&2
  exit 1
}

sandbox_status=0
"$bundle/Contents/MacOS/sandbox-probe" "$port" \
  > "$work/denied.txt" 2>&1 || sandbox_status="$?"
if [[ "$sandbox_status" -ne 77 ]]; then
  echo "MACOS_SANDBOX_NO_GO: expected OS denial (77), observed $sandbox_status" >&2
  cat "$work/denied.txt" >&2
  exit 1
fi
grep -Fq "LOOPBACK_CONNECT_REJECTED errno=" "$work/denied.txt" || {
  echo "MACOS_SANDBOX_NO_GO: no matching OS-denial evidence" >&2
  exit 1
}
echo "MACOS_APP_SANDBOX_LOOPBACK_DENY_PASS_NOT_PRODUCT_EGRESS_AUTHORITY"
