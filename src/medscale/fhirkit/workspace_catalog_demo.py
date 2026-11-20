"""Installed Core CLI demonstration: discover two fictional encrypted FHIR imports.

No external Bundle, path, key, network, patient data or persisted output is
accepted. Both resources are hardcoded invented fixtures, not clinical cases.
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

_WORKSPACE = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
_ACTOR = "fictional-catalog-demo"
_TIME = "2026-11-04T04:00:00+03:00"


def _other_fictional_bundle() -> dict[str, object]:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {"tag": [{"system": "urn:medorigin:fixture-classification", "code": "synthetic"}]},
        "entry": [
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000004",
                "resource": {
                    "resourceType": "Patient",
                    "id": "fictional-catalog-patient-004",
                    "name": [{"text": "Fictional Catalog Example Only"}],
                    "active": True,
                },
            }
        ],
    }


def run_fictional_catalog_demo() -> dict[str, object]:
    """Prove actual import -> reopen -> safe verified source catalog in RAM."""
    from medscale_workspace.audit import AuditEventType, AuditTrail
    from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret
    from medscale_workspace.storage import WorkspaceStore

    from medscale.fhirkit.workspace_catalog import list_synthetic_bundle_imports
    from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic

    first = _fictional_bundle()
    second = _other_fictional_bundle()
    provider = InMemoryTestKeyProvider(new_root_secret())
    with TemporaryDirectory(prefix="medorigin-fictional-catalog-") as directory:
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WORKSPACE,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as store:
            previous = ingest_synthetic_bundle_atomic(
                first,
                store,
                test_key_provider=provider,
                actor_id=_ACTOR,
                occurred_at=_TIME,
                synthetic_only=True,
            )
            AuditTrail(store).append(
                event_type=AuditEventType.WORKSPACE_OPEN,
                actor_id="fictional-ui-operator",
                occurred_at="2026-11-04T04:01:00+03:00",
            )
            latest = ingest_synthetic_bundle_atomic(
                second,
                store,
                test_key_provider=provider,
                actor_id=_ACTOR,
                occurred_at="2026-11-04T04:02:00+03:00",
                synthetic_only=True,
            )
            if store.object_count() != 13:
                raise ValueError("fictional_catalog_store_count_refused")
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WORKSPACE,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as reopened:
            report = AuditTrail(reopened).verify(
                expected_head_event_digest=str(latest["audit_head_digest"])
            )
            if report.events_verified != 3 or reopened.object_count() != 13:
                raise ValueError("fictional_catalog_reopen_refused")
            # Any: hardcoded-fixture demo; every field read is compared below.
            catalog: dict[str, Any] = list_synthetic_bundle_imports(
                reopened,
                test_key_provider=provider,
                actor_id=_ACTOR,
                expected_current_audit_head_digest=str(latest["audit_head_digest"]),
                synthetic_only=True,
                allow_in_memory_listing=True,
            )
            expected = [
                (previous["source_content_sha256"], previous["audit_head_digest"], 1, 3),
                (latest["source_content_sha256"], latest["audit_head_digest"], 3, 1),
            ]
            if (
                catalog["import_count"] != 2
                or [
                    (
                        entry["source_content_sha256"],
                        entry["import_audit_event_digest"],
                        entry["audit_sequence"],
                        entry["resource_count"],
                    )
                    for entry in catalog["imports"]
                ]
                != expected
            ):
                raise ValueError("fictional_catalog_verified_entries_refused")
    if Path(directory).exists():
        raise ValueError("fictional_catalog_ephemeral_cleanup_refused")
    return {
        "schema": "medorigin-ephemeral-fhir-import-catalog-demo/v1",
        "status": "SYNTHETIC_ENCRYPTED_CATALOG_DEMO_PASS",
        "import_count": catalog["import_count"],
        "resource_count": sum(item["resource_count"] for item in catalog["imports"]),
        "verified_audit_events": 3,
        "imports": catalog["imports"],
        "ephemeral_store_removed": True,
        "payload_included": False,
        "clinical_use_authorized": False,
        "full_fhir_r4_conformance_established": False,
        "publication_authorized": False,
    }


def receipt_json() -> str:
    return json.dumps(
        run_fictional_catalog_demo(),
        sort_keys=True,
        separators=(",", ":"),
    )
