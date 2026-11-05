"""No-network source tests for the one-command fictitious Core -> D2 opener."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import launch_windows_real_core963_fictional_batch as bridge

ROOT = Path(__file__).resolve().parent.parent
RECEIPT = ROOT / "fixtures/core/core963-real-encrypted-fictional-file-batch-redacted.json"


class Core963RealFictionalOneCommandTests(unittest.TestCase):
    def test_actual_source_generated_two_file_receipt_has_only_redacted_fields(self):
        raw = RECEIPT.read_bytes()
        self.assertEqual(len(raw), 1341)
        self.assertEqual(len(bridge._verified_receipt(raw)["imports"]), 2)
        self.assertNotIn(b"urn:uuid:", raw)
        self.assertNotIn(b"fictional-patient", raw)
        self.assertNotIn(b"imaginary-file-", raw)

    def test_bound_session_hmac_domain_nonce_and_fictional_receipt_bytes(self):
        import hashlib
        import hmac
        raw = RECEIPT.read_bytes()
        nonce = bytes(range(16))
        key = bytes(range(32))
        result = bridge._per_launch_core_frame(raw, nonce, key)
        tag = b"MedOrigin-D2-FICTIONAL-CORE-BATCH-V1\x00"
        self.assertEqual(result[:len(tag)], tag)
        self.assertEqual(result[len(tag):len(tag)+16], nonce)
        self.assertEqual(result[len(tag)+48:], raw)
        expected = hmac.new(
            key, tag + nonce + len(raw).to_bytes(4, "big") + raw, hashlib.sha256
        ).digest()
        self.assertEqual(result[len(tag)+16:len(tag)+48], expected)
        self.assertNotEqual(
            expected,
            hmac.new(key, b"MedOrigin-D2-FICTIONAL-SESSION-V1\x00"
                     + nonce + len(raw).to_bytes(4, "big") + raw, hashlib.sha256).digest(),
        )
        for invalid in ((raw, nonce[:-1], key), (raw, nonce, key[:-1]),
                        (b"", nonce, key), (b"x" * 4097, nonce, key)):
            with self.assertRaises(ValueError):
                bridge._per_launch_core_frame(*invalid)

    def test_one_final_windows_crlf_is_canonicalized_without_stripping_any_other_bytes(self):
        canonical = RECEIPT.read_bytes()
        self.assertTrue(canonical.endswith(b"\n"))
        windows = canonical[:-1] + b"\r\n"
        self.assertEqual(bridge._canonicalize_windows_stdout(windows), canonical)
        self.assertEqual(bridge._canonicalize_windows_stdout(canonical), canonical)
        self.assertEqual(bridge._canonicalize_windows_stdout(windows + b"\r\n"), windows + b"\r\n")
        self.assertEqual(bridge._canonicalize_windows_stdout(b"\r" + windows), b"\r" + windows)
        with self.assertRaises(ValueError):
            bridge._verified_receipt(bridge._canonicalize_windows_stdout(windows + b"\r\n"))

    def test_mutated_unsafe_flags_and_noncanonical_bytes_are_denied(self):
        raw = RECEIPT.read_bytes()
        for candidate in (b"", b"{}", raw + b" ", raw[:-1], b"x" * 4097):
            with self.assertRaises(ValueError):
                bridge._verified_receipt(candidate)
        for field in bridge.FALSE_FIELDS:
            source = json.loads(raw)
            source[field] = True
            forged = (json.dumps(source, sort_keys=True, separators=(",", ":")) + "\n").encode()
            with self.assertRaises(ValueError, msg=field):
                bridge._verified_receipt(forged)
        altered = json.loads(raw)
        altered["status"] = "CLINICALLY_APPROVED"
        with self.assertRaises(ValueError):
            bridge._verified_receipt((json.dumps(altered, sort_keys=True, separators=(",", ":")) + "\n").encode())

    def test_no_arbitrary_file_arguments_and_untrusted_sender_disclosure(self):
        source = Path(bridge.__file__).read_text(encoding="utf-8")
        self.assertIn("CORE963_SHA", source)
        self.assertIn("_fictional_bundle", bridge.CHILD)
        self.assertIn("_second_fictional_timeline_bundle", bridge.CHILD)
        self.assertIn("file-batch-encrypted-demo", bridge.CHILD)
        self.assertIn("--synthetic-only", bridge.CHILD)
        self.assertIn("--ephemeral-demo", bridge.CHILD)
        self.assertIn("D2_RECEIPT_FLAG", source)
        self.assertIn("D2_SESSION_BATCH_FLAG", source)
        self.assertIn("signed_frame = _per_launch_core_frame(canonical_receipt, nonce, secret)", source)
        self.assertIn("gui.stdin.write(signed_frame)", source)
        self.assertIn("env=child_env", source)
        self.assertIn('"-SessionFramePath", str(frame)', source)
        self.assertIn("cwd=exe.parent", source)
        self.assertNotIn('parser.add_argument("--files"', source)
        self.assertNotIn('parser.add_argument("--patient"', source)
        self.assertIn("not a signed installed-core runtime", source.lower())

    def test_live_source_uia_requires_exact_fixture_and_mutually_exclusive_qa_mode(self):
        harness = (ROOT / "tests/windows-real-core963-file-batch-receipt-uia.ps1").read_text(encoding="utf-8")
        launcher = Path(bridge.__file__).read_text(encoding="utf-8")
        self.assertIn("LiveReceiptPath", harness)
        self.assertIn("live_core_source_receipt_not_canonical", harness)
        self.assertIn("34beba4dd887ab5e26fb8ceaf91d06f85a6ebaca349359aa0f9ecccb612d2292", harness)
        self.assertIn("CORE963_LIVE_ENCRYPTED_TWO_FILE_SOURCE_TO_NATIVE_WINDOWS_UIA_PASS_NONCLINICAL", launcher)
        self.assertIn("live.write_bytes(canonical_receipt)", launcher)
        self.assertIn("qa_auto_close and qa_uia", launcher)
        with patch.object(sys, "platform", "win32"):
            with self.assertRaisesRegex(ValueError, "core963_qa_modes_mutually_exclusive"):
                bridge.launch(Path("no-core"), Path("wrong.exe"), "0" * 64, qa_auto_close=True, qa_uia=True)

    def test_wrong_os_refused_before_python_or_native_process(self):
        with patch.object(sys, "platform", "linux"):
            with self.assertRaisesRegex(ValueError, "windows_owner_host_required"):
                bridge.launch(Path("not-a-core"), Path("no-gui.exe"), "0" * 64, qa_auto_close=True)

    def test_source_root_without_exact_reviewed_tree_cannot_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "core963_source_files_refused"):
                bridge._core_source_attested(Path(temporary))


if __name__ == "__main__":
    unittest.main()
