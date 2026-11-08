"""Read-only pre-storage readiness for fictional local FHIR import batches.

A user-facing, source-scoped preview of the actual encrypted-import
preconditions and expected dated/undated activity. It creates NO SQLite
Workspace, chooses NO key, and reads NO EHR. A synthetic marker is only
an assertion, never a PHI detector or clinical authorization.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from medscale.fhirkit.workspace_file_batch_demo import _freeze_and_preflight
from medscale.fhirkit.workspace_timeline import SyntheticTimelineError, _events


class SyntheticFileBatchReadinessError(ValueError):
    """Fixed redacted refusal; no file paths, identities or FHIR payloads."""


def assess_fictional_file_batch_readiness(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    synthetic_only: bool = False,
    offline_r4_schema: Path | None = None,
) -> dict[str, object]:
    """Preview 2-4 invented sources using the SAME real import admission gate.

    The time-preview result is per source, never a cross-patient join. The
    optional source-pinned official R4 JSON Schema is structural ONLY.
    The only supported FHIR subset is Patient/Encounter/Observation;
    complete terminology, profiles, FHIRPath and clinical use are excluded.
    """
    if synthetic_only is not True:
        raise SyntheticFileBatchReadinessError("fictional_readiness_synthetic_attestation_required")
    if offline_r4_schema is not None and not isinstance(offline_r4_schema, Path):
        raise SyntheticFileBatchReadinessError("fictional_readiness_schema_path_refused")
    try:
        snapshots, proofs = _freeze_and_preflight(payloads)
    except Exception as exc:
        raise SyntheticFileBatchReadinessError(
            "fictional_readiness_source_preflight_refused"
        ) from exc

    # A caller-selected official ZIP, when requested, MUST qualify all
    # sources before any result is emitted. Never silently ignore failure.
    r4_status = "not_requested"
    if offline_r4_schema is not None:
        try:
            from medscale.fhirkit.workspace_file_r4_gate import (
                require_official_r4_structural_preflight,
            )

            gate = require_official_r4_structural_preflight(snapshots, proofs, offline_r4_schema)
            if (
                gate.get("status") != "OFFICIAL_R4_JSON_SCHEMA_STRUCTURE_ONLY_NOT_VALIDATED"
                or gate.get("structural_invalid_count") != 0
                or gate.get("structural_not_validated_count") != len(snapshots)
                or gate.get("clinical_use_authorized") is not False
                or gate.get("fhir_r4_conformance_validated") is not False
            ):
                raise ValueError("unqualified R4 gate")
        except Exception as exc:
            raise SyntheticFileBatchReadinessError(
                "fictional_readiness_official_r4_schema_refused"
            ) from exc
        r4_status = "official_r4_structure_only_not_validated"

    source_summaries: list[dict[str, object]] = []
    total_events = 0
    total_dated = 0
    total_undated = 0
    total_resources = 0
    for ordinal, (snapshot, preflight) in enumerate(zip(snapshots, proofs, strict=True), 1):
        try:
            events, patient_count, undated = _events(snapshot, None)
        except SyntheticTimelineError as exc:
            # Also checked in _freeze_and_preflight, but fail closed on any
            # unexpected divergence between the two preview passes.
            raise SyntheticFileBatchReadinessError("fictional_readiness_timeline_refused") from exc
        dated = len(events) - undated
        days = [event["day_utc"] for event in events if event["date_available"] is True]
        resource_counts = snapshot["entry"]
        expected_events = sum(
            item["resource"]["resourceType"] in ("Encounter", "Observation")
            for item in resource_counts
        )
        if (
            patient_count != 1
            or type(undated) is not int
            or undated < 0
            or dated < 0
            or len(events) != expected_events
            or len(days) != dated
            or any(type(day) is not str or len(day) != 10 for day in days)
        ):
            raise SyntheticFileBatchReadinessError("fictional_readiness_event_contract_refused")
        count = preflight["resource_count"]
        if type(count) is not int or count != len(snapshot["entry"]):
            raise SyntheticFileBatchReadinessError("fictional_readiness_resource_contract_refused")
        day_range = sorted(cast(list[str], days))  # each checked str above
        source_summaries.append(
            {
                "source_ordinal": ordinal,
                "source_content_sha256": preflight["source_content_sha256"],
                "resource_count": count,
                "timeline_event_count": len(events),
                "dated_event_count": dated,
                "undated_event_count": undated,
                "first_day_utc": day_range[0] if day_range else None,
                "last_day_utc": day_range[-1] if day_range else None,
            }
        )
        total_resources += count
        total_events += len(events)
        total_dated += dated
        total_undated += undated
    if total_events != total_dated + total_undated:
        raise SyntheticFileBatchReadinessError("fictional_readiness_totals_refused")
    return {
        "schema": "medorigin-core-fictional-file-batch-readiness/v1",
        "status": "SYNTHETIC_READ_ONLY_IMPORT_READINESS_NOT_VALIDATED",
        "source_count": len(snapshots),
        "total_resource_count": total_resources,
        "total_timeline_events": total_events,
        "total_dated_events": total_dated,
        "total_undated_events": total_undated,
        "sources": source_summaries,
        "official_r4_structural_status": r4_status,
        "source_filenames_included": False,
        "patient_identity_included": False,
        "precise_timestamps_included": False,
        "cross_source_patient_join_performed": False,
        "payload_included": False,
        "workspace_allocated": False,
        "output_persisted": False,
        "network_access_performed": False,
        "fhir_r4_conformance_validated": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }


def fictional_file_batch_readiness_json(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    synthetic_only: bool = False,
    offline_r4_schema: Path | None = None,
) -> str:
    """Machine-readable redacted dry-run result, never original JSON."""
    return (
        json.dumps(
            assess_fictional_file_batch_readiness(
                payloads,
                synthetic_only=synthetic_only,
                offline_r4_schema=offline_r4_schema,
            ),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    )
