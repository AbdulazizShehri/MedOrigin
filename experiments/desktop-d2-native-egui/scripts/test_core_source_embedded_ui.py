"""Source-bound, no-dependency tests for TWO fictional Python Core reports embedded in D2.

No networking, local user inputs, Python Core launches or PHI.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures/core"
CASES = (
    (
        "known-structure-definition.json",
        "165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08",
        "d1f1167a352bbce42e851336d33d0e292902463c1656860bd7cce3ec67598faf",
    ),
    (
        "unknown-fictional-negative.json",
        "7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c",
        "493bdfef2855ab2bb997d56ee7e4afca4b5ae0c4cc75eef39461b00517ef177c",
    ),
)
WARNING = (
    "FHIR R4 schema, terminology, and profile validation were not performed; "
    "this local report records deterministic provenance only."
)
EXPECTED_KEYS = {
    "created_at",
    "errors",
    "format_version",
    "input_hash",
    "report_id",
    "status",
    "validator_name",
    "validator_version",
    "warnings",
}


def no_duplicate_object(pairs):
    item = {}
    for key, value in pairs:
        if key in item:
            raise ValueError("duplicate_report_key")
        item[key] = value
    return item


def checked(raw: bytes, report_hash: str, input_hash: str):
    if not 1 <= len(raw) <= 2048:
        raise ValueError("report_over_bound")
    if hashlib.sha256(raw).hexdigest() != report_hash:
        raise ValueError("unexpected_embedded_core_report_sha")
    report = json.loads(raw, object_pairs_hook=no_duplicate_object)
    if not isinstance(report, dict):
        raise ValueError("report_not_object")
    canonical = (
        json.dumps(
            report, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode()
    if raw != canonical:
        raise ValueError("report_not_canonical")
    if set(report) != EXPECTED_KEYS:
        raise ValueError("report_fields_unreviewed")
    if (
        report["input_hash"] != input_hash
        or report["status"] != "not_validated"
        or report["created_at"] != "2026-10-24T00:00:00Z"
        or report["format_version"] != "fhirkit-validation-report/v1"
        or report["validator_name"] != "medscale-fhirkit-local"
        or report["validator_version"] != "0.1.0"
        or report["warnings"] != [WARNING]
        or report["errors"] != []
        or report["report_id"] != ""
    ):
        raise ValueError("clinical_claim_or_source_not_approved")
    return report


class EmbeddedCoreProvenanceSourceTests(unittest.TestCase):
    def test_exact_both_pinned_reports_are_validated_only_as_source_provenance(self):
        for name, report_hash, input_hash in CASES:
            with self.subTest(name=name):
                report = checked((FIXTURES / name).read_bytes(), report_hash, input_hash)
                self.assertEqual(report["status"], "not_validated")
                self.assertEqual(report["warnings"], [WARNING])

    def test_mutated_or_forged_clinical_claims_refused(self):
        for name, report_hash, input_hash in CASES:
            raw = (FIXTURES / name).read_bytes()
            mutations = (
                raw + b" ",
                raw[:-1],
                raw.replace(b"not_validated", b"valid"),
                raw.replace(input_hash.encode(), b"f" * 64),
                raw.replace(b'"errors":[]', b'"errors":[],"errors":[]'),
                raw.replace(b'"warnings":[', b'"patient":{"name":"not permitted"},"warnings":['),
            )
            for mutation in mutations:
                with (
                    self.subTest(name=name, mutation=mutation[:24]),
                    self.assertRaises(ValueError),
                ):
                    checked(mutation, report_hash, input_hash)

    def test_nativesource_ui_reverifies_receipts_without_external_core_execution(self):
        app = (ROOT / "src/app.rs").read_text()
        core = (ROOT / "src/core_provenance.rs").read_text()
        self.assertIn("inspect_selected_core_receipt", app)
        self.assertIn("Core provenance: two fictional reports (NOT validated)", app)
        self.assertIn("Inspect Core synthetic provenance (read-only)", app)
        self.assertIn("Source report SHA-256", app)
        self.assertIn("Not a live Python Core connection", app)
        self.assertIn("include_bytes!", core)
        self.assertIn("inspect_pinned_core_report", core)
        for _, digest, input_hash in CASES:
            self.assertIn(digest, core)
            self.assertIn(input_hash, core)

    def test_native_ax_script_covers_both_sources_with_real_press(self):
        script = (ROOT / "tests/macos-core-provenance-ax-qualification.swift").read_text()
        self.assertIn("AXUIElementPerformAction", script)
        self.assertIn("MACOS_CORE_PROVENANCE_AX_2_OF_2_PASS_SYNTHETIC_ONLY", script)
        self.assertIn("windows.count == 1", script)
        for _, digest, _ in CASES:
            self.assertIn(digest, script)

    def test_real_windows_uia_has_exact_two_case_reproduction_and_hash_gate(self):
        script = (ROOT / "tests/windows-native-core-provenance-uia.ps1").read_text()
        self.assertIn("Get-FileHash -LiteralPath $ExePath -Algorithm SHA256", script)
        self.assertIn("UIAutomationClient", script)
        self.assertIn("InvokePattern", script)
        self.assertIn("TogglePattern", script)
        self.assertIn("Core status: not_validated", script)
        self.assertIn("D2_WINDOWS_CORE_PROVENANCE_UIA_2_OF_2_PASS_NONPUBLISHING", script)
        self.assertIn("stale positive receipt survived selection change", script)
        for _, digest, _ in CASES:
            self.assertIn(digest, script)


if __name__ == "__main__":
    unittest.main()
