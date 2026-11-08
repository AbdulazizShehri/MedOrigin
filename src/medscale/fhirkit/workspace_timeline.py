"""A chronological, source-verified, fictional FHIR Workspace activity timeline.

The only supported records are already-encrypted, immutable synthetic
Patient/Encounter/Observation collection imports. Never user/PHI admission,
medical advice, a clinical timeline, or full HL7 FHIR conformance.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from medscale.fhirkit.workspace_readback import read_synthetic_bundle_in_memory

_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?"
    r"(?:Z|[+-]\d{2}:\d{2})\Z"
)
_MAX_ENTRIES = 16


class SyntheticTimelineError(ValueError):
    """Fixed redacted code: do not reproduce source payload, IDs or paths."""


def _instant(value: object, field: str) -> datetime:
    if type(value) is not str or len(value) > 40 or _TIMESTAMP.fullmatch(value) is None:
        raise SyntheticTimelineError("timeline_" + field + "_timezone_timestamp_required")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("missing timezone")
        return moment.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise SyntheticTimelineError("timeline_" + field + "_invalid") from exc


def _admit_source_and_patient(
    source: object, requested_patient: object
) -> tuple[str, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(source, dict):
        raise SyntheticTimelineError("timeline_source_not_object")
    entries = source.get("entry")
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ENTRIES:
        raise SyntheticTimelineError("timeline_source_entry_limit_refused")
    urls: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise SyntheticTimelineError("timeline_entry_contract_refused")
        ref, resource = entry.get("fullUrl"), entry.get("resource")
        if type(ref) is not str or not isinstance(resource, dict) or ref in urls:
            raise SyntheticTimelineError("timeline_entry_contract_refused")
        urls[ref] = resource

    patients = [ref for ref, resource in urls.items() if resource.get("resourceType") == "Patient"]
    if not 1 <= len(patients) <= _MAX_ENTRIES:
        raise SyntheticTimelineError("timeline_patient_count_refused")
    if requested_patient is None:
        if len(patients) != 1:
            raise SyntheticTimelineError("explicit_patient_selection_required")
        selected = patients[0]
    else:
        if type(requested_patient) is not str or requested_patient not in patients:
            raise SyntheticTimelineError("selected_patient_not_found")
        selected = requested_patient
    return selected, entries, urls


def _events(
    source: dict[str, Any], requested_patient: object
) -> tuple[list[dict[str, object]], int, int]:
    patient, entries, urls = _admit_source_and_patient(source, requested_patient)
    events: list[tuple[datetime | None, str]] = []
    patient_count = sum(r.get("resourceType") == "Patient" for r in urls.values())
    for entry in entries:
        resource = entry["resource"]
        kind = resource["resourceType"]
        if kind not in ("Encounter", "Observation"):
            continue
        subject = resource.get("subject")
        if not isinstance(subject, dict) or set(subject) != {"reference"}:
            raise SyntheticTimelineError("timeline_subject_reference_refused")
        related_patient = subject["reference"]

        # Enforce the SAME patient across Observation -> Encounter -> Patient.
        # Narrow upstream Bundle preflight checks types, not same-person graph.
        if kind == "Observation" and "encounter" in resource:
            encounter_field = resource["encounter"]
            if not isinstance(encounter_field, dict) or set(encounter_field) != {"reference"}:
                raise SyntheticTimelineError("timeline_encounter_reference_refused")
            encounter = urls.get(encounter_field["reference"])
            if not isinstance(encounter, dict) or encounter.get("resourceType") != "Encounter":
                raise SyntheticTimelineError("timeline_encounter_reference_refused")
            owner = encounter.get("subject")
            if not isinstance(owner, dict) or set(owner) != {"reference"}:
                raise SyntheticTimelineError("timeline_encounter_owner_refused")
            if owner["reference"] != related_patient:
                raise SyntheticTimelineError("cross_patient_encounter_link_refused")

        if related_patient != patient:
            continue

        moment: datetime | None = None
        if kind == "Encounter":
            period = resource.get("period")
            if period is not None:
                if not isinstance(period, dict) or not set(period).issubset({"start", "end"}):
                    raise SyntheticTimelineError("timeline_encounter_period_refused")
                if "end" in period and "start" not in period:
                    raise SyntheticTimelineError("timeline_encounter_period_start_required")
                if "start" in period:
                    # "end" without "start" was refused above, so an end bound
                    # is only ever compared against an admitted start instant.
                    start = _instant(period["start"], "encounter")
                    moment = start
                    if "end" in period and _instant(period["end"], "encounter") < start:
                        raise SyntheticTimelineError("timeline_encounter_period_reversed")
        elif "effectiveDateTime" in resource:
            moment = _instant(resource["effectiveDateTime"], "observation")
        events.append((moment, kind))
    if len(events) > _MAX_ENTRIES:
        raise SyntheticTimelineError("timeline_event_count_refused")

    # Strict timezone normalization; undated entries last, then type to
    # break ties without identifiers. No patient text, resource IDs or
    # precise time appears in the public returned metadata.
    events.sort(
        key=lambda item: (item[0] is None, item[0] or datetime.max.replace(tzinfo=UTC), item[1])
    )
    timeline: list[dict[str, object]] = [
        {
            "ordinal": i + 1,
            "resource_type": kind,
            "day_utc": moment.date().isoformat() if moment is not None else None,
            "date_available": moment is not None,
        }
        for i, (moment, kind) in enumerate(events)
    ]
    return timeline, patient_count, sum(moment is None for moment, _ in events)


def read_verified_synthetic_patient_timeline(
    *,
    store: object,
    test_key_provider: object,
    source_content_sha256: str,
    import_audit_event_digest: str,
    expected_current_audit_head_digest: str,
    actor_id: str,
    patient_local_reference: str | None = None,
    synthetic_only: bool = False,
    allow_in_memory_timeline: bool = False,
) -> dict[str, object]:
    """Source-verified, in-memory patient event timeline; no PHI export.

    The retained original import audit head and current independently
    anchored head are both required. Actor IDs are NOT authentication.
    """
    if synthetic_only is not True or allow_in_memory_timeline is not True:
        raise SyntheticTimelineError("explicit_synthetic_timeline_attestation_required")
    if type(source_content_sha256) is not str or type(import_audit_event_digest) is not str:
        raise SyntheticTimelineError("timeline_source_anchor_refused")
    if type(expected_current_audit_head_digest) is not str:
        raise SyntheticTimelineError("timeline_current_audit_anchor_refused")
    try:
        # Any: every field below is checked here; a wrong runtime type raises
        # inside this try and is refused by the generic handler, as before.
        checked: dict[str, Any] = read_synthetic_bundle_in_memory(
            store,
            test_key_provider=test_key_provider,
            source_content_sha256=source_content_sha256,
            expected_audit_head_digest=import_audit_event_digest,
            expected_current_audit_head_digest=expected_current_audit_head_digest,
            actor_id=actor_id,
            synthetic_only=True,
            allow_in_memory_readback=True,
        )
        if (
            checked["source_content_sha256"] != source_content_sha256
            or checked["audit_head_digest"] != import_audit_event_digest
            or checked["current_audit_head_digest"] != expected_current_audit_head_digest
            or checked["resource_count"] > _MAX_ENTRIES
            or any(
                checked.get(flag) is not False
                for flag in (
                    "filesystem_export_performed",
                    "clinical_use_authorized",
                    "full_fhir_r4_conformance_established",
                    "release_authorized",
                )
            )
        ):
            raise SyntheticTimelineError("timeline_verified_source_contract_refused")
        timeline, patients, undated = _events(checked["bundle"], patient_local_reference)
    except SyntheticTimelineError:
        raise
    except Exception as exc:
        raise SyntheticTimelineError("verified_encrypted_timeline_read_refused") from exc

    return {
        "schema": "medorigin-core-synthetic-verified-patient-timeline/v1",
        "status": "source_verified_fictional_timeline",
        "source_content_sha256": source_content_sha256,
        "import_audit_event_digest": import_audit_event_digest,
        "current_audit_head_digest": expected_current_audit_head_digest,
        "patient_count": patients,
        "selection_mode": "single_unique_patient"
        if patient_local_reference is None
        else "explicit_local_reference",
        "event_count": len(timeline),
        "undated_event_count": undated,
        "timeline": timeline,
        "patient_identity_included": False,
        "resource_payload_included": False,
        "filesystem_export_performed": False,
        "network_access_performed": False,
        "fhir_r4_conformance_validated": False,
        "clinical_use_authorized": False,
        "release_authorized": False,
    }
