"""Strict nonclinical Core encrypted readback -> native D2 source checks."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "fixtures/core/encrypted-readback-projection.json"
EXPORTER = ROOT / "scripts/synthetic_encrypted_readback_projection.py"
GUI = ROOT / "src/main.rs"
ACCEPTOR = ROOT / "src/encrypted_readback.rs"
DIGEST = "c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49"


class SourcePinnedEncryptedReadbackTests(unittest.TestCase):
    def test_exact_nonclinical_decrypted_source_projection_is_bounded(self):
        raw = SOURCE.read_bytes()
        self.assertEqual(len(raw), 1164)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), DIGEST)
        projection = json.loads(raw)
        self.assertEqual(raw, json.dumps(projection, sort_keys=True, separators=(",", ":")).encode())
        self.assertEqual(projection["resource_count"], 3)
        self.assertEqual([r["resource_type"] for r in projection["resources"]],
                         ["Observation", "Patient", "Encounter"])
        self.assertEqual([len(r["links"]) for r in projection["resources"]], [2, 0, 1])
        for marker in ("clinical_use_authorized", "release_authorized",
                       "production_key_provider_used", "full_fhir_r4_conformance_established",
                       "payload_included", "transport_sender_authenticated"):
            self.assertIs(projection[marker], False)
        self.assertIs(projection["audit_chain_verified"], True)
        self.assertIs(projection["encrypted_reopen_verified"], True)
        self.assertIs(projection["ephemeral_store_removed"], True)
        self.assertNotIn("Fictional Example Only", raw.decode())
        for resource in projection["resources"]:
            self.assertEqual(set(resource), {"id", "resource_type", "full_url", "links"})
            self.assertTrue(resource["id"].startswith("fictional-"))

    def test_actual_decrypted_bundle_is_used_and_caller_fields_not_output(self):
        source = EXPORTER.read_text(encoding="utf-8")
        self.assertIn('entries = readback["bundle"]["entry"]', source)
        self.assertIn("read_synthetic_bundle_in_memory(", source)
        self.assertIn("allow_in_memory_readback=True", source)
        self.assertIn("expected_head_event_digest=source_receipt", source)
        self.assertIn('readback["bundle"] != fictional', source)
        self.assertIn("InMemoryTestKeyProvider(new_root_secret())", source)
        self.assertIn("TemporaryDirectory(", source)
        self.assertIn("Path(directory).exists()", source)
        self.assertIn('sys.argv[1:]', source)
        self.assertNotIn("json.dump(", source)
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("subprocess.", source)

    def test_unknown_patient_path_argument_is_refused_before_import_or_echo(self):
        attempt = subprocess.run(
            [sys.executable, "-I", "-B", str(EXPORTER), "--patient-file=/fake/secret"],
            capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(attempt.returncode, 2)
        self.assertEqual(attempt.stdout, b"")
        self.assertIn(b"arguments_refused", attempt.stderr)
        self.assertNotIn(b"/fake/secret", attempt.stderr)

    def test_native_rust_stdin_only_and_forgery_refusals_remain(self):
        main = GUI.read_text(encoding="utf-8")
        admitted = ACCEPTOR.read_text(encoding="utf-8")
        self.assertIn("--synthetic-encrypted-readback-stdin", main)
        self.assertIn("recv_timeout(deadline)", main)
        self.assertIn("admit_exact_encrypted_readback_projection", admitted)
        self.assertIn("raw != SOURCE", admitted)
        self.assertIn(DIGEST, admitted)
        self.assertIn("transport_sender_authenticated", admitted)
        self.assertIn("clinical_use_authorized", admitted)
        self.assertNotIn("std::process::Command", main)
        self.assertNotIn("std::net::", main)


if __name__ == "__main__":
    unittest.main()
