"""Optional, source-pinned *structural* HL7 FHIR R4 JSON-Schema check.

This is not a complete FHIR R4 conformance validator: terminology, profiles,
invariants, business rules, and references are outside JSON Schema. No report
from this module asserts full clinical or FHIR conformance.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from importlib.metadata import PackageNotFoundError, version
from itertools import islice
from pathlib import Path
from typing import Any

from medscale.fhirkit.errors import FhirMissingDependencyError, UnavailableValidatorError
from medscale.fhirkit.report import FORMAT_VERSION, ValidationReport
from medscale.reproducibility import content_hash

# Exact official HL7 FHIR R4 v4.0.1 archive; verified in synthetic D2 QA #906.
# Schema is never bundled or downloaded by this module.
OFFICIAL_R4_SCHEMA_ZIP_SHA256 = "75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6"
OFFICIAL_R4_SCHEMA_MEMBER = "fhir.schema.json"
OFFICIAL_R4_SCHEMA_BYTES = 3_386_892
OFFICIAL_R4_SCHEMA_DEFINITIONS = 680
OFFICIAL_R4_SCHEMA_ID = "http://hl7.org/fhir/json-schema/4.0"
OFFICIAL_R4_DRAFT = "http://json-schema.org/draft-06/schema#"
PINNED_JSONSCHEMA_VERSION = "4.25.1"
MAX_ARCHIVE_BYTES = 500_000
MAX_EXTRACT_BYTES = 4_000_000
MAX_REPORTED_ERRORS = 12
PARTIAL_COVERAGE_WARNING = (
    "Official FHIR R4 v4.0.1 JSON Schema structural check ONLY. "
    "A structural pass is NOT full FHIR R4 conformance: profiles, terminology, "
    "invariants, cross-references and clinical safety were not checked; "
    "the schema accepts some incomplete StructureDefinition examples."
)


def _load_official_r4_json_schema(archive: Path) -> dict[str, Any]:
    """Fail closed unless the user supplied the exact published R4 archive."""
    if archive.is_symlink() or not archive.is_file():
        raise UnavailableValidatorError("official_r4_schema_archive_missing_or_symlink")
    try:
        if archive.stat().st_size > MAX_ARCHIVE_BYTES:
            raise UnavailableValidatorError("official_r4_schema_archive_too_large")
        raw_archive = archive.read_bytes()
    except OSError as exc:
        raise UnavailableValidatorError("official_r4_schema_archive_unreadable") from exc
    if (
        len(raw_archive) > MAX_ARCHIVE_BYTES
        or hashlib.sha256(raw_archive).hexdigest() != OFFICIAL_R4_SCHEMA_ZIP_SHA256
    ):
        raise UnavailableValidatorError("official_r4_schema_archive_sha256_mismatch")

    try:
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(raw_archive)) as z:
            members = z.infolist()
            if len(members) != 1 or members[0].filename != OFFICIAL_R4_SCHEMA_MEMBER:
                raise UnavailableValidatorError("official_r4_schema_archive_member_mismatch")
            if members[0].file_size != OFFICIAL_R4_SCHEMA_BYTES:
                raise UnavailableValidatorError("official_r4_schema_uncompressed_size_mismatch")
            with z.open(members[0]) as fp:
                raw_schema = fp.read(MAX_EXTRACT_BYTES + 1)
        if len(raw_schema) != OFFICIAL_R4_SCHEMA_BYTES:
            raise UnavailableValidatorError("official_r4_schema_uncompressed_bytes_mismatch")
        schema = json.loads(raw_schema)
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnavailableValidatorError("official_r4_schema_archive_invalid") from exc

    if (
        not isinstance(schema, dict)
        or schema.get("$schema") != OFFICIAL_R4_DRAFT
        or schema.get("id") != OFFICIAL_R4_SCHEMA_ID
        or not isinstance(schema.get("definitions"), dict)
        or len(schema["definitions"]) != OFFICIAL_R4_SCHEMA_DEFINITIONS
    ):
        raise UnavailableValidatorError("official_r4_schema_metadata_mismatch")
    return schema


def validate_offline_r4_json_structure(
    payload: dict[str, Any],
    archive: Path,
    created_at: str | None = None,
) -> ValidationReport:
    """Run a real offline *structural* R4 check; never return status='valid'.

    Passing JSON Schema yields 'not_validated' because full conformance is
    unproven; a structural failure yields 'invalid'. No network or schema
    download occurs. The optional, exact-version jsonschema dependency must
    already be present in the local interpreter.
    """
    if not isinstance(payload, dict):
        raise UnavailableValidatorError("fhir_input_must_be_json_object")
    schema = _load_official_r4_json_schema(archive)
    try:
        from jsonschema import Draft6Validator
    except ImportError as exc:
        raise FhirMissingDependencyError("jsonschema_4_25_1_not_installed") from exc
    try:
        installed = version("jsonschema")
    except PackageNotFoundError as exc:
        raise FhirMissingDependencyError("jsonschema_version_cannot_be_verified") from exc
    if installed != PINNED_JSONSCHEMA_VERSION:
        raise FhirMissingDependencyError("jsonschema_version_not_qualified")

    Draft6Validator.check_schema(schema)
    validator = Draft6Validator(schema)
    failures = list(islice(validator.iter_errors(payload), MAX_REPORTED_ERRORS + 1))
    # Report only validator keywords, never untrusted input values or paths.
    errors = tuple(
        "r4_json_schema_structural_error:" + str(failure.validator)
        for failure in failures[:MAX_REPORTED_ERRORS]
    )
    if len(failures) > MAX_REPORTED_ERRORS:
        errors += ("r4_json_schema_additional_errors_not_reported",)
    return ValidationReport(
        input_hash=content_hash(payload),
        validator_name="hl7-fhir-r4-json-schema-structural-only",
        validator_version="R4-4.0.1/jsonschema-4.25.1",
        status="invalid" if errors else "not_validated",
        errors=errors,
        warnings=(PARTIAL_COVERAGE_WARNING,),
        created_at=created_at,
        format_version=FORMAT_VERSION,
    )
