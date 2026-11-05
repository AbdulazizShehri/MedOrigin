"""Source-only strict Core981 protected audit to native D2 QA (no credentials)."""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import launch_windows_protected_audit_readonly as bridge


def receipt() -> bytes:
    source = {
        "schema":"medorigin-core-windows-synthetic-protected-audit-preview/v1",
        "status":"FICTIONAL_WINDOWS_PROTECTED_AUDIT_PREVIEW_ONLY",
        "operation":"verify", "verified_audit_events":1,
        "audit_head_sha256":None, "anchor_matched":True,
        "protected_credential_destroyed":False,
        "encrypted_workspace_store_preserved":False,
        "patient_data_admitted":False,
        "fhir_r4_conformance_validated":False,
        "clinical_use_authorized":False,
        "production_key_provider_selected":False,
        "publication_authorized":False,
    }
    return (json.dumps(source,sort_keys=True,separators=(",",":"))+"\n").encode()


def encode(data: dict) -> bytes:
    return (json.dumps(data,sort_keys=True,separators=(",",":"))+"\n").encode()


class ProtectedAuditReadOnlyTests(unittest.TestCase):
    def test_only_canonical_readonly_core_verify_receipt(self):
        good = receipt()
        self.assertEqual(bridge._canonical(good), good)
        self.assertEqual(bridge._canonical(good[:-1]+b"\r\n"), good)
        for bad in (b"", b"{}", good+b" ", good+b"\n", good[:-1],
                    b"x"*1025, good+b"\r\n"):
            with self.subTest(length=len(bad)), self.assertRaises(ValueError):
                bridge._canonical(bad)
        duplicated = good.replace(
            b'"anchor_matched":true',
            b'"anchor_matched":true,"anchor_matched":true', 1
        )
        with self.assertRaises(ValueError):
            bridge._canonical(duplicated)

    def test_all_clinical_flag_forgeries_and_destructive_actions_denied(self):
        for field in bridge.FALSE_FIELDS:
            data = json.loads(receipt())
            data[field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                bridge._canonical(encode(data))
        for field, value in (
            ("operation", "forget"), ("operation", "create"),
            ("anchor_matched", False),
            ("audit_head_sha256", "0"*64),
            ("verified_audit_events", True),
            ("verified_audit_events", 0),
            ("patient_name", "PHI"),
            ("source_path", "PHI"),
        ):
            data = json.loads(receipt())
            data[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                bridge._canonical(encode(data))

    def test_per_launch_mac_golden_vector_and_domain_separation(self):
        raw, nonce, key = receipt(), bytes(range(16)), bytes(range(32))
        framed = bridge._frame(raw, nonce, key)
        self.assertTrue(framed.startswith(bridge.DOMAIN+nonce))
        index = len(bridge.DOMAIN)+16
        expected = hmac.new(key, bridge.DOMAIN+nonce+len(raw).to_bytes(4,"big")+raw,
                            hashlib.sha256).digest()
        self.assertEqual(framed[index:index+32], expected)
        self.assertEqual(framed[index+32:], raw)
        self.assertNotEqual(bridge.DOMAIN, b"MedOrigin-D2-FICTIONAL-CORE-BATCH-V1\x00")
        self.assertNotEqual(bridge.DOMAIN, b"MedOrigin-D2-FICTIONAL-SESSION-V1\x00")
        for invalid in ((raw,nonce[:-1],key),(raw,nonce,key[:-1]),(b"",nonce,key)):
            with self.assertRaises(ValueError):
                bridge._frame(*invalid)

    def test_pins_core_source_and_only_readonly_view(self):
        self.assertEqual(bridge.CORE981_SHA, "835dfca52858fb0dafa013b90185b47c758f11bb")
        self.assertIn("'windows-audit-preview','verify'", bridge.CHILD)
        self.assertIn("'--synthetic-only','--developer-preview'", bridge.CHILD)
        self.assertNotIn("'forget'", bridge.CHILD)
        self.assertNotIn("'create'", bridge.CHILD)
        text = Path(bridge.__file__).read_text("utf-8")
        self.assertIn("child.stdin.write(framed)", text)
        self.assertIn('"--qa-uia"', text)
        self.assertIn('"-SessionFramePath", str(frame)', text)
        self.assertIn("qa_auto_close and qa_uia", text)
        self.assertNotIn('parser.add_argument("--files"', text)
        self.assertNotIn('parser.add_argument("--patient"', text)
        uia = (Path(bridge.__file__).resolve().parent.parent /
               "tests/windows-protected-audit-readonly-uia.ps1").read_text("utf-8")
        self.assertIn("Protected audit: 1 independently anchored fictional event verified", uia)
        self.assertIn("Protected audit: Clear verification result", uia)
        self.assertIn("--synthetic-protected-audit-session-stdin", uia)

    def test_wrong_os_identity_or_root_denied_before_core(self):
        with patch.object(sys, "platform", "linux"), self.assertRaisesRegex(ValueError,"windows_only"):
            bridge.launch(Path("no"), Path("no"), "bad", "0"*64,
                          Path("no"), "0"*64, qa_auto_close=True)
        with patch.object(sys, "platform", "win32"):
            with self.assertRaisesRegex(ValueError,"identity_format_refused"):
                bridge.launch(Path("no"), Path("no"), "bad", "0"*64,
                              Path("no"), "0"*64, qa_auto_close=True)
            with self.assertRaisesRegex(ValueError, "mutually_exclusive"):
                bridge.launch(Path("no"), Path("no"), "bad", "0"*64,
                              Path("no"), "0"*64, qa_auto_close=True, qa_uia=True)
            with TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ValueError,"only_explicit_fictional_folder"):
                    bridge.launch(Path("no"), Path(tmp),
                                  "00000000-0000-4000-8000-000000000001",
                                  "0"*64, Path("no"), "0"*64, qa_auto_close=True)


if __name__ == "__main__":
    unittest.main()
