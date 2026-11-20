#!/usr/bin/env bash
# Optional actual-WSL integration regression; no external socket, GUI or
# Windows process launch. Run only on an authorized test WSL installation.
set -euo pipefail
if ! grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then
  echo "WSL_EARLY_REFUSAL_NOT_APPLICABLE_ON_THIS_LINUX_HOST"
  exit 0
fi
for tool in unshare python3 readlink; do
  command -v "$tool" >/dev/null || { echo "MISSING_TEST_TOOL:$tool" >&2; exit 2; }
done
here="$(cd -- "$(dirname -- "$0")" && pwd)"
probe="$here/linux-private-netns-smoke.py"
launcher="$here/linux-private-netns-smoke.sh"
test -f "$probe" && test -f "$launcher"
host_ns="$(readlink /proc/self/ns/net)"
sha="$(printf '0%.0s' {1..64})"
if result="$(unshare --user --map-root-user --net -- \
  env MEDORIGIN_D2_PRIVATE_NETNS_EXPERIMENT=1 \
  python3 "$probe" --binary /nonexistent-test-executable \
  --sha256 "$sha" --host-netns "$host_ns")"; then
  echo "UNSAFE_PROBE_FALSE_SUCCESS_IN_WSL_NETNS" >&2
  exit 4
fi
printf '%s' "$result" | python3 -c '
import json, sys
packet = json.load(sys.stdin)
assert packet["decision"] == "NO_GO", packet
assert packet["reason"] == "WSL_WINDOWS_PROCESS_INTEROP_UNCONFINED", packet
assert packet["release_authorized"] is False, packet
for prohibited in ("negative_controls", "negative_controls_while_app_running", "native_x11_window_seen", "binary_sha256"):
    assert prohibited not in packet, packet
'
echo "WSL_INTEROP_GUEST_PYTHON_FAIL_CLOSED_PASS"
bash -n "$launcher"
if bash "$launcher" /nonexistent-test-executable "$sha" >/dev/null 2>&1; then
  echo "UNSAFE_LAUNCHER_FALSE_SUCCESS_ON_WSL" >&2
  exit 5
fi
echo "WSL_INTEROP_SHELL_EARLY_REFUSAL_PASS"
echo "MEDORIGIN_WSL_INTEROP_TWO_INTEGRATION_GATES_PASS_NO_RELEASE"
