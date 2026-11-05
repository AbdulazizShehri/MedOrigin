"""Bounded, read-only timeline triage for fictional FHIR import batches.

Distinct from batch-bundle-diagnose: this checks the SAME temporal and
one-patient-per-source contract enforced before fictional encrypted import.
Only fixed, vetted error descriptions and source ordinals are displayed.
No FHIR profiles/terminology/clinical conformance, EHR, storage or PHI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from medscale.fhirkit.bundle import (
    BundlePreflightError,
    _synthetic_marker,
    inspect_synthetic_bundle,
)
from medscale.fhirkit.bundle_diagnostics import _FIXED_LOCAL_FAILURES
from medscale.fhirkit.input import MAX_FHIR_INPUT_BYTES
from medscale.fhirkit.workspace_timeline import SyntheticTimelineError, _events
from medscale.reproducibility import content_hash

_TIMELINE_DESCRIPTIONS = {
    "timeline_source_not_object": "The fictional timeline source must be a Bundle object.",
    "timeline_source_entry_limit_refused": "The timeline contains too many entries.",
    "timeline_entry_contract_refused": "The timeline has a malformed source entry.",
    "timeline_patient_count_refused": "The timeline has an unsupported patient count.",
    "explicit_patient_selection_required": "A patient must be chosen explicitly.",
    "selected_patient_not_found": "The selected fictional patient was not found.",
    "timeline_subject_reference_refused": "A fictional event has an invalid subject link.",
    "timeline_encounter_reference_refused": "An Observation has an invalid Encounter link.",
    "timeline_encounter_owner_refused": "An Encounter has an invalid patient owner.",
    "cross_patient_encounter_link_refused": "An Encounter links a different patient.",
    "timeline_encounter_period_refused": "An Encounter period has an invalid structure.",
    "timeline_encounter_period_start_required": "An Encounter period end requires a start.",
    "timeline_encounter_period_reversed": "An Encounter ends before it starts.",
    "timeline_encounter_timezone_timestamp_required": (
        "An Encounter period date-time must include an explicit timezone."
    ),
    "timeline_encounter_invalid": "An Encounter period has an impossible date-time.",
    "timeline_observation_timezone_timestamp_required": (
        "An Observation date-time must include an explicit timezone."
    ),
    "timeline_observation_invalid": "An Observation has an impossible date-time.",
    "timeline_event_count_refused": "The timeline exceeds the fictional event limit.",
}
_FIXED_SOURCE_DESCRIPTIONS = {
    "fictional_import_one_patient_per_source_required": (
        "A fictional import file must contain exactly one Patient."
    ),
    "fictional_import_source_resource_count_refused": (
        "A fictional import file exceeds the local resource limit."
    ),
    "fictional_import_duplicate_source_refused": (
        "This fictional Bundle duplicates a previously selected source."
    ),
}
_MAX_FILES = 4


class SyntheticFileBatchTriageError(ValueError):
    """No untrusted text, patient identity, source path, or JSON in refusals."""


def _failed(
    ordinal: int, stage: str, code: str, text: str
) -> dict[str, object]:
    """Use only fixed allowlisted literals; do not include source hash on failure."""
    return {
        "source_ordinal": ordinal,
        "status": "blocked",
        "stage": stage,
        "reason_code": code,
        "reason_text": text,
        "source_content_sha256": None,
        "resource_count": None,
        "timeline_event_count": None,
        "dated_event_count": None,
        "undated_event_count": None,
        "first_day_utc": None,
        "last_day_utc": None,
    }


def _ready(
    ordinal: int, digest: str, count: int, events: list[dict[str, object]],
    undated: int,
) -> dict[str, object]:
    days = [
        event["day_utc"]
        for event in events
        if event.get("date_available") is True
    ]
    dated = len(events) - undated
    if (
        type(undated) is not int
        or dated < 0
        or len(days) != dated
        or any(type(day) is not str or len(day) != 10 for day in days)
    ):
        raise SyntheticFileBatchTriageError("fictional_triage_event_contract_refused")
    dates = sorted(days)
    return {
        "source_ordinal": ordinal,
        "status": "ready_for_synthetic_readiness_only",
        "stage": "local_readiness",
        "reason_code": None,
        "reason_text": None,
        "source_content_sha256": digest,
        "resource_count": count,
        "timeline_event_count": len(events),
        "dated_event_count": dated,
        "undated_event_count": undated,
        "first_day_utc": dates[0] if dates else None,
        "last_day_utc": dates[-1] if dates else None,
    }


def triage_fictional_file_batch(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    synthetic_only: bool = False,
) -> dict[str, object]:
    """Return redacted, source-ordinal reasons even when one marked source fails.

    Refuse the ENTIRE operation before diagnostics if any source is unmarked,
    oversized, unbounded, non-JSON, or ambiguously represented. No temporary
    encrypted Workspace is allocated and no source is accepted for storage.
    """
    if synthetic_only is not True:
        raise SyntheticFileBatchTriageError("fictional_triage_synthetic_consent_required")
    if type(payloads) not in (list, tuple) or not 2 <= len(payloads) <= _MAX_FILES:
        raise SyntheticFileBatchTriageError("fictional_triage_file_count_refused")
    if any(type(p) is not dict or not _synthetic_marker(p) for p in payloads):
        raise SyntheticFileBatchTriageError("fictional_triage_marker_required")

    # Freeze and size-bound *all* source documents before allowing ANY
    # outward-facing response. The caller's objects are never returned.
    snapshots: list[dict[str, Any]] = []
    hashes: list[str] = []
    for source in payloads:
        entries = source.get("entry")
        if type(entries) is not list or len(entries) > 16:
            raise SyntheticFileBatchTriageError("fictional_triage_entry_bounds_refused")
        try:
            raw = json.dumps(
                source,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            if len(raw) > MAX_FHIR_INPUT_BYTES:
                raise SyntheticFileBatchTriageError("fictional_triage_input_size_refused")
            snapshot = json.loads(raw)
            digest = content_hash(snapshot)
        except SyntheticFileBatchTriageError:
            raise
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise SyntheticFileBatchTriageError(
                "fictional_triage_unqualified_source_refused"
            ) from exc
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise SyntheticFileBatchTriageError("fictional_triage_digest_refused")
        snapshots.append(snapshot)
        hashes.append(digest)

    source_reports: list[dict[str, object]] = []
    seen: set[str] = set()
    for ordinal, (snapshot, digest) in enumerate(zip(snapshots, hashes, strict=True), 1):
        if digest in seen:
            source_reports.append(
                _failed(
                    ordinal, "source_identity",
                    "fictional_import_duplicate_source_refused",
                    _FIXED_SOURCE_DESCRIPTIONS["fictional_import_duplicate_source_refused"],
                )
            )
            continue
        seen.add(digest)
        try:
            result = inspect_synthetic_bundle(snapshot)
        except BundlePreflightError as exc:
            reason = str(exc)
            if reason not in _FIXED_LOCAL_FAILURES:
                raise SyntheticFileBatchTriageError(
                    "fictional_triage_unqualified_relationship_failure"
                ) from exc
            source_reports.append(
                _failed(ordinal, "local_relationship", reason, _FIXED_LOCAL_FAILURES[reason])
            )
            continue
        count = result.get("resource_count")
        if (
            result.get("schema") != "medorigin-synthetic-fhir-bundle-preflight/v1"
            or result.get("status") != "local_relationship_preflight_only"
            or result.get("data_class") != "SYNTHETIC_ASSERTED_NOT_VERIFIED"
            or result.get("source_content_sha256") != digest
            or type(count) is not int
            or result.get("payload_content_included") is not False
            or result.get("input_persisted") is not False
            or result.get("network_access_performed") is not False
            or result.get("clinical_use_authorized") is not False
            or result.get("full_fhir_r4_conformance_established") is not False
        ):
            raise SyntheticFileBatchTriageError(
                "fictional_triage_positive_relationship_contract_refused"
            )
        if count > 16:
            source_reports.append(
                _failed(
                    ordinal, "source_limits",
                    "fictional_import_source_resource_count_refused",
                    _FIXED_SOURCE_DESCRIPTIONS[
                        "fictional_import_source_resource_count_refused"
                    ],
                )
            )
            continue
        if result.get("resource_counts", {}).get("Patient") != 1:
            source_reports.append(
                _failed(
                    ordinal, "source_limits",
                    "fictional_import_one_patient_per_source_required",
                    _FIXED_SOURCE_DESCRIPTIONS[
                        "fictional_import_one_patient_per_source_required"
                    ],
                )
            )
            continue
        try:
            events, patient_count, undated = _events(snapshot, None)
        except SyntheticTimelineError as exc:
            reason = str(exc)
            if reason not in _TIMELINE_DESCRIPTIONS:
                raise SyntheticFileBatchTriageError(
                    "fictional_triage_unqualified_timeline_failure"
                ) from exc
            source_reports.append(
                _failed(ordinal, "timeline", reason, _TIMELINE_DESCRIPTIONS[reason])
            )
            continue
        if patient_count != 1 or len(events) > count:
            raise SyntheticFileBatchTriageError(
                "fictional_triage_positive_timeline_contract_refused"
            )
        source_reports.append(_ready(ordinal, digest, count, events, undated))

    rejected = sum(item["status"] == "blocked" for item in source_reports)
    if not rejected:
        # A completely green triage must have EXACTLY the same authoritative
        # source identities and preview day/counts as the real no-store
        # readiness workflow, not merely a separately invented criterion.
        from medscale.fhirkit.workspace_file_readiness import (
            assess_fictional_file_batch_readiness,
        )

        try:
            baseline = assess_fictional_file_batch_readiness(
                snapshots, synthetic_only=True
            )
        except Exception as exc:
            raise SyntheticFileBatchTriageError(
                "fictional_triage_readiness_reconciliation_refused"
            ) from exc
        fields = (
            "source_ordinal", "source_content_sha256", "resource_count",
            "timeline_event_count", "dated_event_count",
            "undated_event_count", "first_day_utc", "last_day_utc",
        )
        if (
            baseline.get("source_count") != len(source_reports)
            or type(baseline.get("sources")) is not list
            or len(baseline["sources"]) != len(source_reports)
            or any(
                any(own.get(key) != other.get(key) for key in fields)
                for own, other in zip(
                    source_reports, baseline["sources"], strict=True
                )
            )
        ):
            raise SyntheticFileBatchTriageError(
                "fictional_triage_readiness_reconciliation_refused"
            )
    return {
        "schema": "medorigin-core-fictional-prestorage-file-triage/v1",
        "status": "SYNTHETIC_FILE_TRIAGE_ONLY_NOT_VALIDATED",
        "source_count": len(source_reports),
        "source_ready_count": len(source_reports) - rejected,
        "source_blocked_count": rejected,
        "all_sources_locally_ready": rejected == 0,
        "sources": source_reports,
        "source_filenames_included": False,
        "patient_identity_included": False,
        "precise_timestamps_included": False,
        "payload_included": False,
        "workspace_allocated": False,
        "output_persisted": False,
        "network_access_performed": False,
        "cross_source_patient_join_performed": False,
        "official_r4_schema_checked": False,
        "fhir_r4_conformance_validated": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }


def fictional_file_batch_triage_json(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    synthetic_only: bool = False,
) -> str:
    """Deterministic JSON; per-source diagnostics are intentionally finite."""
    return json.dumps(
        triage_fictional_file_batch(payloads, synthetic_only=synthetic_only),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"
