"""Portable denial tests for the source-pinned Mac-only Core→D2 QA runner."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_sandboxed_synthetic_core as bridge


class SandboxedCoreBridgeContractTests(unittest.TestCase):
    def sample(self, label: str = "known") -> dict:
        return {
            "created_at": bridge.TIMESTAMP,
            "errors": [],
            "format_version": "fhirkit-validation-report/v1",
            "input_hash": bridge.PINNED_CASES[label][0],
            "report_id": "",
            "status": "not_validated",
            "validator_name": "medscale-fhirkit-local",
            "validator_version": "0.1.0",
            "warnings": [bridge.WARNING],
        }

    def test_exact_known_and_unknown_core_reports_admitted_as_unvalidated(self):
        for label in bridge.PINNED_CASES:
            with self.subTest(label=label):
                packet = self.sample(label)
                bridge.check_core_report(bridge.canonical(packet), packet["input_hash"])

    def test_false_valid_and_invalid_status_are_both_refused(self):
        for status in ("valid", "invalid", "validated", "indeterminate", ""):
            with self.subTest(status=status):
                packet = self.sample()
                packet["status"] = status
                with self.assertRaises(ValueError):
                    bridge.check_core_report(
                        bridge.canonical(packet), bridge.PINNED_CASES["known"][0]
                    )

    def test_disclosure_forgery_or_omission_refused(self):
        for warning in ([], ["FHIR VALID"], [bridge.WARNING, "second warning"]):
            packet = self.sample()
            packet["warnings"] = warning
            with self.assertRaises(ValueError):
                bridge.check_core_report(bridge.canonical(packet), bridge.PINNED_CASES["known"][0])

    def test_patient_payload_or_unknown_resource_hash_refused(self):
        packet = self.sample()
        packet["patient"] = {"name": "not permitted"}
        with self.assertRaises(ValueError):
            bridge.check_core_report(bridge.canonical(packet), bridge.PINNED_CASES["known"][0])
        packet = self.sample()
        packet["input_hash"] = "0" * 64
        with self.assertRaises(ValueError):
            bridge.check_core_report(bridge.canonical(packet), bridge.PINNED_CASES["known"][0])

    def test_duplicate_and_noncanonical_json_refused(self):
        packet = self.sample()
        raw = bridge.canonical(packet)
        variants = [
            raw.rstrip(b"\n"),
            b"  " + raw,
            raw + b"{}",
            b'{"status":"valid","status":"not_validated"}\n',
            raw.replace(b'"errors":[]', b'"errors":[],"errors":[]'),
        ]
        for data in variants:
            with self.subTest(data=data[:20]):  # noqa: SIM117
                with self.assertRaises((ValueError, TypeError)):
                    bridge.check_core_report(data, packet["input_hash"])

    def test_oversized_report_refused(self):
        with self.assertRaisesRegex(ValueError, "size_refused"):
            bridge.check_core_report(b" " * (bridge.MAX_OUTPUT + 1), "x")

    def test_untrusted_program_hash_refused(self):
        with TemporaryDirectory() as temp:
            fake = Path(temp) / "fake"
            fake.write_text("fake executable", encoding="utf-8")
            with self.assertRaises(ValueError):
                bridge.verify_program(fake, "0" * 64, "fake")
            with self.assertRaisesRegex(ValueError, "invalid_fake_sha256"):
                bridge.verify_program(fake, "bad", "fake")

    def test_real_qa_refuses_non_mac_before_any_execution(self):
        with patch.object(bridge.sys, "platform", "win32"):  # noqa: SIM117
            with self.assertRaisesRegex(ValueError, "real_apple_silicon"):
                bridge.qualify(Path("/no"), Path("/no"), "0" * 64, Path("/no"), "0" * 64)

    @unittest.skipUnless(Path("/usr/bin/git").is_file(), "requires POSIX system git")
    def test_ignored_untracked_bytecode_never_qualifies_source(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "src/medscale"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("# synthetic", encoding="utf-8")
            examples = root / "examples/synthetic_fhir_developer_beta"
            examples.mkdir(parents=True)
            (examples / "demo.json").write_text("{}", encoding="utf-8")
            (root / ".gitignore").write_text("__pycache__/" + chr(10), encoding="utf-8")
            for cmd in (
                ["/usr/bin/git", "init", "-q", str(root)],
                ["/usr/bin/git", "-C", str(root), "add", "."],
                [
                    "/usr/bin/git",
                    "-C",
                    str(root),
                    "-c",
                    "user.name=synthetic",
                    "-c",
                    "user.email=synthetic@example.invalid",
                    "commit",
                    "-qm",
                    "fixture",
                ],
            ):
                subprocess.run(cmd, check=True, capture_output=True)
            head = subprocess.run(
                ["/usr/bin/git", "-C", str(root), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            with patch.object(bridge, "PINNED_CORE_SHA", head):
                self.assertEqual(bridge.source_commit(root), head)
                pycache = package / "__pycache__"
                pycache.mkdir()
                (pycache / "__init__.cpython-311.pyc").write_bytes(b"unreviewed")
                # Git status ignores this bytecode; explicit file inventory must not.
                status = subprocess.run(
                    ["/usr/bin/git", "-C", str(root), "status", "--porcelain"],
                    capture_output=True,
                    check=True,
                )
                self.assertFalse(status.stdout)
                with self.assertRaisesRegex(ValueError, "core_source_unreviewed"):
                    bridge.source_commit(root)

    @unittest.skipUnless(os.name == "posix", "POSIX directory mode only")
    def test_restrictive_profile_requires_private_directory(self):
        with TemporaryDirectory() as root:
            work = Path(root) / "private"
            work.mkdir(mode=0o700)
            work.chmod(0o700)
            profile = bridge.sandbox_profile(work)
            self.assertIn("(deny default)", profile)
            self.assertIn("(allow file-write*", profile)
            self.assertNotIn("(allow network", profile)
            work.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "permissions_refused"):
                bridge.sandbox_profile(work)


if __name__ == "__main__":
    unittest.main()
