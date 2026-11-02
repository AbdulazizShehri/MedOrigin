"""Reject ambiguous GitHub JSON receipts before any release-gate interpretation.

Offline unit tests; synthetic-only issue metadata and injected subprocess bytes.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import medorigin_release_blocker_ledger as ledger


def parse_raw(raw: bytes) -> ledger.Gate:
    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args=["gh"], returncode=0, stdout=raw)

    return ledger.load_live_issue(662, "synthetic test", runner)


def base_receipt() -> dict[str, object]:
    return {
        "number": 662,
        "title": "Synthetic issue",
        "state": "open",
        "updated_at": "2026-11-02T10:50:00Z",
        "html_url": "https://github.com/AbdulazizShehri/MedOrigin/issues/662",
    }


class AmbiguousReceiptTests(unittest.TestCase):
    def test_duplicate_state_cannot_claim_closed(self) -> None:
        raw = json.dumps(base_receipt()).encode("utf-8")
        raw = raw.replace(b'"state": "open"', b'"state": "open", "state": "closed"')
        self.assertEqual(parse_raw(raw).status, "EVIDENCE_UNAVAILABLE")

    def test_duplicate_identity_cannot_override_issue_number(self) -> None:
        raw = json.dumps(base_receipt()).encode("utf-8")
        raw = raw.replace(b'"number": 662', b'"number": 999, "number": 662')
        self.assertEqual(parse_raw(raw).status, "EVIDENCE_UNAVAILABLE")

    def test_nested_duplicate_keys_are_not_silently_discarded(self) -> None:
        value = base_receipt()
        raw = json.dumps(value).encode("utf-8")
        raw = raw[:-1] + b', "metadata": {"a": 1, "a": 2}}'
        self.assertEqual(parse_raw(raw).status, "EVIDENCE_UNAVAILABLE")

    def test_nonstandard_nan_constant_is_not_a_valid_receipt(self) -> None:
        raw = json.dumps(base_receipt()).encode("utf-8")
        raw = raw[:-1] + b', "metadata": NaN}'
        self.assertEqual(parse_raw(raw).status, "EVIDENCE_UNAVAILABLE")

    def test_impossible_calendar_timestamp_is_invalid(self) -> None:
        value = base_receipt()
        value["updated_at"] = "2026-02-30T10:50:00Z"
        self.assertEqual(
            ledger.parse_issue(662, "synthetic test", value).status,
            "EVIDENCE_INVALID",
        )

    def test_valid_utf8_and_valid_calendar_still_accepted(self) -> None:
        value = base_receipt()
        value["title"] = "Synthetic — اختبار"
        self.assertEqual(
            parse_raw(json.dumps(value, ensure_ascii=False).encode("utf-8")).status,
            "OPEN_BLOCKER",
        )


if __name__ == "__main__":
    unittest.main()
