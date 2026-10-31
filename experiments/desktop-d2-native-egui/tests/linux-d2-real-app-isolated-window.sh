#!/usr/bin/env bash
# Real native D2 product-source executable in rootless Linux netns.
# Synthetic GUI only; this is NOT a release or whole-network packet attestation.
set -euo pipefail
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "D2_LINUX_NATIVE_NO_GO: Linux required" >&2
  exit 2
fi
inside="0"
if [[ "$#" -eq 2 && "$1" == "--inside" ]]; then
  inside="1"
  shift
fi
if [[ "$#" -ne 1 ]]; then
  echo "D2_LINUX_NATIVE_NO_GO: absolute native D2 binary required" >&2
  exit 2
fi
binary="$1"
if [[ "$binary" != /* || ! -x "$binary" || -L "$binary" ||
      "$(basename "$binary")" != "medorigin-desktop-d2-native-egui" ]]; then
  echo "D2_LINUX_NATIVE_NO_GO: refused non-native executable" >&2
  exit 2
fi

if [[ "$inside" == "0" ]]; then
  # Host network configuration is never changed. This user's Linux kernel must
  # allow unprivileged user and network namespaces; fail if it does not.
  # Positive controls run only on host loopback, with no external traffic.
  # Both protocol families and both socket types must be usable on this host;
  # a missing IPv6 stack is NOT counted as a successful negative test.
  python3 - <<'PYHOST'
import socket

for family, bind_addr in (
    (socket.AF_INET, ("127.0.0.1", 0)),
    (socket.AF_INET6, ("::1", 0, 0, 0)),
):
    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        with socket.socket(family, kind) as server:
            server.settimeout(2)
            server.bind(bind_addr)
            if kind == socket.SOCK_STREAM:
                server.listen(1)
            with socket.socket(family, kind) as client:
                client.settimeout(2)
                if kind == socket.SOCK_STREAM:
                    client.connect(server.getsockname())
                    peer, _ = server.accept()
                    peer.close()
                else:
                    client.sendto(b"synthetic", server.getsockname())
                    received, _ = server.recvfrom(32)
                    assert received == b"synthetic"
print("D2_HOST_IPV4_IPV6_TCP_UDP_LOOPBACK_POSITIVE_CONTROL_PASS")
PYHOST
  host_ns="$(readlink /proc/self/ns/net)"
  MEDORIGIN_D2_EXPECT_HOST_NETNS="$host_ns" \
    unshare -Urn -- bash "$0" --inside "$binary"
  exit 0
fi

if [[ "$(readlink /proc/self/ns/net)" == "$(printenv MEDORIGIN_D2_EXPECT_HOST_NETNS)" ]]; then
  echo "D2_LINUX_NATIVE_NO_GO: native app did not enter a new network namespace" >&2
  exit 1
fi
if [[ "$(ip -o link show | wc -l)" -ne 1 ]] ||
   ! ip -brief link | grep -Eq '^lo[[:space:]]+DOWN'; then
  echo "D2_LINUX_NATIVE_NO_GO: network namespace has unexpected active links" >&2
  ip -brief link >&2
  exit 1
fi

# In this namespace X11 must also run here: Xvfb abstract AF_UNIX sockets
# from the host network namespace are not reachable from the child.
if [[ "$(printenv MEDORIGIN_D2_NATIVE_XVFB || true)" != "1" ]]; then
  exec xvfb-run -a -s "-screen 0 1280x800x24" \
    env MEDORIGIN_D2_NATIVE_XVFB=1 bash "$0" --inside "$binary"
fi
unset WAYLAND_DISPLAY
export XDG_SESSION_TYPE=x11
export WINIT_UNIX_BACKEND=x11
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe

log="$(mktemp /tmp/medorigin-native-netns-ui.XXXXXX)"
"$binary" >"$log" 2>&1 &
pid="$!"
cleanup() {
  kill "$pid" 2>/dev/null || true
  rm -f -- "$log"
}
trap cleanup EXIT
for _ in {1..60}; do
  if xwininfo -root -tree 2>/dev/null \
     | grep -Fq "MedOrigin Native Rust"; then
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "D2_LINUX_NATIVE_NO_GO: window appeared but app terminated" >&2
      cat "$log" >&2
      exit 1
    fi
    # Verify the REAL unmodified D2 GUI PID is in our new netns.
    if [[ "$(readlink "/proc/$pid/ns/net")" != "$(readlink /proc/self/ns/net)" ]]; then
      echo "D2_LINUX_NATIVE_NO_GO: GUI PID escaped the isolated network namespace" >&2
      exit 1
    fi
    # A sibling synthetic Python probe runs in the EXACT same namespace.
    # The product binary has no socket code; this cannot prove what any
    # future product-spawned descendants might attempt.
    MEDORIGIN_D2_EXPECT_ISOLATED_NS="$(readlink /proc/self/ns/net)" python3 - <<'PYISOLATED'
import errno
import os
import socket

assert os.readlink("/proc/self/ns/net") == os.environ["MEDORIGIN_D2_EXPECT_ISOLATED_NS"]
attempts = (
    (socket.AF_INET, ("127.0.0.1", 9)),
    (socket.AF_INET, ("192.0.2.1", 9)),  # RFC 5737 documentation-only
    (socket.AF_INET6, ("::1", 9, 0, 0)),
    (socket.AF_INET6, ("2001:db8::1", 9, 0, 0)),  # RFC 3849 documentation-only
)
for family, address in attempts:
    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        with socket.socket(family, kind) as sock:
            sock.settimeout(1)
            try:
                if kind == socket.SOCK_STREAM:
                    sock.connect(address)
                else:
                    sock.sendto(b"synthetic", address)
            except OSError as exc:
                expected = {errno.ENETUNREACH, errno.EHOSTUNREACH}
                if family == socket.AF_INET6:
                    expected.add(errno.EADDRNOTAVAIL)
                if exc.errno not in expected:
                    raise AssertionError(
                        f"Unexpected socket failure: family={family} kind={kind} errno={exc.errno}"
                    ) from exc
            else:
                raise AssertionError(
                    f"Unexpected network allowance: family={family} kind={kind} addr={address}"
                )
print("D2_NATIVE_SAME_NETNS_8_OF_8_IPV4_IPV6_TCP_UDP_DENIED_PASS")
PYISOLATED
    echo "D2_UNMODIFIED_NATIVE_GUI_ROOTLESS_NETNS_IPV4_IPV6_TCP_UDP_NEGATIVE_PASS_NOT_RELEASE"
    echo "D2_UNMODIFIED_NATIVE_GUI_ROOTLESS_NETNS_WINDOW_PASS_NOT_RELEASE"
    exit 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 0.2
done
echo "D2_LINUX_NATIVE_NO_GO: original synthetic native window absent" >&2
cat "$log" >&2
exit 1
