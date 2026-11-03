#!/usr/bin/env python3
"""Fail-closed consistency check for MedOrigin's Windows D1 egress snapshots.

This checks *only* the structure and internal arithmetic of actual lifecycle
output, not the truth of OS process/network measurements. It can never grant
release or network-isolation approval, even for zero observed connections.
"""
import argparse
import json
from pathlib import Path
import re
import sys

REPORT_SCHEMA = "medorigin-d1-real-windows-egress-snapshot-series-v1"
SHA = re.compile(r"[0-9a-fA-F]{64}\Z")
OBSERVED = "D1_OBSERVED_EXTERNAL_TCP_NO_GO"
NOT_OBSERVED = "NO_EXTERNAL_TCP_OBSERVED_PACKET_DNS_UNPROVEN"


def require(condition, code):
    if not condition:
        raise ValueError(code)


def count(value, name, maximum=1000000):
    require(type(value) is int and 0 <= value <= maximum, "INVALID_" + name)
    return value


def assess(packet, expected_sha256):
    result = {
        "schema": "medorigin-d1-egress-evidence-consistency-v1",
        "decision": "NO_GO",
        "internal_consistency_checked": False,
        "release_authorized": False,
        "os_packet_egress_denial_proven": False,
        "dns_udp_denial_proven": False,
    }
    try:
        require(type(packet) is dict, "INVALID_ROOT")
        require(packet.get("schema") == REPORT_SCHEMA, "INVALID_REPORT_SCHEMA")
        require(type(expected_sha256) is str and SHA.fullmatch(expected_sha256), "INVALID_EXPECTED_SHA")
        digest = packet.get("root_executable_sha256")
        require(type(digest) is str and SHA.fullmatch(digest), "INVALID_REPORTED_SHA")
        require(digest.lower() == expected_sha256.lower(), "SOURCE_EXECUTABLE_SHA_MISMATCH")
        for key in ("release_authorized", "os_packet_denial_proven", "dns_udp_denial_proven", "host_policy_modified"):
            require(packet.get(key) is False, "UNSAFE_OR_MISSING_" + key.upper())
        require(packet.get("decision") == "NO_GO", "UNSAFE_REPORT_DECISION")
        require(packet.get("actual_runtime_launched") is True, "RUNTIME_NOT_PROVEN_LAUNCHED")
        require(packet.get("owned_root_stopped") is True, "OWNED_ROOT_SHUTDOWN_UNVERIFIED")
        expected = count(packet.get("snapshots_requested"), "SNAPSHOTS_REQUESTED", 20)
        require(expected >= 2, "INSUFFICIENT_SNAPSHOTS_REQUESTED")
        completed = count(packet.get("snapshots_completed"), "SNAPSHOTS_COMPLETED", expected)
        require(completed == expected, "INCOMPLETE_SNAPSHOT_SERIES")
        cases = packet.get("cases")
        require(type(cases) is list and len(cases) == expected, "INCONSISTENT_CASE_COUNT")
        observed = count(packet.get("snapshots_with_observed_external_tcp"), "OBSERVED_SNAPSHOT_COUNT", expected)
        max_tcp = count(packet.get("maximum_external_tcp"), "MAX_EXTERNAL_TCP")
        max_processes = count(packet.get("maximum_descendant_inclusive_processes"), "MAX_OBSERVED_PROCESSES")
        require(max_processes >= 1, "NO_ROOT_PROCESS_OBSERVED")
        seen = 0
        actual_max_tcp = 0
        actual_max_processes = 0
        for index, sample in enumerate(cases, 1):
            require(type(sample) is dict, "INVALID_SAMPLE")
            require(type(sample.get("sample")) is int and sample["sample"] == index, "BAD_SAMPLE_ORDER")
            require(sample.get("decision") == "NO_GO", "UNSAFE_SAMPLE_DECISION")
            tcp = count(sample.get("external_tcp_all_states"), "SAMPLE_EXTERNAL_TCP")
            established = count(sample.get("external_established_tcp"), "SAMPLE_ESTABLISHED_TCP")
            processes = count(sample.get("observed_processes"), "SAMPLE_PROCESS_COUNT")
            count(sample.get("udp_endpoints"), "SAMPLE_UDP_ENDPOINTS")
            require(processes >= 1 and established <= tcp, "IMPOSSIBLE_SAMPLE_COUNTS")
            reason = sample.get("reason")
            if reason == OBSERVED:
                require(tcp > 0, "EXTERNAL_TCP_MARKER_WITHOUT_TCP")
                seen += 1
            elif reason == NOT_OBSERVED:
                require(tcp == 0, "HIDDEN_EXTERNAL_TCP_IN_CLEAN_SAMPLE")
            else:
                raise ValueError("INCOMPLETE_OR_UNRECOGNIZED_SAMPLE")
            actual_max_tcp = max(actual_max_tcp, tcp)
            actual_max_processes = max(actual_max_processes, processes)
        require(observed == seen and max_tcp == actual_max_tcp and max_processes == actual_max_processes,
                "SUMMARY_ARITHMETIC_MISMATCH")
        required_reason = "OBSERVED_EXTERNAL_TCP_NO_GO" if seen else "NO_EXTERNAL_TCP_OBSERVED_OS_DENIAL_UNPROVEN"
        require(packet.get("reason") == required_reason, "INCONSISTENT_SUMMARY_REASON")
        result["internal_consistency_checked"] = True
        result["observation"] = "EXTERNAL_TCP_OBSERVED" if seen else "NO_EXTERNAL_TCP_OBSERVED_UNPROVEN"
        result["reason"] = "INTERNALLY_CONSISTENT_NOT_ISOLATION_EVIDENCE"
        result["snapshots_checked"] = expected
        result["observed_external_tcp_snapshots"] = seen
    except (ValueError, TypeError, KeyError) as exc:
        result["reason"] = str(exc) if isinstance(exc, ValueError) else "MALFORMED_REPORT"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        require(args.input.is_file() and args.input.stat().st_size <= 131072, "MISSING_OR_OVERSIZED_REPORT")
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = assess(data, args.expected_sha256)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        result = {
            "schema": "medorigin-d1-egress-evidence-consistency-v1",
            "decision": "NO_GO",
            "internal_consistency_checked": False,
            "release_authorized": False,
            "os_packet_egress_denial_proven": False,
            "dns_udp_denial_proven": False,
            "reason": "REPORT_INPUT_UNREADABLE_OR_INVALID",
        }
    print(json.dumps(result, sort_keys=True))
    # Nonzero even for internally consistent, zero-socket observations.
    return 2 if result["internal_consistency_checked"] else 4


if __name__ == "__main__":
    sys.exit(main())
