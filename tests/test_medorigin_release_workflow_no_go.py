"""Read-only release workflow no-publication contract; no tags, APIs or writes."""

from __future__ import annotations

import re
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts import medorigin_release_blocker_ledger as ledger

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".github" / "workflows" / "release.yml"


def job(name: str, text: str) -> str:
    # GitHub Actions jobs are two-space-indented; reject a missing or duplicate
    # key rather than accepting a token hidden in a comment or step.
    pattern = re.compile(rf"(?m)^  {re.escape(name)}:\s*\n")
    found = list(pattern.finditer(text))
    if len(found) != 1:
        raise AssertionError(f"Expected one real job entry for {name}; saw {len(found)}")
    start = found[0].start()
    end_match = re.search(r"(?m)^  [a-z][a-z0-9-]*:\s*\n", text[found[0].end() :])
    end = found[0].end() + end_match.start() if end_match else len(text)
    return text[start:end]


class PublicationNoGoWorkflowTests(unittest.TestCase):
    source: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = RELEASE.read_text(encoding="utf-8")

    def test_tag_only_release_trigger_is_preserved(self) -> None:
        self.assertIn('  push:\n    tags:\n      - "v*"', self.source)
        self.assertIn("permissions:\n  contents: read\n", self.source)

    def test_real_publication_job_requires_independent_no_go(self) -> None:
        release = job("github-release", self.source)
        self.assertIn("needs: [quality, build, install-smoke, publication-readiness]", release)
        self.assertIn("vars.GITHUB_RELEASE_PUBLISH_ENABLED == 'true'", release)
        self.assertIn("contents: write", release)

    def test_guard_has_fixed_tag_push_gate_and_no_write_capability(self) -> None:
        guard = job("publication-readiness", self.source)
        self.assertIn(
            "if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')",
            guard,
        )
        self.assertIn("permissions:\n      contents: read\n      issues: read", guard)
        self.assertNotIn("contents: write", guard)
        self.assertNotIn("id-token: write", guard)
        self.assertNotIn("upload-artifact", guard)
        self.assertNotIn("action-gh-release", guard)
        self.assertIn("persist-credentials: false", guard)
        self.assertIn("ref: ${{ github.sha }}", guard)

    def test_guard_only_calls_read_only_failing_strict_ledger(self) -> None:
        guard = job("publication-readiness", self.source)
        self.assertIn("GH_TOKEN: ${{ github.token }}", guard)
        self.assertIn("python3 scripts/medorigin_release_blocker_ledger.py --strict", guard)
        self.assertNotIn("|| true", guard)
        self.assertNotIn("continue-on-error", guard)

    def test_testpypi_is_transitively_blocked_by_release(self) -> None:
        pypi = job("testpypi-publish", self.source)
        self.assertIn("needs: github-release", pypi)
        self.assertIn("vars.TESTPYPI_PUBLISH_ENABLED == 'true'", pypi)

    def test_all_closed_issues_still_produce_no_go_strict_exit(self) -> None:
        def independent_read(number: int, reason: str) -> ledger.Gate:
            return ledger.Gate(
                number,
                reason,
                "CLOSED_REQUIRES_INDEPENDENT_ATTESTATION",
                "closed",
                "2026-11-02T10:00:00Z",
                f"https://github.com/{ledger.REPO}/issues/{number}",
            )

        with redirect_stdout(StringIO()):
            rc = ledger.main(["--strict"], independent_read)
        self.assertEqual(rc, 2)
        report = ledger.build_report(independent_read)
        self.assertIs(report["publication_authorized"], False)
        self.assertIs(report["independent_security_review_attested"], False)

    def test_missing_issues_still_fail_closed(self) -> None:
        def no_read(number: int, reason: str) -> ledger.Gate:
            return ledger.Gate(
                number,
                reason,
                "EVIDENCE_UNAVAILABLE",
                "unknown",
                None,
                f"https://github.com/{ledger.REPO}/issues/{number}",
                "github_read_failed",
            )

        with redirect_stdout(StringIO()):
            rc = ledger.main(["--strict"], no_read)
        self.assertEqual(rc, 3)
        self.assertEqual(ledger.build_report(no_read)["state"], "EVIDENCE_INCOMPLETE_NO_GO")


if __name__ == "__main__":
    unittest.main()
