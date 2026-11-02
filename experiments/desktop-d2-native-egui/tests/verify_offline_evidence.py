#!/usr/bin/env python3
"""Fail-closed validation of a self-reported offline evidence packet.

Does not capture network traffic, enforce OS policy or authorize release.
"""
import argparse
import json
import re
from pathlib import Path

GATES = tuple(f"NET-{i:02}" for i in range(1, 10))


def evaluate(packet):
    problems = []
    if type(packet) is not dict:
        return {"decision": "NO_GO", "problems": ["root must be an object"], "release_authorized": False, "zero_egress_proven": False}
    if packet.get("schema") != "medorigin-offline-evidence-v1":
        problems.append("invalid evidence schema")
    if not isinstance(packet.get("source_commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", packet["source_commit"]):
        problems.append("missing exact source commit")
    if not isinstance(packet.get("binary_sha256"), str) or not re.fullmatch(r"[0-9a-fA-F]{64}", packet["binary_sha256"]):
        problems.append("missing exact binary SHA-256")
    if packet.get("clinical_data_used") is not False:
        problems.append("clinical data restriction not attested")
    if packet.get("independent_review") is not True:
        problems.append("independent review unverified")
    results = packet.get("gates")
    if type(results) is not dict:
        results = {}
        problems.append("missing gates object")
    gate_out = {}
    for gate in GATES:
        item = results.get(gate)
        if type(item) is not dict:
            gate_out[gate] = "UNKNOWN"
            problems.append(f"{gate}: missing evidence object")
            continue
        status = item.get("status")
        evidence = item.get("evidence")
        reviewer = item.get("reviewer")
        if status != "PASS" or type(evidence) is not list or not evidence or not all(type(s) is str and s.strip() and len(s) <= 256 for s in evidence) or type(reviewer) is not str or not reviewer.strip():
            gate_out[gate] = "FAIL" if status == "FAIL" else "UNKNOWN"
            problems.append(f"{gate}: not independently evidenced PASS")
        else:
            gate_out[gate] = "PASS"
    for extra in sorted(set(results) - set(GATES)):
        problems.append(f"unknown gate: {extra}")
    return {
        "decision": "EVIDENCE_COMPLETE_REVIEW_REQUIRED" if not problems else "NO_GO",
        "gates": gate_out,
        "problems": problems,
        "release_authorized": False,
        "zero_egress_proven": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.packet.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(json.dumps({"decision": "NO_GO", "problems": [f"invalid packet: {type(error).__name__}"], "release_authorized": False}))
        return 2
    result = evaluate(data)
    print(json.dumps(result, indent=2, sort_keys=True))
    # A self-attested packet cannot produce a successful CI release gate.\n    return 3 if result["decision"] == "EVIDENCE_COMPLETE_REVIEW_REQUIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
