"""Local synthetic FHIR Bundle relationship preflight (not HL7 conformance).

A narrow, source-owned, read-only multi-resource workflow for MedOrigin Core.
No EHR, network, storage, patient-text output, or clinical validation.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any
from uuid import UUID

from medscale.reproducibility import content_hash

_BUNDLE_TAG_SYSTEM = "urn:medorigin:fixture-classification"
_BUNDLE_TAG_CODE = "synthetic"
_FHIR_ID = re.compile(r"[A-Za-z0-9.-]{1,64}\Z")
# Exact required status codes for the specifically supported HL7 FHIR R4 v4.0.1
# narrow synthetic subset. These are NOT R4B/R5 codes. Local code admission
# alone never proves full FHIR terminology/profile/invariant conformance.
# https://hl7.org/fhir/R4/codesystem-encounter-status.html
# https://hl7.org/fhir/R4/valueset-observation-status.html
_ENCOUNTER_STATUS_R4 = frozenset(
    {
        "planned",
        "arrived",
        "triaged",
        "in-progress",
        "onleave",
        "finished",
        "cancelled",
        "entered-in-error",
        "unknown",
    }
)
_OBSERVATION_STATUS_R4 = frozenset(
    {
        "registered",
        "preliminary",
        "final",
        "amended",
        "corrected",
        "cancelled",
        "entered-in-error",
        "unknown",
    }
)
_ALLOWED_RESOURCE_KEYS = {
    "Patient": {
        "resourceType",
        "id",
        "meta",
        "active",
        "name",
        "gender",
        "birthDate",
        "identifier",
    },
    "Encounter": {
        "resourceType",
        "id",
        "meta",
        "status",
        "class",
        "subject",
        "period",
        "reasonCode",
    },
    "Observation": {
        "resourceType",
        "id",
        "meta",
        "status",
        "code",
        "subject",
        "encounter",
        "effectiveDateTime",
        "valueString",
        "valueQuantity",
    },
}
_MAX_ENTRIES = 128
_REPORT_SCHEMA = "medorigin-synthetic-fhir-bundle-preflight/v1"


class BundlePreflightError(ValueError):
    """Refusal with a fixed code that does not echo input values."""


def _ref(resource: dict[str, Any], name: str) -> str:
    """Admit only an explicit local UUID reference, not a network URL."""
    value = resource.get(name)
    if not isinstance(value, dict) or set(value) != {"reference"}:
        raise BundlePreflightError("required_local_reference_missing_or_malformed")
    reference = value["reference"]
    if not isinstance(reference, str) or not reference.startswith("urn:uuid:"):
        raise BundlePreflightError("external_or_invalid_reference_refused")
    try:
        suffix = reference[len("urn:uuid:") :]
        if str(UUID(suffix)) != suffix:
            raise ValueError("noncanonical UUID")
    except (ValueError, AttributeError) as exc:
        raise BundlePreflightError("external_or_invalid_reference_refused") from exc
    return reference


def _synthetic_marker(payload: dict[str, Any]) -> bool:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return False
    tags = meta.get("tag")
    return (
        isinstance(tags, list)
        and len(tags) == 1
        and isinstance(tags[0], dict)
        and tags[0] == {"system": _BUNDLE_TAG_SYSTEM, "code": _BUNDLE_TAG_CODE}
    )


def _resource_identity(resource: Any) -> tuple[str, str]:
    if not isinstance(resource, dict):
        raise BundlePreflightError("bundle_entry_resource_not_object")
    kind = resource.get("resourceType")
    if not isinstance(kind, str) or kind not in _ALLOWED_RESOURCE_KEYS:
        raise BundlePreflightError("unsupported_bundle_resource_type")
    if not set(resource).issubset(_ALLOWED_RESOURCE_KEYS[kind]):
        raise BundlePreflightError("unreviewed_bundle_resource_field_refused")
    fhir_id = resource.get("id")
    if not isinstance(fhir_id, str) or not _FHIR_ID.fullmatch(fhir_id):
        raise BundlePreflightError("invalid_bundle_resource_id")
    if "meta" in resource and not isinstance(resource["meta"], dict):
        raise BundlePreflightError("invalid_bundle_resource_meta")
    if kind == "Encounter":
        if not isinstance(resource.get("status"), str) or not isinstance(
            resource.get("class"), dict
        ):
            raise BundlePreflightError("incomplete_encounter_subset")
        if resource["status"] not in _ENCOUNTER_STATUS_R4:
            raise BundlePreflightError("encounter_status_not_in_r4_required_codes")
    elif kind == "Observation":
        if not isinstance(resource.get("status"), str) or not isinstance(
            resource.get("code"), dict
        ):
            raise BundlePreflightError("incomplete_observation_subset")
        if resource["status"] not in _OBSERVATION_STATUS_R4:
            raise BundlePreflightError("observation_status_not_in_r4_required_codes")
    return kind, fhir_id


def inspect_synthetic_bundle(payload: dict[str, Any]) -> dict[str, object]:
    """Check a bounded FHIR R4-shaped synthetic Bundle's local relationships.

    The synthetic marker is a caller assertion, never proof that input lacks
    patient data. The returned summary contains NO names, patient IDs,
    references, original entry contents or file paths. Passing this preflight
    does NOT assert schema/profile/terminology/full-reference conformance.
    """
    if not isinstance(payload, dict):
        raise BundlePreflightError("bundle_not_object")
    if not set(payload).issubset({"resourceType", "id", "meta", "type", "entry"}):
        raise BundlePreflightError("unreviewed_bundle_field_refused")
    if payload.get("resourceType") != "Bundle" or payload.get("type") != "collection":
        raise BundlePreflightError("only_collection_bundle_supported")
    if not _synthetic_marker(payload):
        raise BundlePreflightError("explicit_synthetic_fixture_marker_required")
    entries = payload.get("entry")
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ENTRIES:
        raise BundlePreflightError("bundle_entry_count_out_of_range")

    resources: list[tuple[str, str, dict[str, Any]]] = []
    identities: set[str] = set()
    urls: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"fullUrl", "resource"}:
            raise BundlePreflightError("bundle_entry_structure_refused")
        full_url = entry["fullUrl"]
        if not isinstance(full_url, str) or not full_url.startswith("urn:uuid:"):
            raise BundlePreflightError("nonlocal_or_invalid_fullurl")
        try:
            suffix = full_url[len("urn:uuid:") :]
            if str(UUID(suffix)) != suffix:
                raise ValueError("noncanonical UUID")
        except (ValueError, AttributeError) as exc:
            raise BundlePreflightError("nonlocal_or_invalid_fullurl") from exc
        if full_url in urls:
            raise BundlePreflightError("duplicate_bundle_fullurl")
        resource = entry["resource"]
        kind, fhir_id = _resource_identity(resource)
        urls[full_url] = kind
        identity = kind + "/" + fhir_id
        if identity in identities:
            raise BundlePreflightError("duplicate_bundle_resource_identity")
        identities.add(identity)
        resources.append((kind, fhir_id, resource))

    # Bind each Encounter's local Patient subject to its fullUrl before
    # scanning Observations. The caller's entries may be in ANY order.
    # Merely confirming that Observation.encounter resolves to *some*
    # Encounter is insufficient: a multi-patient Bundle could otherwise
    # silently associate another Patient's Encounter with an Observation.
    encounter_patients: dict[str, str] = {
        entry["fullUrl"]: _ref(entry["resource"], "subject")
        for entry in entries
        if entry["resource"]["resourceType"] == "Encounter"
    }

    # All local identities are known before checking forward references.
    checked_references = 0
    for kind, _, resource in resources:
        if kind in {"Encounter", "Observation"}:
            patient = _ref(resource, "subject")
            if patient not in urls:
                raise BundlePreflightError("unresolved_local_patient_reference")
            if urls[patient] != "Patient":
                raise BundlePreflightError("local_reference_target_type_mismatch")
            checked_references += 1
        if kind == "Observation" and "encounter" in resource:
            encounter = _ref(resource, "encounter")
            if encounter not in urls:
                raise BundlePreflightError("unresolved_local_encounter_reference")
            if urls[encounter] != "Encounter":
                raise BundlePreflightError("local_reference_target_type_mismatch")
            if encounter_patients[encounter] != patient:
                raise BundlePreflightError("observation_encounter_patient_mismatch")
            checked_references += 1

    counts = Counter(kind for kind, _, _ in resources)
    return {
        "schema": _REPORT_SCHEMA,
        "status": "local_relationship_preflight_only",
        "source_content_sha256": content_hash(payload),
        "data_class": "SYNTHETIC_ASSERTED_NOT_VERIFIED",
        "resource_count": len(resources),
        "resource_counts": {kind: counts.get(kind, 0) for kind in sorted(_ALLOWED_RESOURCE_KEYS)},
        "local_references_checked": checked_references,
        "payload_content_included": False,
        "input_persisted": False,
        "network_access_performed": False,
        "full_fhir_r4_conformance_established": False,
        "terminology_profiles_invariants_verified": False,
        "all_possible_reference_fields_verified": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }
