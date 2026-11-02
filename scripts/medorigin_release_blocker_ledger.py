#!/usr/bin/env python3
"""Read-only MedOrigin software release blocker ledger.

An issue being closed is NOT an approval, independent review or signed artifact.
This program can never authorize publication and performs no mutation/API writes.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

REPO = "AbdulazizShehri/MedOrigin"
GATES = {
    574: "founder version, package identity and release decision",
    603: "independent security, artifact and source review",
    622: "optional research dependency and advisory qualification",
    662: "WebView2 background OS network-egress attribution",
    673: "Linux AccessKit and zbus maintenance acceptance",
    676: "spoken VoiceOver and independent accessibility review",
}
REQUIRED_APPROVALS = (
    "signed owner release and exact artifact authorization",
    "independent source and artifact security review",
    "approved package identity and ADR-0044/0045 disposition",
    "platform-specific OS network and accessibility evidence",
)


@dataclass(frozen=True)
class Gate:
    issue: int
    reason: str
    status: str
    source_state: str
    updated_at: str | None
    url: str
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "issue": self.issue,
            "reason": self.reason,
            "status": self.status,
            "source_state": self.source_state,
            "updated_at": self.updated_at,
            "url": self.url,
            "error": self.error,
        }


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous JSON members, including nested and escaped duplicates."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object member")
        result[key] = value
    return result


def reject_nonstandard_constant(value: str) -> object:
    """GitHub JSON must not contain NaN or Infinity extensions."""
    raise ValueError("nonstandard JSON constant")


def valid_utc_timestamp(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def parse_issue(number: int, reason: str, payload: object) -> Gate:
    """Fail closed on incomplete/mismatched/PR data, even if state says closed."""
    url = f"https://github.com/{REPO}/issues/{number}"
    if (
        not isinstance(payload, dict)
        or payload.get("number") != number
        or type(payload.get("number")) is not int
        or "pull_request" in payload
        or not isinstance(payload.get("title"), str)
        or not payload["title"].strip()
        or payload.get("state") not in ("open", "closed")
        or not isinstance(payload.get("html_url"), str)
        or payload["html_url"] != url
    ):
        return Gate(
            number, reason, "EVIDENCE_INVALID", "unknown", None, url, "invalid_issue_receipt"
        )
    updated = payload.get("updated_at")
    if not isinstance(updated, str) or not valid_utc_timestamp(updated):
        return Gate(
            number, reason, "EVIDENCE_INVALID", "unknown", None, url, "missing_or_invalid_timestamp"
        )
    state = payload["state"]
    return Gate(
        number,
        reason,
        "OPEN_BLOCKER" if state == "open" else "CLOSED_REQUIRES_INDEPENDENT_ATTESTATION",
        state,
        updated,
        url,
    )


def load_live_issue(
    number: int,
    reason: str,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> Gate:
    """Only the fixed repository issue-read endpoint; never shell or write verbs."""
    url = f"https://github.com/{REPO}/issues/{number}"
    try:
        receipt = runner(
            ["gh", "api", "--method", "GET", f"repos/{REPO}/issues/{number}"],
            capture_output=True,
            text=False,
            timeout=20,
            check=False,
        )
        if receipt.returncode != 0:
            return Gate(
                number, reason, "EVIDENCE_UNAVAILABLE", "unknown", None, url, "github_read_failed"
            )
        # GitHub output is UTF-8. Parse bytes directly to avoid Windows cp1252
        # decoding crashes when an issue body contains Unicode characters.
        payload = json.loads(
            receipt.stdout,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonstandard_constant,
        )
    except (OSError, ValueError, TypeError, UnicodeError, subprocess.TimeoutExpired):
        return Gate(
            number, reason, "EVIDENCE_UNAVAILABLE", "unknown", None, url, "github_read_failed"
        )
    return parse_issue(number, reason, payload)


def build_report(reader: Callable[[int, str], Gate] = load_live_issue) -> dict[str, object]:
    gates = [reader(number, reason) for number, reason in GATES.items()]
    invalid = any(g.status in ("EVIDENCE_UNAVAILABLE", "EVIDENCE_INVALID") for g in gates)
    return {
        "schema": "MEDORIGIN_RELEASE_BLOCKER_LEDGER_V1",
        "repository": REPO,
        "scope": "developer_beta_candidate_synthetic_only",
        "state": "EVIDENCE_INCOMPLETE_NO_GO" if invalid else "PUBLICATION_NO_GO",
        "publication_authorized": False,
        "artifact_signature_verified": False,
        "independent_security_review_attested": False,
        "required_approvals_not_attested": list(REQUIRED_APPROVALS),
        "gates": [g.to_dict() for g in gates],
        "disclaimer": (
            "Closing issues or passing CI cannot authorize a tag, merge, installer, "
            "registry upload or clinical use."
        ),
    }


def main(
    argv: list[str] | None = None, reader: Callable[[int, str], Gate] = load_live_issue
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit structured read-only JSON")
    parser.add_argument(
        "--strict", action="store_true", help="exit nonzero while release is blocked"
    )
    args = parser.parse_args(argv)
    report = build_report(reader)
    if args.json:
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print(f"{report['state']} — MedOrigin Developer Beta (no publication authority)")
        gates = report["gates"]
        assert isinstance(gates, list)
        for g in gates:
            assert isinstance(g, dict)
            print(f"#{g['issue']}: {g['status']} — {g['reason']}")
        print("Independent approvals and signed artifact authority NOT ATTESTED.")
    # Strict mode is useful as a negative control; it is expected to fail until
    # an independently governed release path replaces this source-only ledger.
    if args.strict:
        return 2 if report["state"] == "PUBLICATION_NO_GO" else 3
    return 3 if report["state"] == "EVIDENCE_INCOMPLETE_NO_GO" else 0


if __name__ == "__main__":
    sys.exit(main())
