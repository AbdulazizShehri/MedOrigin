"""Source-only negative-first tests for pinned official R4 -> redacted native preview."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import launch_windows_real_core971_official_r4_fictional_batch as bridge

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "fixtures/core/core963-real-encrypted-fictional-file-batch-redacted.json"
GATE = {
    "schema": "medorigin-core-fictional-file-official-r4-structural-gate/v1",
    "status": "OFFICIAL_R4_JSON_SCHEMA_STRUCTURE_ONLY_NOT_VALIDATED",
    "official_r4_archive_sha256": bridge.HL7_R4_ZIP_SHA,
    "source_count": 2,
    "structural_not_validated_count": 2,
    "structural_invalid_count": 0,
    "fhir_r4_conformance_validated": False,
    "terminology_profiles_invariants_verified": False,
    "clinical_use_authorized": False,
    "publication_authorized": False,
}


def encode(v: dict) -> bytes:
    return (json.dumps(v, sort_keys=True, separators=(",", ":")) + "\n").encode()


def new_receipt() -> dict:
    old = json.loads(LEGACY.read_bytes())
    old["official_r4_structural_gate"] = copy.deepcopy(GATE)
    return old


class Core971OfficialR4NativeTests(unittest.TestCase):
    def test_canonical_redacted_core963_shape_preserved_but_new_r4_required(self):
        raw = encode(new_receipt())
        obj = bridge._verified_official_receipt(raw)
        self.assertEqual(obj["official_r4_structural_gate"], GATE)
        self.assertEqual(obj["import_count"], 2)
        self.assertLess(len(raw), bridge.legacy.MAX_RECEIPT)
        with self.assertRaises(ValueError):
            bridge._verified_official_receipt(LEGACY.read_bytes())

    def test_missing_forged_structural_gate_or_positive_clinical_claim_is_refused(self):
        source = new_receipt()
        for field in GATE:
            obj = copy.deepcopy(source)
            del obj["official_r4_structural_gate"][field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                bridge._verified_official_receipt(encode(obj))
        for field in (
            "fhir_r4_conformance_validated",
            "terminology_profiles_invariants_verified",
            "clinical_use_authorized",
            "publication_authorized",
        ):
            obj = copy.deepcopy(source)
            obj["official_r4_structural_gate"][field] = True
            with self.subTest(forger=field), self.assertRaises(ValueError):
                bridge._verified_official_receipt(encode(obj))
        for field, value in [
            ("schema", "made-up"),
            ("status", "VALIDATED"),
            ("source_count", 1),
            ("structural_invalid_count", 1),
            ("structural_not_validated_count", 0),
            ("official_r4_archive_sha256", "0" * 64),
            ("source_count", True),
            ("clinical_use_authorized", None),
        ]:
            obj = copy.deepcopy(source)
            obj["official_r4_structural_gate"][field] = value
            with self.subTest(forged=field), self.assertRaises(ValueError):
                bridge._verified_official_receipt(encode(obj))

    def test_patient_identity_arbitrary_extra_fields_or_noncanonical_bytes_fail(self):
        raw = encode(new_receipt())
        for candidate in [b"", raw[:-1], raw + b"\n", b" " + raw, b"x" * 4097]:
            with self.subTest(size=len(candidate)), self.assertRaises(ValueError):
                bridge._verified_official_receipt(candidate)
        altered = new_receipt()
        altered["official_r4_structural_gate"]["patient_id"] = "NO"
        with self.assertRaises(ValueError):
            bridge._verified_official_receipt(encode(altered))
        altered = new_receipt()
        altered["file_path"] = "NO"
        with self.assertRaises(ValueError):
            bridge._verified_official_receipt(encode(altered))
        altered = new_receipt()
        altered["official_r4_structural_gate"]["path"] = "NO"
        with self.assertRaises(ValueError):
            bridge._verified_official_receipt(encode(altered))
        altered = new_receipt()
        altered["status"] = "CLINICALLY_APPROVED"
        with self.assertRaises(ValueError):
            bridge._verified_official_receipt(encode(altered))
        duplicate = raw.replace(b'"source_count":2', b'"source_count":2,"source_count":2', 1)
        with self.assertRaises(ValueError):
            bridge._verified_official_receipt(duplicate)

    def test_cannot_fake_official_zip_or_unpinned_file(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "fhir.schema.json.zip"
            fake.write_bytes(b"X" * 287789)
            with self.assertRaisesRegex(
                ValueError, "core971_official_r4_zip_sha_or_bounds_refused"
            ):
                bridge._attest_offline_r4_schema(fake)
            missing = Path(directory) / "missing.zip"
            with self.assertRaisesRegex(ValueError, "core971_reviewed_input_missing"):
                bridge._attest_offline_r4_schema(missing)

    def test_no_arbitrary_patient_file_selection_and_core971_exact_sha(self):
        code = Path(bridge.__file__).read_text("utf8")
        self.assertEqual(bridge.CORE971_SHA, "9c27397f956303f92aeaf4bc173257c093a53238")
        self.assertIn("--offline-r4-schema", bridge.CHILD)
        self.assertIn("--synthetic-only", bridge.CHILD)
        self.assertIn("--ephemeral-demo", bridge.CHILD)
        self.assertIn("file-batch-encrypted-demo", bridge.CHILD)
        self.assertIn("_fictional_bundle", bridge.CHILD)
        self.assertIn("_second_fictional_timeline_bundle", bridge.CHILD)
        self.assertNotIn('parser.add_argument("--files"', code)
        self.assertNotIn('parser.add_argument("--patient"', code)
        self.assertIn("cwd=exe.parent", code)
        self.assertIn("qa_auto_close and qa_uia", code)
        uia = ROOT / "tests/windows-real-core971-official-r4-uia.ps1"
        self.assertIn("Official R4: 2 of 2", uia.read_text("utf8"))
        self.assertIn("ExpectedReceiptSha256", uia.read_text("utf8"))

    def test_invalid_os_and_mutually_exclusive_mode_rejected_before_any_import(self):
        with (
            patch.object(sys, "platform", "linux"),
            self.assertRaisesRegex(ValueError, "core971_windows_host_required"),
        ):
            bridge.launch(Path("NO"), Path("NO"), "0" * 64, Path("NO"), qa_uia=True)
        with (
            patch.object(sys, "platform", "win32"),
            self.assertRaisesRegex(ValueError, "core971_qa_modes_mutually_exclusive"),
        ):
            bridge.launch(
                Path("NO"), Path("NO"), "0" * 64, Path("NO"), qa_auto_close=True, qa_uia=True
            )

    def test_changed_core_tree_or_missing_official_gate_is_denied(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "core971_reviewed_input_missing"),
        ):
            bridge._attest_core(Path(directory))
        self.assertIn(
            "CORE971_OFFICIAL_R4_TO_NATIVE_NO_GO", Path(bridge.__file__).read_text("utf8")
        )


if __name__ == "__main__":
    unittest.main()
