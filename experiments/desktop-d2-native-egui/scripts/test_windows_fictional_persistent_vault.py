"""Offline source-only and Windows user-DPAPI safety tests (fictional only)."""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import fictional_session_frame as frame
import windows_fictional_persistent_vault as qa

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures/core/encrypted-persistent-readback-projection.json"
)
APPROVED_SHA = "3673eb77b2dbef25fd6cb33d9c345d2f37d38a86bcf1652ed9defae4da139243"


class FictionalPersistentVaultTests(unittest.TestCase):
    def test_exact_persistent_projection_is_redacted_source_pinned(self):
        raw = FIXTURE.read_bytes()
        self.assertEqual(len(raw), 1215)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), APPROVED_SHA)
        document = json.loads(raw)
        self.assertEqual(document["schema"], qa.PROJECTION_SCHEMA)
        self.assertEqual(document["status"], qa.PROJECTION_STATUS)
        self.assertEqual(document["resource_count"], 3)
        self.assertEqual(
            [x["resource_type"] for x in document["resources"]],
            ["Observation", "Patient", "Encounter"],
        )
        for name, expected in (
            ("persistent_test_vault_reopened", True),
            ("ephemeral_store_removed", False),
            ("payload_included", False),
            ("production_key_provider_used", False),
            ("clinical_use_authorized", False),
            ("full_fhir_r4_conformance_established", False),
            ("transport_sender_authenticated", False),
            ("release_authorized", False),
        ):
            self.assertIs(document[name], expected)
        for entry in document["resources"]:
            self.assertEqual(set(entry), {"resource_type", "id", "full_url", "links"})
        self.assertNotIn(b"patient_name", raw.lower())
        self.assertNotIn(b"birthdate", raw.lower())

    def test_dpapi_buffer_bounded_and_wrong_platform_refuses(self):
        for bytes_ in (b"", b"x" * 4097, b"not_a_real_password" * 600):
            with self.assertRaisesRegex(ValueError, "blob_size_refused"):
                qa._blob(bytes_)
        self.assertEqual(qa._blob(b"ok")[0].cbData, 2)
        with patch.object(qa.os, "name", "posix"):
            with self.assertRaisesRegex(ValueError, "windows_user_dpapi_required"):
                qa.protect_user_local(b"k" * 32)
            with self.assertRaisesRegex(ValueError, "windows_user_dpapi_required"):
                qa.unprotect_user_local(b"ciphertext")

    @unittest.skipUnless(os.name == "nt", "Windows user-only DPAPI integration")
    def test_real_current_windows_user_dpapi_roundtrip_and_ciphertext_tamper(self):
        secret = b"FICTIONAL-ONLY-ROOT-KEY-TEST-DATA" + b"x" * 32
        wrapped = qa.protect_user_local(secret)
        self.assertNotIn(secret, wrapped)
        self.assertNotEqual(wrapped, secret)
        self.assertEqual(qa.unprotect_user_local(wrapped), secret)
        invalid = bytearray(wrapped)
        invalid[-12] ^= 1
        with self.assertRaisesRegex(ValueError, "unprotect_refused"):
            qa.unprotect_user_local(bytes(invalid))

    @unittest.skipUnless(os.name == "nt", "Windows strict QA directory admission")
    def test_qa_root_is_explicit_exact_name_and_existing_store_never_overwritten(self):
        with TemporaryDirectory(prefix="medorigin-fake-vault-test-") as parent:
            root = Path(parent) / qa.QA_DIR_NAME
            self.assertEqual(qa._safe_qa_root(root, create=True), root)
            root.mkdir()
            with self.assertRaisesRegex(ValueError, "exists_do_not_overwrite"):
                qa._safe_qa_root(root, create=True)
            with self.assertRaisesRegex(ValueError, "missing_verified_component"):
                qa._safe_qa_root(root, create=False)
            wrong = Path(parent) / "patients"
            with self.assertRaisesRegex(ValueError, "root_name_or_path_refused"):
                qa._safe_qa_root(wrong, create=True)

    def test_per_launch_hmac_allows_only_exact_persistent_or_ephemeral_fixture(self):
        raw = FIXTURE.read_bytes()
        nonce, key = frame.fresh_ephemeral_session()
        wrapped = frame.frame_one_time_fictional_core(raw, nonce, key)
        self.assertEqual(wrapped[-len(raw) :], raw)
        self.assertLess(len(wrapped), frame.MAX_FRAME + 1)
        with self.assertRaisesRegex(ValueError, "unreviewed_data_or_secret"):
            frame.frame_one_time_fictional_core(raw + b" ", nonce, key)


if __name__ == "__main__":
    unittest.main()
