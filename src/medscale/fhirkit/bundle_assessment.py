"""Synthetic-only local FHIR Bundle relationship + official R4 structure assessment.

This source-bound Core workflow combines TWO intentionally partial,
independently reviewed checks, *never* full clinical/FHIR R4 conformance.
No user payload, patient/resource identity or raw exception may leave the API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from medscale.fhirkit.bundle import inspect_synthetic_bundle
from medscale.fhirkit.r4_outcome import structural_outcome_for_report
from medscale.fhirkit.r4_schema import (
    OFFICIAL_R4_SCHEMA_ZIP_SHA256,
    validate_offline_r4_json_structure,
)


class SyntheticBundleAssessmentError(ValueError):
    """Fixed, source-safe refusal, not an untrusted path or JSON message."""


def assess_synthetic_bundle_offline(
    payload: dict[str, Any],
    official_r4_schema_archive: Path,
    *,
    synthetic_only: bool = False,
) -> dict[str, object]:
    """Return one bounded, redacted receipt for two real local FHIR checks.

    A successful relationship check only covers the narrow Patient,
    Encounter and Observation subset; an official R4 JSON Schema pass
    deliberately remains status 'not_validated'. No persistence, network,
    PHI detection, user authorization or conformance declaration exists.
    """
    if synthetic_only is not True:
        raise SyntheticBundleAssessmentError("synthetic_bundle_attestation_required")

    # This validates a strict synthetic marker and all admitted local
    # reference relationships *before* running the optional JSON Schema.
    # It must never admit arbitrary unreviewed or network-facing fields.
    preflight = inspect_synthetic_bundle(payload)
    report = validate_offline_r4_json_structure(payload, official_r4_schema_archive)
    outcome = structural_outcome_for_report(report)

    source_sha = preflight.get("source_content_sha256")
    if (
        not isinstance(source_sha, str)
        or len(source_sha) != 64
        or not all(char in "0123456789abcdef" for char in source_sha)
        or report.input_hash != source_sha
        or report.status not in ("invalid", "not_validated")
        or preflight.get("status") != "local_relationship_preflight_only"
        or preflight.get("payload_content_included") is not False
        or preflight.get("network_access_performed") is not False
        or preflight.get("full_fhir_r4_conformance_established") is not False
    ):
        raise SyntheticBundleAssessmentError("dual_source_assessment_contract_refused")
    return {
        "schema": "medorigin-synthetic-fhir-bundle-dual-assessment/v1",
        "status": "SYNTHETIC_R4_BUNDLE_PRECHECK_ONLY",
        "source_content_sha256": source_sha,
        "synthetic_marker_verified_as_assertion_only": True,
        "relationship_status": "local_relationship_preflight_only",
        "resource_count": preflight["resource_count"],
        "resource_counts": preflight["resource_counts"],
        "local_references_checked": preflight["local_references_checked"],
        "r4_structural_status": report.status,
        "r4_operation_outcome": outcome,
        "official_r4_archive_sha256": OFFICIAL_R4_SCHEMA_ZIP_SHA256,
        "payload_included": False,
        "output_persisted": False,
        "network_access_performed": False,
        "fhir_r4_conformance_validated": False,
        "terminology_profiles_invariants_verified": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }


def synthetic_bundle_assessment_json(
    payload: dict[str, Any],
    official_r4_schema_archive: Path,
    *,
    synthetic_only: bool = False,
) -> str:
    """Deterministic serialized receipt; never expose raw FHIR resource text."""
    return (
        json.dumps(
            assess_synthetic_bundle_offline(
                payload, official_r4_schema_archive, synthetic_only=synthetic_only
            ),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    )
