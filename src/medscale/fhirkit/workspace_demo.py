"""Portable, fictional-only, ephemeral encrypted Workspace CLI demonstration.

This module ships with Core but only imports optional Workspace at run time.
It accepts no caller-supplied FHIR data, network endpoint, path or key.
"""

from __future__ import annotations

# mypy: disable-error-code="import-not-found"
# The Workspace package under apps/workspace is deliberately outside strict mypy's
# file set while Issue #464 item 1 is open; it is imported at runtime. Declaring
# the missing import here keeps that deferral explicit.
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

_WORKSPACE_ID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
_TIME = "2026-11-04T04:00:00+03:00"
_TAG = {"system": "urn:medorigin:fixture-classification", "code": "synthetic"}


def _fictional_bundle() -> dict[str, object]:
    """Return a fresh hardcoded, nonclinical, invented three-resource input."""
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {"tag": [dict(_TAG)]},
        "entry": [
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000001",
                "resource": {
                    "resourceType": "Observation",
                    "id": "fictional-observation-001",
                    "status": "final",
                    "code": {"text": "fictional observation"},
                    "subject": {"reference": "urn:uuid:00000000-0000-4000-8000-000000000002"},
                    "encounter": {"reference": "urn:uuid:00000000-0000-4000-8000-000000000003"},
                    "valueString": "fictional value",
                },
            },
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000002",
                "resource": {
                    "resourceType": "Patient",
                    "id": "fictional-patient-001",
                    "active": True,
                    "name": [{"text": "Fictional Example Only"}],
                },
            },
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000003",
                "resource": {
                    "resourceType": "Encounter",
                    "id": "fictional-encounter-001",
                    "status": "finished",
                    "class": {"code": "AMB"},
                    "subject": {"reference": "urn:uuid:00000000-0000-4000-8000-000000000002"},
                },
            },
        ],
    }


def run_ephemeral_fictional_workspace_demo() -> dict[str, object]:
    """Execute actual encrypted Core + Workspace import without caller data.

    No output contains resource identity, name, any resource field,
    filesystem path or key. The temporary encrypted database is deleted
    before the receipt can be returned.
    """
    from medscale_workspace.audit import AuditTrail
    from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret
    from medscale_workspace.storage import WorkspaceStore

    from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic
    from medscale.fhirkit.workspace_readback import read_synthetic_bundle_in_memory

    fictional = _fictional_bundle()
    provider = InMemoryTestKeyProvider(new_root_secret())
    with TemporaryDirectory(prefix="medorigin-fictional-core-") as directory:
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WORKSPACE_ID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as store:
            result = ingest_synthetic_bundle_atomic(
                fictional,
                store,
                test_key_provider=provider,
                actor_id="fictional-core-demo",
                occurred_at=_TIME,
                synthetic_only=True,
            )
            if store.object_count() != 8 or AuditTrail(store).verify().events_verified != 1:
                raise ValueError("synthetic_workspace_demo_integrity_refused")

        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WORKSPACE_ID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as store:
            report = AuditTrail(store).verify(
                expected_head_event_digest=str(result["audit_head_digest"])
            )
            if store.object_count() != 8 or report.events_verified != 1:
                raise ValueError("synthetic_workspace_demo_reopen_refused")
            readback = read_synthetic_bundle_in_memory(
                store,
                test_key_provider=provider,
                source_content_sha256=str(result["source_content_sha256"]),
                expected_audit_head_digest=str(result["audit_head_digest"]),
                actor_id="fictional-core-demo",
                synthetic_only=True,
                allow_in_memory_readback=True,
            )
            if readback["bundle"] != fictional or readback["resource_count"] != 3:
                raise ValueError("synthetic_workspace_demo_readback_refused")
    if Path(directory).exists():
        raise ValueError("synthetic_workspace_demo_cleanup_refused")
    return {
        "schema": "medorigin-installed-ephemeral-fhir-workspace/v1",
        "status": "SYNTHETIC_ENCRYPTED_ATOMIC_DEMO_PASS",
        "resource_count": result["resource_count"],
        "provenance_records": result["provenance_records_written"],
        "audit_events": result["audit_events_written"],
        "verified_reopen": True,
        "ephemeral_store_removed": True,
        "payload_included": False,
        "clinical_use_authorized": False,
        "full_fhir_r4_conformance_established": False,
        "production_key_provider_used": False,
        "publication_authorized": False,
    }


def receipt_json() -> str:
    """Serialize only bounded non-sensitive aggregate demo metadata."""
    return json.dumps(
        run_ephemeral_fictional_workspace_demo(),
        sort_keys=True,
        separators=(",", ":"),
    )
