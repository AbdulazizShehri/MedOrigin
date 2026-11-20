#!/usr/bin/env bash
# Nonclinical native GUI smoke: observes a real X11 window, not security isolation.
set -euo pipefail
if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "LINUX_GUI_SMOKE_REFUSED: exact executable argument required" >&2
  exit 2
fi
bin="$1"
if [[ "$(basename "$bin")" != "medorigin-desktop-d2-native-egui" ]]; then
  echo "LINUX_GUI_SMOKE_REFUSED: unexpected executable name" >&2
  exit 2
fi
test -x "$bin"
command -v xwininfo >/dev/null
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
unset WAYLAND_DISPLAY
log="/tmp/medorigin-d2-synthetic-x11-smoke-$$.log"
"$bin" > "$log" 2>&1 &
pid=$!
cleanup() {
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  rm -f "$log"
}
trap cleanup EXIT
for attempt in $(seq 1 45); do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "LINUX_GUI_SMOKE_NO_GO: native process exited" >&2
    tail -20 "$log" >&2 || true
    exit 3
  fi
  if xwininfo -root -tree 2>/dev/null | grep -Fq "MedOrigin Native Rust"; then
    echo "LINUX_SYNTHETIC_NATIVE_X11_WINDOW_OBSERVED"
    echo "LINUX_GUI_SMOKE_PASS_NOT_CLINICAL_RELEASE"
    exit 0
  fi
  sleep 0.25
done
echo "LINUX_GUI_SMOKE_NO_GO: app window not observed" >&2
tail -20 "$log" >&2 || true
exit 4
