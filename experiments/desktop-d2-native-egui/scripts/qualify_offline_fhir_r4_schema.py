#!/usr/bin/env python3
"""Validate only fixed fictional examples against HL7 FHIR R4 JSON Schema.

This is REAL R4 structural JSON-Schema testing, but NOT clinical validation,
terminology/profile/invariant conformance, PHI permission, or release approval.
Never accepts a caller-provided FHIR record; no network operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

R4_ZIP_SHA256 = "75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6"
R4_SCHEMA_FILE = "fhir.schema.json"
R4_SCHEMA_SIZE = 3_386_892
SCHEMA_DRAFT = "http://json-schema.org/draft-06/schema#"
SCHEMA_ID = "http://hl7.org/fhir/json-schema/4.0"
EXPECTED_DEFINITIONS = 680
JSONSCHEMA_VERSION = "4.25.1"
MAX_ZIP_BYTES = 500_000
MAX_SCHEMA_BYTES = 4_000_000

# No input path, no PHI, no user content, no clinical conclusion.
POSITIVE_PATIENT = {"resourceType": "Patient", "id": "synthetic", "active": True}
NEGATIVES = {
    "patient_invalid_active_type": {
        "resourceType": "Patient", "id": "synthetic", "active": "true",
    },
    "unknown_fictional_resource": {
        "resourceType": "UnknownFictionalResource", "id": "fictional-negative-control",
    },
    "observation_missing_required_fields": {
        "resourceType": "Observation", "id": "synthetic",
    },
}
# The official R4 JSON Schema ACCEPTS this incomplete resource. That is a
# critical, observed coverage limit, not a valid FHIR conformance result.
SCHEMA_BLIND_SPOT = {
    "resourceType": "StructureDefinition", "id": "medorigin-synthetic-demo",
}
SUCCESS = "HL7_R4_OFFLINE_JSON_SCHEMA_STRUCTURAL_CONTROLS_PASS_NOT_CLINICAL_VALIDATION"


def hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_source_pinned_r4_schema(archive: Path) -> dict:
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("r4_schema_archive_missing_or_symlink")
    if archive.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError("r4_schema_archive_size_refused")
    if hash_bytes(archive.read_bytes()) != R4_ZIP_SHA256:
        raise ValueError("r4_schema_official_zip_hash_mismatch")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if len(members) != 1 or members[0].filename != R4_SCHEMA_FILE:
            raise ValueError("r4_schema_archive_members_refused")
        if members[0].file_size != R4_SCHEMA_SIZE:
            raise ValueError("r4_schema_decompressed_size_mismatch")
        with z.open(members[0]) as reader:
            raw = reader.read(MAX_SCHEMA_BYTES + 1)
    if len(raw) != R4_SCHEMA_SIZE:
        raise ValueError("r4_schema_changed_during_read")
    value = json.loads(raw)
    if (
        not isinstance(value, dict)
        or value.get("$schema") != SCHEMA_DRAFT
        or value.get("id") != SCHEMA_ID
        or len(value.get("definitions", {})) != EXPECTED_DEFINITIONS
    ):
        raise ValueError("r4_schema_version_or_definition_contract_refused")
    return value


def validate_fictional_structural_cases(schema: dict) -> dict:
    try:
        from jsonschema import Draft6Validator
        from importlib.metadata import version
    except ImportError as exc:
        raise ValueError("jsonschema_library_missing_no_validation_qualified") from exc
    if version("jsonschema") != JSONSCHEMA_VERSION:
        raise ValueError("jsonschema_validator_version_unqualified")
    Draft6Validator.check_schema(schema)
    validator = Draft6Validator(schema)
    if next(validator.iter_errors(POSITIVE_PATIENT), None) is not None:
        raise ValueError("synthetic_patient_structural_positive_was_rejected")
    for label, candidate in NEGATIVES.items():
        if next(validator.iter_errors(candidate), None) is None:
            raise ValueError("invalid_fictional_r4_structure_accepted:" + label)
    if next(validator.iter_errors(SCHEMA_BLIND_SPOT), None) is not None:
        raise ValueError("pinned_schema_blind_spot_expectation_changed")
    return {
        "schema_draft": "draft-06",
        "scope": "STRUCTURAL_JSON_SCHEMA_ONLY_NOT_CLINICAL_VALIDATION",
        "positive_structural_cases": 1,
        "negative_structural_cases_refused": len(NEGATIVES),
        "known_json_schema_blind_spots": ["incomplete_structure_definition_accepted"],
        "requires_full_r4_profile_and_terminology_validator": True,
        "fhir_r4_conformance_established": False,
        "input": "SOURCE_CONTROLLED_SYNTHETIC_ONLY",
        "terminology_validated": False,
        "profiles_validated": False,
        "cross_references_validated": False,
        "clinical_release_authorized": False,
    }


def qualify(archive: Path) -> dict:
    schema = load_source_pinned_r4_schema(archive)
    result = validate_fictional_structural_cases(schema)
    print(json.dumps(result, sort_keys=True))
    print(SUCCESS)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-r4-schema-zip", type=Path, required=True)
    args = parser.parse_args()
    try:
        qualify(args.official_r4_schema_zip)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print("FHIR_R4_SCHEMA_QA_NO_GO: " + str(exc), file=sys.stderr)
        sys.exit(2)
