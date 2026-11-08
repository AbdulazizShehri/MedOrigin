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
    echo "D2_UNMODIFIED_NATIVE_GUI_ROOTLESS_NETNS_WINDOW_PASS_NOT_RELEASE"
    exit 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 0.2
done
echo "D2_LINUX_NATIVE_NO_GO: original synthetic native window absent" >&2
cat "$log" >&2
exit 1
