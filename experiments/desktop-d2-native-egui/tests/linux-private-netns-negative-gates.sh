#!/usr/bin/env bash
# Real Linux namespace negative controls. No network attempts are made by this
# script: it tests refusal paths that must abort before probe socket calls.
set -euo pipefail
if [[ $# -ne 2 ]]; then echo "usage: ... BINARY SHA256" >&2; exit 2; fi
binary="$1"; digest="$2"
probe="$(dirname -- "$0")/linux-private-netns-smoke.py"
hostns="$(readlink /proc/self/ns/net)"
export MEDORIGIN_TEST_BINARY="$binary"
export MEDORIGIN_TEST_SHA="$digest"
export MEDORIGIN_TEST_PROBE="$probe"
export MEDORIGIN_TEST_HOSTNS="$hostns"

assert_json_refusal() {
  local got="$1" expected="$2"
  python3 -c 'import sys,json
d=json.load(sys.stdin)
assert d.get("decision") == "NO_GO", d
assert d.get("reason") == sys.argv[1], d
assert "negative_controls" not in d, d
assert d.get("release_authorized") is False, d
' "$expected" <<< "$got"
  echo "EXPECTED_REFUSAL_PASS=$expected"
}

if output="$(env MEDORIGIN_D2_PRIVATE_NETNS_EXPERIMENT=1 python3 "$probe" --binary "$binary" --sha256 "$digest" --host-netns "$hostns")"; then
  echo "FALSE_SUCCESS_OUTSIDE_NETWORK_NAMESPACE" >&2; exit 2
fi
assert_json_refusal "$output" "NOT_IN_PRIVATE_NETWORK_NAMESPACE"

if output="$(env -u MEDORIGIN_D2_PRIVATE_NETNS_EXPERIMENT python3 "$probe" --binary "$binary" --sha256 "$digest" --host-netns "$hostns")"; then
  echo "FALSE_SUCCESS_WITHOUT_EXPERIMENT_OPT_IN" >&2; exit 2
fi
assert_json_refusal "$output" "EXPLICIT_EXPERIMENT_OPT_IN_MISSING"

# All route/lo mutations occur ONLY inside newly created private user+network
# namespaces, never in the host namespace.
if output="$(unshare --user --map-root-user --net -- sh -c '
  ip -4 route add blackhole 198.51.100.0/24 || exit 8
  MEDORIGIN_D2_PRIVATE_NETNS_EXPERIMENT=1 python3 "$MEDORIGIN_TEST_PROBE" \
    --binary "$MEDORIGIN_TEST_BINARY" --sha256 "$MEDORIGIN_TEST_SHA" --host-netns "$MEDORIGIN_TEST_HOSTNS"
')"; then
  echo "FALSE_SUCCESS_WITH_ROUTE_PRESENT" >&2; exit 2
fi
assert_json_refusal "$output" "UNEXPECTED_NETWORK_ROUTE"

if output="$(unshare --user --map-root-user --net -- sh -c '
  ip link set lo up || exit 8
  MEDORIGIN_D2_PRIVATE_NETNS_EXPERIMENT=1 python3 "$MEDORIGIN_TEST_PROBE" \
    --binary "$MEDORIGIN_TEST_BINARY" --sha256 "$MEDORIGIN_TEST_SHA" --host-netns "$MEDORIGIN_TEST_HOSTNS"
')"; then
  echo "FALSE_SUCCESS_WITH_LOOPBACK_UP" >&2; exit 2
fi
assert_json_refusal "$output" "LOOPBACK_INTERFACE_UP"

echo 'MEDORIGIN_LINUX_PRIVATE_NETNS_FOUR_NEGATIVE_GATES_PASS_NONPUBLISHING'
