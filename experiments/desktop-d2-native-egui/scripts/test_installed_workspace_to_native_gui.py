"""Offline source/adversarial controls for Core encrypted Workspace -> D2 GUI."""

import importlib
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
demo = importlib.import_module("qualify_installed_workspace_to_native_gui")


class EncryptedWorkspaceToNativeD2(unittest.TestCase):
    def test_non_mac_real_sandbox_must_fail_closed_before_launch(self):
        with (
            patch.object(demo.sys, "platform", "win32"),
            self.assertRaisesRegex(ValueError, "apple_silicon"),
        ):
            demo.qualify(None)

    def test_both_installed_wheels_source_and_metadata_are_pinned(self):
        source = Path(demo.__file__).read_text(encoding="utf-8")
        self.assertEqual(demo.EXPECTED_CORE_COMMIT, "0351b667ec910480fd61c30f18cf3bb0dd0ae842")
        self.assertEqual(
            demo.EXPECTED_RECEIPT_SHA,
            "25acdb57db8ca3f11d353cf311167973760caaa95bb64de7339fe21e3b05cc2e",
        )
        self.assertIn("installed.read_bytes() != source.read_bytes()", source)
        self.assertIn("set(expected_files) != packaged", source)
        self.assertIn("mac_sandboxed_ephemeral_encrypted_core_demo_refused", source)
        self.assertIn("prove_restrictive_mac_policy", source)
        self.assertIn("sandbox_profile(work)", source)
        self.assertIn('"--synthetic-workspace-receipt-stdin"', source)

    def test_rust_native_exact_canonical_encrypted_summary_has_no_patient_path(self):
        native = (ROOT / "src/main.rs").read_text()
        receipt = (ROOT / "src/workspace_receipt.rs").read_text()
        app = (ROOT / "src/app.rs").read_text()
        self.assertIn('"--synthetic-workspace-receipt-stdin"', native)
        self.assertIn("recv_timeout(deadline)", native)
        self.assertIn("from_one_time_synthetic_workspace_stdin", native)
        self.assertIn("if args.is_empty()", native)
        self.assertIn("raw != SOURCE_RECEIPT", receipt)
        self.assertIn("clinical", receipt)
        self.assertIn(
            "publication_authorized",
            (ROOT / "fixtures/core/workspace-ephemeral-demo.json").read_text(),
        )
        self.assertIn("encrypted_workspace_receipt = None", app)
        self.assertIn("Encrypted Workspace proof", app)
        self.assertIn("source and freshness NOT authenticated by GUI", app)
        self.assertNotIn("std::process::Command", native)
        self.assertNotIn("std::net::", native)

    def test_windows_real_uia_is_source_sha_bounded_and_rejects_forgery(self):
        path = ROOT / "tests/windows-encrypted-workspace-native-uia.ps1"
        text = path.read_text(encoding="utf-8")
        self.assertIn("ExpectedSha256", text)
        self.assertIn("Workspace demo SHA-256", text)
        self.assertIn("Fictional resources: 3", text)
        self.assertIn("Verified encrypted reopen: true", text)
        self.assertIn("D2_WINDOWS_ENCRYPTED_WORKSPACE_NATIVE_UIA_PASS_NONCLINICAL", text)
        self.assertIn("clinical_use_authorized", text)
        self.assertIn("Get-FileHash", text)

    def test_malformed_abi_package_bytes_and_nonclinical_gate_are_static(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "fake.whl"
            path.write_bytes(b"unreviewed arbitrary wheel")
            with patch.object(demo.subprocess, "run") as process:
                process.return_value.stdout = demo.EXPECTED_CORE_COMMIT + "\n"
                with self.assertRaisesRegex(ValueError, "unreviewed_bytes"):
                    demo.attest_installed(Path(tmp), Path(tmp), Path(tmp))
                process.assert_called()


if __name__ == "__main__":
    unittest.main()
