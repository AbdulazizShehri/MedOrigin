"""Fail-closed local source tests; no GitHub network or issue mutations."""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_private_release_gate as gate


def alert(number: int, severity: str, package: str = "pillow") -> dict:
    return {
        "number": number,
        "state": "open",
        "dependency": {
            "manifest_path": "uv.lock",
            "scope": "runtime",
            "package": {"name": package, "ecosystem": "pip"},
        },
        "security_advisory": {"severity": severity},
    }


def issues(state: str = "open") -> dict[int, dict]:
    return {number: {"number": number, "state": state} for number in gate.BLOCKER_ISSUES}


class PrivateReleaseGateTests(unittest.TestCase):
    def test_open_issues_and_high_severity_alerts_force_no_go(self):
        result = gate.determine_release_status(
            [
                alert(1, "critical"),
                alert(2, "high"),
                alert(3, "medium", "filelock"),
                alert(4, "low", "setuptools"),
            ],
            issues(),
        )
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["clinical_data_authorized"])
        self.assertEqual(result["dependabot_open_total"], 4)
        self.assertEqual(
            result["dependabot_open_by_severity"],
            {
                "critical": 1,
                "high": 1,
                "medium": 1,
                "low": 1,
            },
        )
        self.assertEqual(result["dependabot_affected_manifests"], {"uv.lock": 4})
        self.assertEqual(result["open_release_blocker_issues"], list(gate.BLOCKER_ISSUES))
        self.assertEqual(
            result["dependency_reachability_to_native_d2"],
            "NOT_DETERMINED_FROM_ALERT_API",
        )

    def test_even_zero_alerts_closed_issues_cannot_self_authorize_release(self):
        result = gate.determine_release_status([], issues("closed"))
        self.assertEqual(result["dependabot_open_total"], 0)
        self.assertEqual(result["open_release_blocker_issues"], [])
        for field in (
            "release_authorized",
            "clinical_data_authorized",
            "independent_security_review_qualified",
            "full_fhir_r4_validator_qualified",
            "native_three_os_packet_isolation_qualified",
            "founder_release_approval_verified",
        ):
            self.assertIs(result[field], False, field)

    def test_reject_duplicate_or_nonopen_alert(self):
        with self.assertRaisesRegex(gate.QualificationRefused, "duplicate"):
            gate.determine_release_status([alert(1, "high"), alert(1, "high")], issues())
        duplicate = alert(2, "critical")
        duplicate["state"] = "dismissed"
        with self.assertRaisesRegex(gate.QualificationRefused, "nonopen"):
            gate.determine_release_status([duplicate], issues())

    def test_reject_missing_advisory_or_unknown_severity(self):
        sample = alert(3, "critical")
        del sample["security_advisory"]
        with self.assertRaisesRegex(gate.QualificationRefused, "advisory"):
            gate.determine_release_status([sample], issues())
        with self.assertRaisesRegex(gate.QualificationRefused, "scope"):
            gate.determine_release_status([alert(3, "UNKNOWN")], issues())

    def test_refuse_incomplete_issue_set_and_forged_states(self):
        snapshot = issues()
        del snapshot[676]
        with self.assertRaisesRegex(gate.QualificationRefused, "incomplete"):
            gate.determine_release_status([], snapshot)
        snapshot = issues()
        snapshot[662]["number"] = 603
        with self.assertRaisesRegex(gate.QualificationRefused, "identity"):
            gate.determine_release_status([], snapshot)
        snapshot = issues()
        snapshot[662]["state"] = "unknown"
        with self.assertRaisesRegex(gate.QualificationRefused, "state"):
            gate.determine_release_status([], snapshot)

    def test_gh_resource_cannot_read_another_repository(self):
        with self.assertRaisesRegex(gate.QualificationRefused, "unapproved"):
            gate.gh_json("repos/another/repo/issues/1")

    def test_live_gate_always_exits_nonzero_with_complete_sources(self):
        with (
            patch.object(gate, "live_security_snapshot", return_value=([], issues("closed"))),
            redirect_stdout(io.StringIO()) as stream,
        ):
            code = gate.main()
        self.assertEqual(code, 2)
        self.assertIn("MEDORIGIN_PRIVATE_RELEASE_GUARD_ENFORCED_NO_GO", stream.getvalue())
        self.assertNotIn('"release_authorized": true', stream.getvalue())

    def test_live_gate_exits_nonzero_if_github_api_unavailable(self):
        with (
            patch.object(
                gate,
                "live_security_snapshot",
                side_effect=gate.QualificationRefused("github_api_unavailable"),
            ),
            redirect_stderr(io.StringIO()) as stream,
        ):
            code = gate.main()
        self.assertEqual(code, 2)
        self.assertIn("NO_GO_EVIDENCE_UNAVAILABLE", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
