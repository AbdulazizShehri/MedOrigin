"""Offline evidence validator contract tests: all decisions remain non-releasing."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from verify_offline_evidence import evaluate


def packet():
    return {
        "schema": "medorigin-offline-evidence-v1",
        "source_commit": "a" * 40,
        "binary_sha256": "b" * 64,
        "clinical_data_used": False,
        "independent_review": True,
        "gates": {
            f"NET-{i:02}": {"status": "PASS", "evidence": ["test-only-log.json"], "reviewer": "Independent reviewer"}
            for i in range(1, 10)
        },
    }


class TestOfflineEvidence(unittest.TestCase):
    def test_complete_never_authorizes_release(self):
        result = evaluate(packet())
        self.assertEqual(result["decision"], "EVIDENCE_COMPLETE_REVIEW_REQUIRED")
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["zero_egress_proven"])

    def test_missing_gate_fails(self):
        p = packet()
        del p["gates"]["NET-09"]
        self.assertEqual(evaluate(p)["decision"], "NO_GO")

    def test_unknown_gate_fails(self):
        p = packet()
        p["gates"]["NET-10"] = {"status": "PASS", "evidence": ["x"], "reviewer": "z"}
        self.assertEqual(evaluate(p)["decision"], "NO_GO")

    def test_no_evidence_fails(self):
        p = packet()
        p["gates"]["NET-06"]["evidence"] = []
        self.assertEqual(evaluate(p)["decision"], "NO_GO")

    def test_string_review_fails(self):
        p = packet()
        p["independent_review"] = "true"
        self.assertEqual(evaluate(p)["decision"], "NO_GO")

    def test_boolean_status_fails(self):
        p = packet()
        p["gates"]["NET-02"]["status"] = True
        self.assertEqual(evaluate(p)["decision"], "NO_GO")

    def test_invalid_root_fails(self):
        self.assertEqual(evaluate([])["decision"], "NO_GO")

    def test_incorrect_sha_fails(self):
        p = packet()
        p["binary_sha256"] = "bad"
        self.assertEqual(evaluate(p)["decision"], "NO_GO")

    def test_missing_clinical_attestation_fails(self):
        p = packet()
        del p["clinical_data_used"]
        self.assertEqual(evaluate(p)["decision"], "NO_GO")

    def test_malformed_json_cli_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packet.json"
            path.write_text("{bad", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("verify_offline_evidence.py")), str(path)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["decision"], "NO_GO")


if __name__ == "__main__":
    unittest.main()
