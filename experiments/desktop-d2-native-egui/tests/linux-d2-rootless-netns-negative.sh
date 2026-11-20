#!/usr/bin/env bash
# Nonpublishing: actual D2 GUI test-only wrapper, in Linux rootless netns.
# Does NOT relax the product's no-network source guard.
set -euo pipefail
if [[ "$(uname -s)" != "Linux" || "$#" -ne 1 ]]; then
  echo "D2_LINUX_NETNS_NO_GO: Linux and absolute test-only binary required" >&2
  exit 2
fi
binary="$1"
if [[ "$binary" != /* || ! -x "$binary" || -L "$binary" ||
      "$(basename "$binary")" != "medorigin_d2_self_sandbox_probe" ]]; then
  echo "D2_LINUX_NETNS_NO_GO: invalid test-only executable" >&2
  exit 2
fi
for dependency in unshare ip python3 Xvfb xvfb-run xwininfo; do
  command -v "$dependency" >/dev/null || {
    echo "D2_LINUX_NETNS_NO_GO: missing $dependency" >&2
    exit 1
  }
done
if [[ "$(printenv MEDORIGIN_LINUX_TEST_INSIDE_XVFB || true)" != "1" ]]; then
  exec xvfb-run -a -s "-screen 0 1280x800x24" \
    env MEDORIGIN_LINUX_TEST_INSIDE_XVFB=1 bash "$0" "$binary"
fi
# WSLg may set WAYLAND_DISPLAY even while an isolated Xvfb DISPLAY exists.
# Force the test's egui window onto this disposable X11 server only.
unset WAYLAND_DISPLAY
export XDG_SESSION_TYPE=x11
export WINIT_UNIX_BACKEND=x11
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
# Inside unshare: start our OWN Xvfb server in the SAME network namespace.
# Host Xvfb can use abstract UNIX sockets scoped to its netns and is therefore
# intentionally not reachable across the network-namespace boundary.
if [[ "$(printenv MEDORIGIN_LINUX_NETNS_CHILD || true)" == "1" ]]; then
  current_ns="$(readlink /proc/self/ns/net)"
  if [[ "$current_ns" == "$(printenv MEDORIGIN_LINUX_HOST_NS)" ]]; then
    echo "D2_LINUX_NETNS_NO_GO: child is in host netns" >&2
    exit 1
  fi
  if [[ "$(ip -o link show | wc -l)" -ne 1 ]] ||
     ! ip -brief link | grep -Eq '^lo[[:space:]]+DOWN'; then
    echo "D2_LINUX_NETNS_NO_GO: child has non-loopback or enabled interfaces" >&2
    ip -brief link >&2
    exit 1
  fi
  child_log="$(mktemp /tmp/medorigin-netns-child.XXXXXX)"
  "$binary" > "$child_log" 2>&1 &
  child_pid="$!"
  trap 'kill "$child_pid" 2>/dev/null || true; rm -f -- "$child_log"' EXIT
  for _ in {1..60}; do
    if grep -Fqx "MEDORIGIN_D2_LINUX_NETWORK_PROBE_RESULT=D2_LINUX_ROOTLESS_NETNS_LOOPBACK_UNREACHABLE" "$child_log" &&
       xwininfo -root -tree 2>/dev/null |
         grep -Fq "MedOrigin D2 Synthetic Network Test (NOT PRODUCT)"; then
      echo "D2_LINUX_CHILD_UNSHARED_NETNS_SOCKET_BLOCK_AND_NATIVE_XVFB_UI_PASS"
      exit 0
    fi
    if ! kill -0 "$child_pid" 2>/dev/null; then break; fi
    sleep 0.2
  done
  echo "D2_LINUX_NETNS_NO_GO: isolated GUI failed socket or window assertions" >&2
  cat "$child_log" >&2
  exit 1
fi
work="$(mktemp -d "/tmp/medorigin-linux-netns-d2.XXXXXX")"
listener_pid=""
gui_pid=""
cleanup() {
  if [[ -n "$gui_pid" ]]; then kill "$gui_pid" 2>/dev/null || true; fi
  if [[ -n "$listener_pid" ]]; then kill "$listener_pid" 2>/dev/null || true; fi
  rm -rf -- "$work"
}
trap cleanup EXIT

python3 -u - "$work/port" <<'PY' > "$work/loopback-listener.log" 2>&1 &
import socket
import sys
import time
from pathlib import Path

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.bind(("127.0.0.1", 0))
    server.listen(8)
    Path(sys.argv[1]).write_text(str(server.getsockname()[1]), encoding="ascii")
    time.sleep(50)
PY
listener_pid="$!"
for _ in {1..60}; do
  [[ -s "$work/port" ]] && break
  sleep 0.1
done
if [[ ! -s "$work/port" ]]; then
  echo "D2_LINUX_NETNS_NO_GO: no localhost listener" >&2
  exit 1
fi
port="$(cat "$work/port")"

# Separate positive control must be able to reach exactly the same port.
python3 - "$port" <<'PY'
import socket
import sys

with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=2):
    print("D2_LINUX_LOCALHOST_LISTENER_POSITIVE_CONTROL_PASS")
PY

wait_for_gui() {
  local pid="$1" expected="$2" log="$3"
  for _ in {1..60}; do
    if grep -Fqx "MEDORIGIN_D2_LINUX_NETWORK_PROBE_RESULT=$expected" "$log" \
       && xwininfo -root -tree 2>/dev/null \
         | grep -Fq "MedOrigin D2 Synthetic Network Test (NOT PRODUCT)"; then
      return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 0.2
  done
  echo "D2_LINUX_NETNS_NO_GO: expected $expected and real Xvfb window absent" >&2
  cat "$log" >&2
  return 1
}

# Same test-only D2 UI binary must connect without a namespace.
MEDORIGIN_D2_SYNTHETIC_LOOPBACK_PORT="$port" "$binary" \
  > "$work/unrestricted.log" 2>&1 &
gui_pid="$!"
wait_for_gui "$gui_pid" "D2_SELF_SANDBOX_PROBE_UNEXPECTED_NETWORK_ALLOWED_NO_GO" \
  "$work/unrestricted.log"
echo "D2_LINUX_SAME_BINARY_UNCONFINED_CONNECT_ALLOWED_PASS"
kill "$gui_pid" 2>/dev/null || true
wait "$gui_pid" 2>/dev/null || true
gui_pid=""

# Network and user namespaces are created without sudo or global firewall
# changes. Xvfb MUST start within this new namespace; the outer X server's
# abstract UNIX socket cannot cross it. The child verifies only lo/DOWN and
# compares its /proc netns inode to the externally supplied host inode.
host_ns="$(readlink /proc/self/ns/net)"
if ! MEDORIGIN_LINUX_NETNS_CHILD=1 \
  MEDORIGIN_LINUX_TEST_INSIDE_XVFB=0 \
  MEDORIGIN_LINUX_HOST_NS="$host_ns" \
  MEDORIGIN_D2_SYNTHETIC_LOOPBACK_PORT="$port" \
  unshare -Urn -- bash "$0" "$binary" > "$work/isolated.log" 2>&1; then
  echo "D2_LINUX_NETNS_NO_GO: child namespace/Xvfb/native GUI test failed" >&2
  cat "$work/isolated.log" >&2
  exit 1
fi
grep -Fqx "D2_LINUX_CHILD_UNSHARED_NETNS_SOCKET_BLOCK_AND_NATIVE_XVFB_UI_PASS" \
  "$work/isolated.log" || {
  echo "D2_LINUX_NETNS_NO_GO: child success marker absent" >&2
  cat "$work/isolated.log" >&2
  exit 1
}
echo "D2_LINUX_ACTUAL_TEST_WRAPPER_ROOTLESS_NETNS_AND_GUI_PASS_NO_RELEASE"
