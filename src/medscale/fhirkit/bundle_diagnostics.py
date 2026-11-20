"""Finite, redacted FHIR R4 OperationOutcome for rejected synthetic Bundles.

Only a source-scoped, exact synthetic marker plus an existing bounded
BundlePreflightError from Core's narrow local-reference checker can produce
a document. The official R4 schema is *not* checked on this failure route;
never imply full FHIR or clinical conformance.
"""

from __future__ import annotations

import json
from typing import Any

from medscale.fhirkit.bundle import (
    BundlePreflightError,
    _synthetic_marker,
)

# Fixed descriptions only. No input path, patient identifier, raw exception,
# resource value or external reference is ever inserted into a diagnostic.
_FIXED_LOCAL_FAILURES: dict[str, str] = {
    "only_collection_bundle_supported": (
        "This synthetic Bundle must use the collection Bundle resource type."
    ),
    "unreviewed_bundle_field_refused": (
        "The synthetic Bundle contains a field outside the admitted subset."
    ),
    "bundle_entry_count_out_of_range": (
        "The synthetic Bundle has no entries or exceeds the local entry limit."
    ),
    "bundle_entry_structure_refused": (
        "A synthetic Bundle entry has an unsupported local structure."
    ),
    "bundle_entry_resource_not_object": (
        "A synthetic Bundle entry does not contain a resource object."
    ),
    "nonlocal_or_invalid_fullurl": (
        "A synthetic Bundle entry fullUrl is not a canonical local UUID."
    ),
    "duplicate_bundle_fullurl": ("Two synthetic Bundle entries share the same local UUID."),
    "unsupported_bundle_resource_type": (
        "An entry is not in the admitted Patient, Encounter or Observation subset."
    ),
    "unreviewed_bundle_resource_field_refused": (
        "An admitted resource contains an unreviewed field."
    ),
    "invalid_bundle_resource_id": ("An admitted resource has an invalid local FHIR id shape."),
    "invalid_bundle_resource_meta": ("An admitted resource has a malformed metadata object."),
    "incomplete_encounter_subset": (
        "A synthetic Encounter lacks an admitted status or class shape."
    ),
    "incomplete_observation_subset": (
        "A synthetic Observation lacks an admitted status or code shape."
    ),
    "encounter_status_not_in_r4_required_codes": (
        "A synthetic Encounter status is not a required-binding HL7 FHIR R4 v4.0.1 code."
    ),
    "observation_status_not_in_r4_required_codes": (
        "A synthetic Observation status is not a required-binding HL7 FHIR R4 v4.0.1 code."
    ),
    "observation_multiple_r4_choice_values_refused": (
        "A synthetic Observation has more than one admitted FHIR R4 value[x] choice."
    ),
    "required_local_reference_missing_or_malformed": (
        "A required synthetic local subject or encounter reference is malformed."
    ),
    "external_or_invalid_reference_refused": (
        "A required synthetic reference is not a canonical local UUID."
    ),
    "unresolved_local_patient_reference": (
        "A synthetic local Patient reference does not resolve in this Bundle."
    ),
    "unresolved_local_encounter_reference": (
        "A synthetic local Encounter reference does not resolve in this Bundle."
    ),
    "local_reference_target_type_mismatch": (
        "A synthetic local reference resolves to the wrong admitted resource type."
    ),
    "observation_encounter_patient_mismatch": (
        "A synthetic Observation and its linked Encounter refer to different local Patients."
    ),
    "duplicate_bundle_resource_identity": (
        "Two entries have the same FHIR resource type and local resource id."
    ),
}
_FIXED_WARNING = (
    "Only a narrow synthetic Bundle local-reference check was attempted. "
    "Official FHIR R4 structural, profile, terminology, invariant and clinical "
    "conformance checks were NOT run or established."
)


class NegativeBundleOutcomeError(ValueError):
    """A fixed-phrase refusal that never mirrors patient input."""


def rejected_synthetic_bundle_operation_outcome(
    payload: dict[str, Any],
    refusal: BundlePreflightError,
) -> dict[str, object]:
    """Turn *only* known synthetic-marker-backed relationship failures into FHIR.

    The outcome is a rejection, not a successful dual-assessment receipt.
    Callers must still exit nonzero; neither the presence of this Outcome
    nor the original synthetic marker proves the absence of patient data.
    """
    if not isinstance(payload, dict) or not _synthetic_marker(payload):
        raise NegativeBundleOutcomeError("explicit_synthetic_fixture_marker_required")
    if type(refusal) is not BundlePreflightError:
        raise NegativeBundleOutcomeError("unqualified_bundle_failure_refused")
    reason = str(refusal)
    if reason not in _FIXED_LOCAL_FAILURES:
        raise NegativeBundleOutcomeError("unqualified_bundle_failure_refused")

    return {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": "error",
                "code": "structure",
                "details": {"text": _FIXED_LOCAL_FAILURES[reason]},
            },
            {
                "severity": "warning",
                "code": "informational",
                "details": {"text": _FIXED_WARNING},
            },
        ],
    }


def rejected_synthetic_bundle_outcome_json(
    payload: dict[str, Any],
    refusal: BundlePreflightError,
) -> str:
    return (
        json.dumps(
            rejected_synthetic_bundle_operation_outcome(payload, refusal),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    )
