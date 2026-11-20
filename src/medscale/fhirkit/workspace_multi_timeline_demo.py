"""Two genuine encrypted fictional FHIR imports -> independent per-import timelines.

Standalone real Core+Workspace CLI demonstration. No caller file, network,
patient identity, user-supplied key or production clinical authorization.
"""

from __future__ import annotations

# mypy: disable-error-code="import-not-found"
# The Workspace package under apps/workspace is deliberately outside strict mypy's
# file set while Issue #464 item 1 is open; it is imported at runtime. Declaring
# the missing import here keeps that deferral explicit.
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import UUID

from medscale.fhirkit.workspace_demo import _fictional_bundle

_WORKSPACE = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
_ACTOR = "fictional-multi-timeline"
_TIME = "2026-11-04T08:00:00+03:00"


def _second_fictional_timeline_bundle() -> dict[str, object]:
    # Any: hardcoded invented fixture of a known nested shape.
    source: dict[str, Any] = copy.deepcopy(_fictional_bundle())
    mapping = {
        f"urn:uuid:00000000-0000-4000-8000-{n:012d}": (
            f"urn:uuid:00000000-0000-4000-8000-{n + 3:012d}"
        )
        for n in (1, 2, 3)
    }
    for item in source["entry"]:
        item["fullUrl"] = mapping[item["fullUrl"]]
        resource = item["resource"]
        resource["id"] = resource["id"].replace("-001", "-002")
        if "subject" in resource:
            resource["subject"]["reference"] = mapping[resource["subject"]["reference"]]
        if "encounter" in resource:
            resource["encounter"]["reference"] = mapping[resource["encounter"]["reference"]]
    source["entry"][0]["resource"]["effectiveDateTime"] = "2026-11-05T00:10:00Z"
    source["entry"][2]["resource"]["period"] = {
        "start": "2026-11-04T22:20:00Z",
        "end": "2026-11-04T23:00:00Z",
    }
    return source


def run_fictional_multiimport_timeline_demo(
    *,
    from_day_utc: str | None = None,
    through_day_utc: str | None = None,
    resource_type: str | None = None,
) -> dict[str, object]:
    from medscale_workspace.audit import AuditEventType, AuditTrail
    from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret
    from medscale_workspace.storage import WorkspaceStore

    from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic
    from medscale.fhirkit.workspace_multi_timeline import (
        SyntheticMultiImportTimelineError,
        _checked_day,
        list_filtered_verified_synthetic_import_timelines,
        list_verified_synthetic_import_timelines,
    )

    # Reject bad view input before allocating an encrypted fictional store.
    start = _checked_day(from_day_utc)
    end = _checked_day(through_day_utc)
    if start is not None and end is not None and start > end:
        raise SyntheticMultiImportTimelineError("multi_timeline_filter_range_refused")
    if resource_type is not None and (
        type(resource_type) is not str or resource_type not in ("Encounter", "Observation")
    ):
        raise SyntheticMultiImportTimelineError("multi_timeline_filter_type_refused")
    filtered: dict[str, Any] | None = None

    first_bundle: dict[str, Any] = _fictional_bundle()
    first_bundle["entry"][0]["resource"]["effectiveDateTime"] = "2026-11-02T22:10:00-05:00"
    first_bundle["entry"][2]["resource"]["period"] = {
        "start": "2026-11-03T02:20:00Z",
        "end": "2026-11-03T03:00:00Z",
    }
    second_bundle = _second_fictional_timeline_bundle()

    provider = InMemoryTestKeyProvider(new_root_secret())
    with TemporaryDirectory(prefix="medorigin-fake-multi-timeline-") as directory:
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WORKSPACE,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as store:
            first = ingest_synthetic_bundle_atomic(
                first_bundle,
                store,
                test_key_provider=provider,
                actor_id=_ACTOR,
                occurred_at=_TIME,
                synthetic_only=True,
            )
            AuditTrail(store).append(
                event_type=AuditEventType.WORKSPACE_OPEN,
                actor_id="fictional-browser",
                occurred_at="2026-11-04T08:01:00+03:00",
            )
            second = ingest_synthetic_bundle_atomic(
                second_bundle,
                store,
                test_key_provider=provider,
                actor_id=_ACTOR,
                occurred_at="2026-11-04T08:02:00+03:00",
                synthetic_only=True,
            )
            if (
                store.object_count() != 17
                or AuditTrail(store)
                .verify(expected_head_event_digest=second["audit_head_digest"])
                .events_verified
                != 3
            ):
                raise ValueError("fictional_multi_timeline_import_refused")
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WORKSPACE,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as store:
            # Any: nested import/event fields are compared below.
            timeline: dict[str, Any] = list_verified_synthetic_import_timelines(
                store=store,
                test_key_provider=provider,
                actor_id=_ACTOR,
                expected_current_audit_head_digest=str(second["audit_head_digest"]),
                synthetic_only=True,
                allow_in_memory_listing=True,
                allow_in_memory_timeline=True,
            )
            if (
                timeline["import_count"] != 2
                or timeline["total_event_count"] != 4
                or timeline["current_audit_head_digest"] != second["audit_head_digest"]
                or [e["event_count"] for e in timeline["imports"]] != [2, 2]
                or [e["source_content_sha256"] for e in timeline["imports"]]
                != [first["source_content_sha256"], second["source_content_sha256"]]
                or timeline["imports"][0]["events"][0]["day_utc"] != "2026-11-03"
                or timeline["imports"][1]["events"][0]["day_utc"] != "2026-11-04"
                or timeline["cross_import_patient_identity_join_performed"] is not False
            ):
                raise ValueError("fictional_multi_timeline_source_contract_refused")
            if start is not None or end is not None or resource_type is not None:
                # Any: the view's count fields are compared below.
                filtered_view: dict[str, Any] = list_filtered_verified_synthetic_import_timelines(
                    store=store,
                    test_key_provider=provider,
                    actor_id=_ACTOR,
                    expected_current_audit_head_digest=str(second["audit_head_digest"]),
                    synthetic_only=True,
                    allow_in_memory_listing=True,
                    allow_in_memory_timeline=True,
                    from_day_utc=start,
                    through_day_utc=end,
                    resource_type=resource_type,
                )
                filtered = filtered_view
                if (
                    filtered_view["import_count"] != 2
                    or filtered_view["source_total_event_count"] != 4
                    or filtered_view["source_total_event_count"]
                    != filtered_view["visible_total_event_count"]
                    + filtered_view["hidden_total_event_count"]
                    or filtered_view["cross_import_patient_identity_join_performed"] is not False
                ):
                    raise ValueError("fictional_multi_timeline_filter_contract_refused")
    if Path(directory).exists():
        raise ValueError("fictional_multi_timeline_cleanup_refused")
    if filtered is not None:
        return {
            **filtered,
            "schema": "medorigin-core-fake-encrypted-filtered-multiimport-timeline-demo/v1",
            "status": "SYNTHETIC_VERIFIED_FILTERED_MULTIIMPORT_TIMELINES_PASS",
            "verified_audit_events": 3,
            "closed_and_reopened": True,
            "ephemeral_store_removed": True,
        }
    return {
        "schema": "medorigin-core-fake-encrypted-multiimport-timeline-demo/v1",
        "status": "SYNTHETIC_VERIFIED_MULTIPLE_IMPORT_TIMELINES_PASS",
        "import_count": timeline["import_count"],
        "event_count": timeline["total_event_count"],
        "verified_audit_events": 3,
        "imports": timeline["imports"],
        "closed_and_reopened": True,
        "ephemeral_store_removed": True,
        "cross_import_patient_identity_join_performed": False,
        "patient_identity_included": False,
        "resource_payload_included": False,
        "clinical_use_authorized": False,
        "fhir_r4_conformance_validated": False,
        "release_authorized": False,
    }


def receipt_json(
    *,
    from_day_utc: str | None = None,
    through_day_utc: str | None = None,
    resource_type: str | None = None,
) -> str:
    return json.dumps(
        run_fictional_multiimport_timeline_demo(
            from_day_utc=from_day_utc,
            through_day_utc=through_day_utc,
            resource_type=resource_type,
        ),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
