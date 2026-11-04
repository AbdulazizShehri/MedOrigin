"""Bounded multi-import fictional patient activity timeline from encrypted Workspace.

Per-import chronology only; NEVER assume a Patient in one imported FHIR
Bundle is the same real or fictional Patient in another Bundle. No PHI,
production authentication, identity federation, FHIR profile validation,
clinical decision support, data export, network, or release permission.
"""

from __future__ import annotations

import re

from medscale.fhirkit.workspace_catalog import list_synthetic_bundle_imports
from medscale.fhirkit.workspace_timeline import read_verified_synthetic_patient_timeline

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_IMPORTS = 16
_MAX_EVENTS = 128


class SyntheticMultiImportTimelineError(ValueError):
    """Only a fixed redacted error token, never a source value or host path."""


def list_verified_synthetic_import_timelines(
    *,
    store: object,
    test_key_provider: object,
    actor_id: str,
    expected_current_audit_head_digest: str,
    synthetic_only: bool = False,
    allow_in_memory_listing: bool = False,
    allow_in_memory_timeline: bool = False,
    patient_selections: dict[str, str] | None = None,
    max_imports: int = 16,
    max_total_events: int = 128,
) -> dict[str, object]:
    """Return complete, source-bound per-import timelines, never joined patients.

    Zero partial results are emitted: if any original Bundle is unavailable,
    has a compromised audit anchor, invalid chronology, conflicting patient
    links, or an unselected multi-patient scope, the entire call fails.
    """
    if (
        synthetic_only is not True
        or allow_in_memory_listing is not True
        or allow_in_memory_timeline is not True
    ):
        raise SyntheticMultiImportTimelineError("multi_timeline_explicit_permissions_required")
    if (
        type(expected_current_audit_head_digest) is not str
        or _SHA256.fullmatch(expected_current_audit_head_digest) is None
    ):
        raise SyntheticMultiImportTimelineError("multi_timeline_current_anchor_refused")
    if (
        type(max_imports) is not int
        or not 1 <= max_imports <= _MAX_IMPORTS
        or type(max_total_events) is not int
        or not 1 <= max_total_events <= _MAX_EVENTS
    ):
        raise SyntheticMultiImportTimelineError("multi_timeline_bounds_refused")
    if patient_selections is not None and (
        type(patient_selections) is not dict
        or len(patient_selections) > max_imports
        or any(
            type(source) is not str
            or _SHA256.fullmatch(source) is None
            or type(patient_ref) is not str
            or not patient_ref.startswith("urn:uuid:")
            or len(patient_ref) > 48
            for source, patient_ref in patient_selections.items()
        )
    ):
        raise SyntheticMultiImportTimelineError("multi_timeline_patient_selection_refused")

    try:
        catalog = list_synthetic_bundle_imports(
            store,
            test_key_provider=test_key_provider,
            actor_id=actor_id,
            expected_current_audit_head_digest=expected_current_audit_head_digest,
            synthetic_only=True,
            allow_in_memory_listing=True,
            max_imports=max_imports,
        )
    except Exception as exc:
        raise SyntheticMultiImportTimelineError(
            "multi_timeline_catalog_verification_refused"
        ) from exc

    if (
        catalog.get("schema") != "medorigin-core-synthetic-import-catalog/v1"
        or catalog.get("status") != "verified_synthetic_import_catalog"
        or catalog.get("current_audit_head_digest") != expected_current_audit_head_digest
        or type(catalog.get("import_count")) is not int
        or type(catalog.get("imports")) is not list
        or catalog["import_count"] != len(catalog["imports"])
        or catalog["import_count"] > max_imports
        or any(
            catalog.get(flag) is not False
            for flag in (
                "payload_included",
                "filesystem_export_performed",
                "clinical_use_authorized",
                "full_fhir_r4_conformance_established",
                "release_authorized",
            )
        )
    ):
        raise SyntheticMultiImportTimelineError("multi_timeline_catalog_contract_refused")

    selected = patient_selections or {}
    known = {record["source_content_sha256"] for record in catalog["imports"]}
    if set(selected) - known:
        raise SyntheticMultiImportTimelineError("multi_timeline_unknown_patient_selection")

    aggregated: list[dict[str, object]] = []
    seen: set[str] = set()
    total_events = 0
    total_undated = 0
    prior_sequence = 0
    for record in catalog["imports"]:
        source = record["source_content_sha256"]
        original_audit = record["import_audit_event_digest"]
        sequence = record["audit_sequence"]
        if (
            type(source) is not str
            or _SHA256.fullmatch(source) is None
            or source in seen
            or type(original_audit) is not str
            or _SHA256.fullmatch(original_audit) is None
            or type(sequence) is not int
            or sequence <= prior_sequence
            or type(record["resource_count"]) is not int
            or not 1 <= record["resource_count"] <= 16
        ):
            raise SyntheticMultiImportTimelineError("multi_timeline_catalog_entry_refused")
        seen.add(source)
        prior_sequence = sequence
        try:
            result = read_verified_synthetic_patient_timeline(
                store=store,
                test_key_provider=test_key_provider,
                source_content_sha256=source,
                import_audit_event_digest=original_audit,
                expected_current_audit_head_digest=expected_current_audit_head_digest,
                actor_id=actor_id,
                patient_local_reference=selected.get(source),
                synthetic_only=True,
                allow_in_memory_timeline=True,
            )
        except Exception as exc:
            raise SyntheticMultiImportTimelineError(
                "multi_timeline_source_verification_refused"
            ) from exc

        events = result.get("timeline")
        count = result.get("event_count")
        undated = result.get("undated_event_count")
        patient_count = result.get("patient_count")
        if (
            result.get("schema") != "medorigin-core-synthetic-verified-patient-timeline/v1"
            or result.get("status") != "source_verified_fictional_timeline"
            or result.get("source_content_sha256") != source
            or result.get("import_audit_event_digest") != original_audit
            or result.get("current_audit_head_digest") != expected_current_audit_head_digest
            or result.get("selection_mode")
            != ("explicit_local_reference" if source in selected else "single_unique_patient")
            or type(count) is not int
            or not 0 <= count <= record["resource_count"]
            or type(undated) is not int
            or not 0 <= undated <= count
            or type(patient_count) is not int
            or not 1 <= patient_count <= record["resource_count"]
            or not isinstance(events, list)
            or len(events) != count
            or any(
                result.get(flag) is not False
                for flag in (
                    "patient_identity_included",
                    "resource_payload_included",
                    "filesystem_export_performed",
                    "network_access_performed",
                    "fhir_r4_conformance_validated",
                    "clinical_use_authorized",
                    "release_authorized",
                )
            )
        ):
            raise SyntheticMultiImportTimelineError("multi_timeline_source_contract_refused")

        # Rebuild only specifically reviewed scalar fields. Never relay
        # downstream arbitrary keys, patient IDs, identities or payloads.
        safe_events: list[dict[str, object]] = []
        for index, event in enumerate(events, 1):
            if (
                not isinstance(event, dict)
                or set(event) != {"ordinal", "resource_type", "day_utc", "date_available"}
                or type(event["ordinal"]) is not int
                or event["ordinal"] != index
                or event["resource_type"] not in ("Encounter", "Observation")
                or type(event["date_available"]) is not bool
                or (
                    event["day_utc"] is not None
                    and (
                        type(event["day_utc"]) is not str
                        or re.fullmatch(r"\d{4}-\d{2}-\d{2}", event["day_utc"]) is None
                    )
                )
                or (event["day_utc"] is None) != (not event["date_available"])
            ):
                raise SyntheticMultiImportTimelineError("multi_timeline_event_contract_refused")
            safe_events.append(
                {
                    "ordinal": index,
                    "resource_type": event["resource_type"],
                    "day_utc": event["day_utc"],
                    "date_available": event["date_available"],
                }
            )

        total_events += count
        total_undated += undated
        if total_events > max_total_events:
            raise SyntheticMultiImportTimelineError("multi_timeline_event_limit_refused")
        aggregated.append(
            {
                "import_ordinal": len(aggregated) + 1,
                "audit_sequence": sequence,
                "source_content_sha256": source,
                "import_audit_event_digest": original_audit,
                "source_resource_count": record["resource_count"],
                "patient_count_within_import": patient_count,
                "patient_selection_mode": result["selection_mode"],
                "event_count": count,
                "undated_event_count": undated,
                "events": safe_events,
            }
        )
    return {
        "schema": "medorigin-core-verified-fictional-multiimport-timelines/v1",
        "status": "verified_independent_import_timelines",
        "current_audit_head_digest": expected_current_audit_head_digest,
        "import_count": len(aggregated),
        "total_event_count": total_events,
        "total_undated_event_count": total_undated,
        "imports": aggregated,
        "cross_import_patient_identity_join_performed": False,
        "patient_identity_included": False,
        "resource_payload_included": False,
        "filesystem_export_performed": False,
        "network_access_performed": False,
        "fhir_r4_conformance_validated": False,
        "clinical_use_authorized": False,
        "release_authorized": False,
    }
