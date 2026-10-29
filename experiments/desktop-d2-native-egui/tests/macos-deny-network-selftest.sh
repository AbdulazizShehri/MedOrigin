#!/usr/bin/env bash
# Source-only loopback denial regression, NO external network, no app launched.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "D2_MAC_SANDBOX_UNSUPPORTED_HOST" >&2
  exit 2
fi
policy="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/macos-deny-network.sb"
[[ -f "$policy" ]] || { echo "D2_MAC_POLICY_MISSING" >&2; exit 2; }
[[ -x /usr/bin/sandbox-exec ]] || { echo "D2_MAC_SANDBOX_EXEC_UNAVAILABLE" >&2; exit 2; }
python="$(command -v python3)"
output="$(/usr/bin/sandbox-exec -f "$policy" "$python" -c '
import errno
import socket
import sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(("127.0.0.1", 9))
except PermissionError as exc:
    if exc.errno == errno.EPERM:
        print("D2_MAC_SANDBOX_DENIED_TCP_EPERM")
        sys.exit(0)
    print("D2_MAC_SANDBOX_UNEXPECTED_PERMISSION_ERROR")
    sys.exit(1)
except OSError as exc:
    print("D2_MAC_SANDBOX_NETWORK_NOT_DENIED", exc.errno)
    sys.exit(1)
else:
    print("D2_MAC_SANDBOX_UNEXPECTED_CONNECT")
    sys.exit(1)
' 2>&1)" || { echo "$output" >&2; exit 1; }
[[ "$output" == "D2_MAC_SANDBOX_DENIED_TCP_EPERM" ]] || {
  echo "D2_MAC_SANDBOX_UNEXPECTED_RESULT: $output" >&2
  exit 1
}
echo "D2_MAC_SANDBOX_POLICY_LOOPBACK_DENIAL_PASS (synthetic only; no egress certification)"
