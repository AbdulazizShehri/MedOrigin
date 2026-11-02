#!/usr/bin/env bash
# One-shot nonpublishing actual D2 Linux GUI network namespace smoke.
# This does not install firewall rules, elevate, contact network endpoints,
# or establish Windows/D1, macOS, general production or clinical readiness.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: bash linux-private-netns-smoke.sh EXACT_LINUX_D2_ELF SHA256" >&2
  exit 2
fi
binary="$1"
pinned_sha="$2"
test -f "$binary" || { echo "EXACT_ELF_MISSING" >&2; exit 2; }
test "$(basename -- "$binary")" = "medorigin-desktop-d2-native-egui" || { echo "WRONG_ELF_NAME" >&2; exit 2; }
[[ "$pinned_sha" =~ ^[0-9a-fA-F]{64}$ ]] || { echo "INVALID_EXPECTED_SHA" >&2; exit 2; }
test "$(sha256sum -- "$binary" | cut -d ' ' -f 1)" = "$(printf '%s' "$pinned_sha" | tr A-F a-f)" || { echo "ELF_SHA_MISMATCH" >&2; exit 2; }
for tool in unshare xvfb-run dbus-run-session ip xwininfo python3 timeout sha256sum; do
  command -v "$tool" >/dev/null || { echo "MISSING_TOOL:$tool" >&2; exit 2; }
done
host_netns="$(readlink /proc/self/ns/net)"
[[ "$host_netns" =~ ^net:\[[0-9]+\]$ ]] || { echo "UNPINNABLE_HOST_NAMESPACE" >&2; exit 2; }

# New user + network namespaces BEFORE launching Xvfb, D-Bus or the app.
# Socket attempts only occur inside child AFTER it verifies namespace,
# one DOWN loopback-only interface and no IPv4/IPv6 routes via Netlink.
unset WAYLAND_DISPLAY WAYLAND_SOCKET
timeout --signal=TERM --kill-after=5s 55s \
  unshare --user --map-root-user --net -- \
  xvfb-run -a -s "-screen 0 1280x800x24" \
  dbus-run-session -- \
  env MEDORIGIN_D2_PRIVATE_NETNS_EXPERIMENT=1 \
  python3 "$(dirname -- "$0")/linux-private-netns-smoke.py" \
    --binary "$binary" --sha256 "$pinned_sha" --host-netns "$host_netns"
