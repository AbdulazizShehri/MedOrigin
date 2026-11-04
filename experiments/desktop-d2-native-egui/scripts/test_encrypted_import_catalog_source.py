"""Source-only negative tests for real encrypted fictional import history D2.

No real patient records, no Core installation or GUI required in hosted CI.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures/core/encrypted-import-catalog-demo.json"
DIGEST = "cfa5c71cd07763b6a1b32f7e6de8c51c565c4b6caf09224c51fcba095263b623"


class SyntheticCatalogSourceQualification(unittest.TestCase):
    def test_exact_actual_encrypted_two_import_catalog_is_bounded_and_source_canonical(self):
        raw = FIXTURE.read_bytes()
        self.assertEqual(len(raw), 799)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), DIGEST)
        data = json.loads(raw)
        self.assertEqual(raw, json.dumps(data, sort_keys=True, separators=(",", ":")).encode())
        self.assertEqual(data["schema"], "medorigin-ephemeral-fhir-import-catalog-demo/v1")
        self.assertEqual(data["status"], "SYNTHETIC_ENCRYPTED_CATALOG_DEMO_PASS")
        self.assertEqual(data["import_count"], 2)
        self.assertEqual(data["resource_count"], 4)
        self.assertEqual(data["verified_audit_events"], 3)
        self.assertEqual([(e["audit_sequence"], e["resource_count"]) for e in data["imports"]], [(1, 3), (3, 1)])
        for field in ("clinical_use_authorized", "full_fhir_r4_conformance_established",
                      "publication_authorized", "payload_included"):
            self.assertIs(data[field], False)
        self.assertIs(data["ephemeral_store_removed"], True)

    def test_no_raw_fhir_or_patient_fields_or_unbounded_records(self):
        data = json.loads(FIXTURE.read_bytes())
        self.assertEqual(set(data), {"schema", "status", "import_count", "resource_count",
                        "verified_audit_events", "imports", "ephemeral_store_removed",
                        "clinical_use_authorized", "full_fhir_r4_conformance_established",
                        "publication_authorized", "payload_included"})
        for entry in data["imports"]:
            self.assertEqual(set(entry), {"source_content_sha256", "import_audit_event_digest",
                                            "audit_sequence", "resource_count"})
            self.assertEqual(len(entry["source_content_sha256"]), 64)
            self.assertEqual(len(entry["import_audit_event_digest"]), 64)
        for sensitive in ("patient.name", "Fictional Catalog Example", "birthDate", "identifier",
                          "address", "resourceType", '"entry"', "original_bundle", "secret",
                          "private_key", "clinical_validated"):
            self.assertNotIn(sensitive, FIXTURE.read_text(encoding="utf-8"))

    def test_rust_fails_closed_for_modified_source_and_untrusted_stdin(self):
        src = (ROOT / "src/encrypted_import_catalog.rs").read_text()
        main = (ROOT / "src/main.rs").read_text()
        self.assertIn("raw != FIXED_CATALOG", src)
        self.assertIn(DIGEST, src)
        self.assertIn("MAX_CATALOG_BYTES: usize = 1024", src)
        self.assertIn("fictional_import_catalog_false_clinical_proof", src)
        self.assertIn("--synthetic-encrypted-import-history-stdin", main)
        self.assertIn("recv_timeout(deadline)", main)
        self.assertIn("MAX_FICTIONAL_CORE_STDIN: usize = 2048", main)
        self.assertNotIn("std::process::Command", main)
        self.assertNotIn("std::net::", main)

    def test_mac_actual_core_under_os_confinement_and_gui_process_cleanup(self):
        src = (ROOT / "scripts/qualify_mac_encrypted_import_catalog_gui.py").read_text()
        self.assertIn("35290b7c0f6f47995b52a10bb0ade9f7b27a67a8", src)
        self.assertIn("require_pinned_core(core)", src)
        self.assertIn("prove_restrictive_mac_policy(policy, work, python)", src)
        self.assertIn("run_sandboxed(policy, [", src)
        self.assertIn("result.stdout != receipt.read_bytes()", src)
        self.assertIn("native.terminate()", src)
        self.assertIn("native.kill()", src)
        self.assertIn("Temp", src)
        self.assertNotIn("shell=True", src)
        self.assertNotIn("requests.", src)

    def test_windows_real_core_catalog_job_lifetime_and_source_gate(self):
        runner = (ROOT / "scripts/qualify_windows_encrypted_import_catalog_native_gui.py").read_text()
        job = (ROOT / "scripts/supervise_windows_encrypted_catalog_job.py").read_text()
        self.assertIn("PINNED_CORE_SHA = \"35290b7c0f6f47995b52a10bb0ade9f7b27a67a8\"", runner)
        self.assertIn("approved_core_source(core)", runner)
        self.assertIn("real_catalog_under_windows_job(", runner)
        self.assertIn("raw != fixture.read_bytes()", runner)
        self.assertIn("genuine_windows_historical_import_GUI_UIA_refused", runner)
        self.assertIn("CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT", job)
        self.assertIn("api.AssignProcessToJobObject(job, proc.hProcess)", job)
        self.assertIn("api.IsProcessInJob(proc.hProcess, job", job)
        self.assertIn("api.ResumeThread(proc.hThread)", job)
        self.assertLess(
            job.index("api.AssignProcessToJobObject(job, proc.hProcess)"),
            job.index("api.ResumeThread(proc.hThread)"),
        )
        self.assertIn("JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", job)
        self.assertIn("api.TerminateJobObject(job, 1)", job)
        self.assertIn("WaitForSingleObject(proc.hProcess, 45000)", job)
        self.assertIn("m.version('cryptography')", job)
        self.assertNotIn("shell=True", runner + job)
        self.assertNotIn("requests.", runner + job)

    def test_windows_real_uia_contract_is_exact_nonclinical_projection(self):
        source = (ROOT / "tests/windows-encrypted-import-catalog-uia.ps1").read_text()
        self.assertIn("WINDOWS_REAL_ENCRYPTED_CORE_TWO_HISTORICAL_IMPORTS_NATIVE_UIA_PASS_NOT_CLINICAL", source)
        self.assertIn(DIGEST, source)
        self.assertIn("Length -ne 799", source)
        self.assertIn("--synthetic-encrypted-import-history-stdin", source)
        self.assertIn("Back to encrypted fictional import list", source)
        self.assertIn("Clear encrypted import history", source)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)


if __name__ == "__main__":
    unittest.main()
