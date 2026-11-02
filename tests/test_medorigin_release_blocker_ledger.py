"""No-account, no-network tests for the read-only MedOrigin release blocker ledger."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import medorigin_release_blocker_ledger as ledger


def receipt(number: int, state: str = "open") -> dict[str, object]:
    return {
        "number": number,
        "state": state,
        "title": "Synthetic test issue",
        "updated_at": "2026-11-02T10:50:00Z",
        "html_url": f"https://github.com/{ledger.REPO}/issues/{number}",
    }


def report_gates(report: dict[str, object]) -> list[dict[str, object]]:
    value = report["gates"]
    if not isinstance(value, list) or not all(isinstance(g, dict) for g in value):
        raise AssertionError("Invalid internal release gate report type")
    return cast(list[dict[str, object]], value)


class LedgerTests(unittest.TestCase):
    def test_all_live_open_blockers_remain_no_go(self) -> None:
        def fake(num: int, reason: str) -> ledger.Gate:
            return ledger.parse_issue(num, reason, receipt(num))

        report = ledger.build_report(fake)
        gates = report_gates(report)
        self.assertEqual(report["state"], "PUBLICATION_NO_GO")
        self.assertFalse(report["publication_authorized"])
        self.assertFalse(report["artifact_signature_verified"])
        self.assertEqual([g["issue"] for g in gates], [574, 603, 622, 662, 673, 676])
        self.assertTrue(all(g["status"] == "OPEN_BLOCKER" for g in gates))

    def test_even_all_closed_issues_cannot_authorize_release(self) -> None:
        def fake(num: int, reason: str) -> ledger.Gate:
            return ledger.parse_issue(num, reason, receipt(num, "closed"))

        report = ledger.build_report(fake)
        self.assertFalse(report["publication_authorized"])
        self.assertFalse(report["independent_security_review_attested"])
        self.assertEqual(report["state"], "PUBLICATION_NO_GO")
        self.assertTrue(
            all(
                g["status"] == "CLOSED_REQUIRES_INDEPENDENT_ATTESTATION"
                for g in report_gates(report)
            )
        )

    def test_strict_mode_is_fail_closed_by_design(self) -> None:
        def reader(n: int, r: str) -> ledger.Gate:
            return ledger.parse_issue(n, r, receipt(n))

        with redirect_stdout(StringIO()) as output:
            code = ledger.main(["--strict"], reader)
        self.assertEqual(code, 2)
        self.assertIn("PUBLICATION_NO_GO", output.getvalue())

    def test_json_mode_contains_no_approval_flag(self) -> None:
        def reader(n: int, r: str) -> ledger.Gate:
            return ledger.parse_issue(n, r, receipt(n))

        with redirect_stdout(StringIO()) as output:
            code = ledger.main(["--json"], reader)
        self.assertEqual(code, 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["schema"], "MEDORIGIN_RELEASE_BLOCKER_LEDGER_V1")
        self.assertIs(data["publication_authorized"], False)

    def test_utf8_non_ascii_issue_json_is_safe_on_windows(self) -> None:
        value = receipt(662)
        value["title"] = "Network denied — اختبار عربي"
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")

        def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(args=["gh"], returncode=0, stdout=raw)

        result = ledger.load_live_issue(662, "network", runner)
        self.assertEqual(result.status, "OPEN_BLOCKER")

    def test_bad_utf8_and_missing_stdout_fail_closed_without_traceback(self) -> None:
        for raw in (bytes([255]), None):

            def runner(
                *args: object, payload: bytes | None = raw, **kwargs: object
            ) -> subprocess.CompletedProcess[bytes]:
                return subprocess.CompletedProcess(args=["gh"], returncode=0, stdout=payload)

            result = ledger.load_live_issue(662, "network", runner)
            self.assertEqual(result.status, "EVIDENCE_UNAVAILABLE")

    def test_unknown_issue_state_denied(self) -> None:
        value = receipt(662)
        value["state"] = "not-a-state"
        self.assertEqual(ledger.parse_issue(662, "test", value).status, "EVIDENCE_INVALID")

    def test_issue_number_mismatch_denied(self) -> None:
        value = receipt(662)
        value["number"] = 673
        self.assertEqual(ledger.parse_issue(662, "test", value).status, "EVIDENCE_INVALID")

    def test_boolean_issue_number_not_accepted(self) -> None:
        value = receipt(662)
        value["number"] = True
        self.assertEqual(ledger.parse_issue(662, "test", value).status, "EVIDENCE_INVALID")

    def test_pr_disguised_as_issue_denied(self) -> None:
        value = receipt(662, "closed")
        value["pull_request"] = {"url": "https://invalid.invalid"}
        self.assertEqual(ledger.parse_issue(662, "test", value).status, "EVIDENCE_INVALID")

    def test_cross_repo_url_denied(self) -> None:
        value = receipt(662)
        value["html_url"] = "https://github.com/other/repo/issues/662"
        self.assertEqual(ledger.parse_issue(662, "test", value).status, "EVIDENCE_INVALID")

    def test_missing_timestamp_denied(self) -> None:
        value = receipt(662)
        del value["updated_at"]
        self.assertEqual(ledger.parse_issue(662, "test", value).status, "EVIDENCE_INVALID")

    def test_gh_error_returns_unavailable_without_leaking_stderr(self) -> None:
        def failed_runner(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            self.assertEqual(cmd[:3], ["gh", "api", "--method"])
            self.assertEqual(cmd[3], "GET")
            self.assertEqual(cmd[-1], f"repos/{ledger.REPO}/issues/662")
            self.assertFalse(kwargs["check"])
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout=b"", stderr=b"TOKEN=secret"
            )

        status = ledger.load_live_issue(662, "test", failed_runner)
        self.assertEqual(status.status, "EVIDENCE_UNAVAILABLE")
        self.assertNotIn("secret", json.dumps(status.to_dict()))

    def test_expired_gh_timeout_returns_unavailable(self) -> None:
        def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            raise subprocess.TimeoutExpired(cmd="gh", timeout=20)

        self.assertEqual(
            ledger.load_live_issue(662, "test", timeout).status,
            "EVIDENCE_UNAVAILABLE",
        )

    def test_unavailable_causes_json_no_go_and_exit3(self) -> None:
        def reader(n: int, r: str) -> ledger.Gate:
            if n == 662:
                return ledger.Gate(
                    n,
                    r,
                    "EVIDENCE_UNAVAILABLE",
                    "unknown",
                    None,
                    f"https://github.com/{ledger.REPO}/issues/{n}",
                    "github_read_failed",
                )
            return ledger.parse_issue(n, r, receipt(n))

        with redirect_stdout(StringIO()) as output:
            code = ledger.main(["--json"], reader)
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(output.getvalue())["state"], "EVIDENCE_INCOMPLETE_NO_GO")


if __name__ == "__main__":
    unittest.main()
