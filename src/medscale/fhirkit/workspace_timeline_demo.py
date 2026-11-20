"""One real encrypted, fictional patient-activity timeline from Core/Workspace.

Only a hardcoded invented 3-resource local FHIR Bundle is admitted.
The ephemeral AES-GCM Workspace is closed, reopened, verified, and removed
before returning metadata. Never patient data or clinical release.
"""

from __future__ import annotations

# mypy: disable-error-code="import-not-found"
# The Workspace package under apps/workspace is deliberately outside strict mypy's
# file set while Issue #464 item 1 is open; it is imported at runtime. Declaring
# the missing import here keeps that deferral explicit.
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import UUID

from medscale.fhirkit.workspace_demo import _fictional_bundle

_WID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
_ACTOR = "fictional-timeline-owner"
_TIME1 = "2026-11-04T08:00:00+03:00"
_TIME2 = "2026-11-04T08:10:00+03:00"


def run_fictional_encrypted_timeline_demo() -> dict[str, object]:
    """Use actual encrypted Workspace, provenance, audit, and timeline ordering."""
    from medscale_workspace.audit import AuditEventType, AuditTrail
    from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret
    from medscale_workspace.storage import WorkspaceStore

    from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic
    from medscale.fhirkit.workspace_timeline import read_verified_synthetic_patient_timeline

    # Any: hardcoded invented fixture of a known nested shape.
    source: dict[str, Any] = _fictional_bundle()
    source["entry"][0]["resource"]["effectiveDateTime"] = "2026-11-02T22:10:00-05:00"
    source["entry"][2]["resource"]["period"] = {
        "start": "2026-11-03T02:20:00Z",
        "end": "2026-11-03T03:00:00Z",
    }
    provider = InMemoryTestKeyProvider(new_root_secret())
    with TemporaryDirectory(prefix="medorigin-fictional-timeline-") as directory:
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as store:
            imported: dict[str, Any] = ingest_synthetic_bundle_atomic(
                source,
                store,
                test_key_provider=provider,
                actor_id=_ACTOR,
                occurred_at=_TIME1,
                synthetic_only=True,
            )
            if store.object_count() != 8:
                raise ValueError("fictional_timeline_import_count_refused")
            benign = AuditTrail(store).append(
                event_type=AuditEventType.WORKSPACE_OPEN,
                actor_id=_ACTOR,
                occurred_at=_TIME2,
            )
            if (
                AuditTrail(store)
                .verify(expected_head_event_digest=benign.event_digest)
                .events_verified
                != 2
            ):
                raise ValueError("fictional_timeline_audit_refused")
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as reopened:
            timeline: dict[str, Any] = read_verified_synthetic_patient_timeline(
                store=reopened,
                test_key_provider=provider,
                source_content_sha256=imported["source_content_sha256"],
                import_audit_event_digest=imported["audit_head_digest"],
                expected_current_audit_head_digest=benign.event_digest,
                actor_id=_ACTOR,
                synthetic_only=True,
                allow_in_memory_timeline=True,
            )
            if (
                timeline["event_count"] != 2
                or timeline["undated_event_count"] != 0
                or [e["resource_type"] for e in timeline["timeline"]]
                != ["Encounter", "Observation"]
                or [e["day_utc"] for e in timeline["timeline"]] != ["2026-11-03", "2026-11-03"]
                or timeline["current_audit_head_digest"] != benign.event_digest
                or timeline["fhir_r4_conformance_validated"] is not False
                or timeline["clinical_use_authorized"] is not False
            ):
                raise ValueError("fictional_timeline_order_or_proof_refused")
    if Path(directory).exists():
        raise ValueError("fictional_timeline_temporary_workspace_cleanup_refused")
    return {
        "schema": "medorigin-core-fake-encrypted-activity-timeline-demo/v1",
        "status": "SYNTHETIC_SOURCE_VERIFIED_TIMELINE_PASS",
        "source_content_sha256": timeline["source_content_sha256"],
        "import_audit_event_digest": timeline["import_audit_event_digest"],
        "current_audit_head_digest": timeline["current_audit_head_digest"],
        "resource_count": imported["resource_count"],
        "timeline": timeline["timeline"],
        "event_count": timeline["event_count"],
        "audit_events_verified": 2,
        "closed_and_reopened": True,
        "ephemeral_store_removed": True,
        "patient_identity_included": False,
        "resource_payload_included": False,
        "fhir_r4_conformance_validated": False,
        "clinical_use_authorized": False,
        "release_authorized": False,
    }


def timeline_json() -> str:
    return json.dumps(
        run_fictional_encrypted_timeline_demo(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
