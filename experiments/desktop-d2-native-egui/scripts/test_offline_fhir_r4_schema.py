"""No-network fail-closed source tests for official HL7 FHIR R4 Schema QA."""

from __future__ import annotations

import json
import sys
import types
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_offline_fhir_r4_schema as r4


class PinnedFHIRR4SchemaTests(unittest.TestCase):
    def schema_fixture(self) -> bytes:
        return json.dumps(
            {
                "$schema": r4.SCHEMA_DRAFT,
                "id": r4.SCHEMA_ID,
                "definitions": {"Patient": {"type": "object"}},
            },
            sort_keys=True,
        ).encode("utf-8")

    def fake_archive(self, folder: Path, *, extra_member: bool = False) -> Path:
        archive = folder / "fixture.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(r4.R4_SCHEMA_FILE, self.schema_fixture())
            if extra_member:
                z.writestr("extra.txt", b"unreviewed")
        return archive

    def test_source_pinned_zip_exact_members_and_schema_metadata_admission(self):
        with TemporaryDirectory() as tmp:
            path = self.fake_archive(Path(tmp))
            with (
                patch.object(r4, "R4_ZIP_SHA256", r4.hash_bytes(path.read_bytes())),
                patch.object(r4, "R4_SCHEMA_SIZE", len(self.schema_fixture())),
                patch.object(r4, "EXPECTED_DEFINITIONS", 1),
            ):
                parsed = r4.load_source_pinned_r4_schema(path)
                self.assertEqual(parsed["$schema"], r4.SCHEMA_DRAFT)

    def test_unreviewed_zip_bytes_and_members_are_refused(self):
        with TemporaryDirectory() as tmp:
            path = self.fake_archive(Path(tmp), extra_member=True)
            with (  # noqa: SIM117
                patch.object(r4, "R4_ZIP_SHA256", r4.hash_bytes(path.read_bytes())),
                patch.object(r4, "R4_SCHEMA_SIZE", len(self.schema_fixture())),
                patch.object(r4, "EXPECTED_DEFINITIONS", 1),
            ):
                with self.assertRaisesRegex(ValueError, "archive_members_refused"):
                    r4.load_source_pinned_r4_schema(path)
            with self.assertRaisesRegex(ValueError, "hash_mismatch"):
                r4.load_source_pinned_r4_schema(path)

    def test_truncated_and_missing_zip_are_refused(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "not-a-schema.zip"
            path.write_bytes(b"not an approved schema")
            with self.assertRaisesRegex(ValueError, "hash_mismatch"):
                r4.load_source_pinned_r4_schema(path)
            with self.assertRaisesRegex(ValueError, "missing"):
                r4.load_source_pinned_r4_schema(path.parent / "missing.zip")

    def test_symlinked_schema_input_is_refused(self):
        with TemporaryDirectory() as tmp:
            path = self.fake_archive(Path(tmp))
            alias = Path(tmp) / "alias.zip"
            try:
                alias.symlink_to(path)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ValueError, "symlink"):
                r4.load_source_pinned_r4_schema(alias)

    def test_all_structural_qa_results_remain_explicitly_nonclinical(self):
        class FakeDraft6Validator:
            @staticmethod
            def check_schema(schema):
                assert schema == {"synthetic": "schema"}

            def __init__(self, schema):
                self.schema = schema

            def iter_errors(self, data):
                if data in r4.NEGATIVES.values():
                    return iter([ValueError("fictional invalid control")])
                return iter([])

        fake_module = types.ModuleType("jsonschema")
        fake_module.Draft6Validator = FakeDraft6Validator
        with (
            patch.dict(sys.modules, {"jsonschema": fake_module}),
            patch("importlib.metadata.version", return_value=r4.JSONSCHEMA_VERSION),
        ):
            result = r4.validate_fictional_structural_cases({"synthetic": "schema"})
        self.assertEqual(result["positive_structural_cases"], 1)
        self.assertEqual(result["negative_structural_cases_refused"], 3)
        self.assertFalse(result["clinical_release_authorized"])
        self.assertFalse(result["fhir_r4_conformance_established"])
        self.assertTrue(result["requires_full_r4_profile_and_terminology_validator"])
        self.assertEqual(
            result["known_json_schema_blind_spots"],
            ["incomplete_structure_definition_accepted"],
        )

    def test_changed_schema_behavior_causes_refusal(self):
        class BrokenDraft:
            @staticmethod
            def check_schema(schema):
                pass

            def __init__(self, schema):
                pass

            def iter_errors(self, data):
                return iter([])

        fake_module = types.ModuleType("jsonschema")
        fake_module.Draft6Validator = BrokenDraft
        with (  # noqa: SIM117
            patch.dict(sys.modules, {"jsonschema": fake_module}),
            patch("importlib.metadata.version", return_value=r4.JSONSCHEMA_VERSION),
        ):
            with self.assertRaisesRegex(ValueError, "structure_accepted"):
                r4.validate_fictional_structural_cases({})

    def test_wrong_validator_package_version_fails_closed(self):
        module = types.ModuleType("jsonschema")
        module.Draft6Validator = object
        with (  # noqa: SIM117
            patch.dict(sys.modules, {"jsonschema": module}),
            patch("importlib.metadata.version", return_value="0.0.0"),
        ):
            with self.assertRaisesRegex(ValueError, "version_unqualified"):
                r4.validate_fictional_structural_cases({})


if __name__ == "__main__":
    unittest.main()
