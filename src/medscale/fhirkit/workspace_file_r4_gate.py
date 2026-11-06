"""Optional source-pinned official HL7 R4 structural gate BEFORE encrypted import.

The exact official v4.0.1 JSON Schema ZIP and jsonschema==4.25.1 are
caller-provided local data/dependency. A structural pass NEVER establishes
FHIR conformance, clinical safety, terminology, profiles or invariants.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from medscale.fhirkit.bundle_batch_assessment import assess_synthetic_bundle_batch_offline
from medscale.fhirkit.r4_outcome import _WARNING
from medscale.fhirkit.r4_schema import OFFICIAL_R4_SCHEMA_ZIP_SHA256

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TOP_KEYS = frozenset(
    {
        "schema",
        "status",
        "document_count",
        "total_resource_count",
        "structural_not_validated_count",
        "structural_invalid_count",
        "documents",
        "official_r4_archive_sha256",
        "source_filenames_included",
        "resource_payload_included",
        "result_persisted",
        "network_access_performed",
        "cross_bundle_patient_join_performed",
        "fhir_r4_conformance_validated",
        "clinical_use_authorized",
        "publication_authorized",
    }
)
_DOC_KEYS = frozenset(
    {
        "document_ordinal",
        "source_content_sha256",
        "resource_count",
        "resource_counts",
        "local_references_checked",
        "relationship_status",
        "r4_structural_status",
        "r4_operation_outcome",
    }
)


class FictionalFileR4GateError(ValueError):
    """Fixed redacted refusal, never a source path or untrusted error text."""


def require_official_r4_structural_preflight(
    snapshots: list[dict[str, Any]],
    preflights: list[dict[str, object]],
    archive: Path,
) -> dict[str, object]:
    """Verify ALL original source hashes against exact official R4 structure.

    Only one fully verified positive structural result for EVERY independent
    source allows caller to start ephemeral encrypted import. A positive
    status is *not_validated* by design; never accept a fake 'valid' result.
    """
    if (
        type(snapshots) is not list
        or type(preflights) is not list
        or not 2 <= len(snapshots) <= 4
        or len(snapshots) != len(preflights)
        or not isinstance(archive, Path)
    ):
        raise FictionalFileR4GateError("fictional_r4_gate_arguments_refused")
    # The downstream assessor pins the ZIP SHA, schema size, schema metadata,
    # exact jsonschema version and each source. Refuse all exceptions as a
    # fixed message so no path/patient text can be forwarded.
    try:
        result = assess_synthetic_bundle_batch_offline(snapshots, archive, synthetic_only=True)
    except Exception as exc:
        raise FictionalFileR4GateError("fictional_r4_structural_gate_refused") from exc
    if (
        type(result) is not dict
        or set(result) != _TOP_KEYS
        or result.get("schema") != "medorigin-core-synthetic-fhir-batch-dual-assessment/v1"
        or result.get("status") != "SYNTHETIC_BATCH_PARTIAL_R4_PRECHECK_ONLY"
        or result.get("official_r4_archive_sha256") != OFFICIAL_R4_SCHEMA_ZIP_SHA256
        or type(result.get("document_count")) is not int
        or result["document_count"] != len(snapshots)
        or type(result.get("structural_invalid_count")) is not int
        or result["structural_invalid_count"] != 0
        or type(result.get("structural_not_validated_count")) is not int
        or result["structural_not_validated_count"] != len(snapshots)
        or type(result.get("documents")) is not list
        or len(result["documents"]) != len(snapshots)
        or type(result.get("total_resource_count")) is not int
        or result["total_resource_count"]
        != sum(p.get("resource_count", 0) if type(p) is dict else 0 for p in preflights)
        or any(
            result.get(key) is not False
            for key in (
                "source_filenames_included",
                "resource_payload_included",
                "result_persisted",
                "network_access_performed",
                "cross_bundle_patient_join_performed",
                "fhir_r4_conformance_validated",
                "clinical_use_authorized",
                "publication_authorized",
            )
        )
    ):
        raise FictionalFileR4GateError("fictional_r4_structural_contract_refused")

    checked: set[str] = set()
    for ordinal, (source, bound) in enumerate(zip(result["documents"], preflights, strict=True), 1):
        if type(source) is not dict or type(bound) is not dict or set(source) != _DOC_KEYS:
            raise FictionalFileR4GateError("fictional_r4_structural_source_refused")
        sha = bound.get("source_content_sha256")
        count = bound.get("resource_count")
        outcome = source.get("r4_operation_outcome")
        if (
            type(sha) is not str
            or _SHA.fullmatch(sha) is None
            or sha in checked
            or type(count) is not int
            or not 1 <= count <= 16
            or source.get("document_ordinal") != ordinal
            or source.get("source_content_sha256") != sha
            or source.get("resource_count") != count
            or source.get("relationship_status") != "local_relationship_preflight_only"
            or source.get("r4_structural_status") != "not_validated"
            or type(source.get("resource_counts")) is not dict
            or set(source["resource_counts"]) != {"Encounter", "Observation", "Patient"}
            or any(type(v) is not int or v < 0 for v in source["resource_counts"].values())
            or sum(source["resource_counts"].values()) != count
            or source["resource_counts"]["Patient"] != 1
            or type(source.get("local_references_checked")) is not int
            or not 0 <= source["local_references_checked"] <= count * 3
            or outcome
            != {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "warning",
                        "code": "informational",
                        "details": {"text": _WARNING},
                    }
                ],
            }
        ):
            raise FictionalFileR4GateError("fictional_r4_structural_source_refused")
        checked.add(sha)

    return {
        "schema": "medorigin-core-fictional-file-official-r4-structural-gate/v1",
        "status": "OFFICIAL_R4_JSON_SCHEMA_STRUCTURE_ONLY_NOT_VALIDATED",
        "official_r4_archive_sha256": OFFICIAL_R4_SCHEMA_ZIP_SHA256,
        "source_count": len(checked),
        "structural_not_validated_count": len(checked),
        "structural_invalid_count": 0,
        "fhir_r4_conformance_validated": False,
        "terminology_profiles_invariants_verified": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }
