"""True installed Core+Workspace+official offline R4 encrypted receipt demo.

A single hardcoded, invented FHIR Bundle is used. There is no patient input,
output path, network, export, persisted file, or clinical admission. Only the
schema ZIP is caller-supplied and checked against an immutable HL7 SHA.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from medscale.fhirkit.workspace_demo import _fictional_bundle

_WID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
_ACTOR = "fictional-structural-demo"
_FIRST = "2026-11-04T04:00:00+03:00"
_SECOND = "2026-11-04T04:02:00+03:00"


def run_ephemeral_encrypted_structural_demo(archive: Path) -> dict[str, object]:
    """Import, validate official schema, encrypt Outcome, reopen and read."""
    from medscale_workspace.audit import AuditTrail
    from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret
    from medscale_workspace.storage import WorkspaceStore

    from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic
    from medscale.fhirkit.workspace_structural import (
        read_imported_synthetic_structural_result,
        validate_and_store_imported_synthetic_bundle_structure,
    )

    provider = InMemoryTestKeyProvider(new_root_secret())
    original = _fictional_bundle()
    with TemporaryDirectory(prefix="medorigin-fictional-r4-receipt-") as directory:
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as store:
            imported = ingest_synthetic_bundle_atomic(
                original,
                store,
                test_key_provider=provider,
                actor_id=_ACTOR,
                occurred_at=_FIRST,
                synthetic_only=True,
            )
            if store.object_count() != 8:
                raise ValueError("synthetic_source_import_integrity_refused")
            receipt = validate_and_store_imported_synthetic_bundle_structure(
                store=store,
                test_key_provider=provider,
                source_content_sha256=str(imported["source_content_sha256"]),
                import_audit_event_digest=str(imported["audit_head_digest"]),
                expected_current_audit_head_digest=str(imported["audit_head_digest"]),
                official_r4_schema_archive=archive,
                actor_id=_ACTOR,
                occurred_at=_SECOND,
                synthetic_only=True,
                allow_encrypted_receipt_write=True,
            )
            if store.object_count() != 11:
                raise ValueError("synthetic_structural_receipt_object_count_refused")
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as reopened:
            checked = AuditTrail(reopened).verify(
                expected_head_event_digest=str(receipt["audit_head_digest"])
            )
            recovered = read_imported_synthetic_structural_result(
                store=reopened,
                test_key_provider=provider,
                source_content_sha256=str(imported["source_content_sha256"]),
                import_audit_event_digest=str(imported["audit_head_digest"]),
                expected_current_audit_head_digest=str(receipt["audit_head_digest"]),
                expected_receipt_sha256=str(receipt["receipt_sha256"]),
                actor_id=_ACTOR,
                synthetic_only=True,
                allow_in_memory_readback=True,
            )
            if (
                checked.events_verified != 2
                or reopened.object_count() != 11
                or recovered["structural_status"] != receipt["structural_status"]
                or recovered["receipt_sha256"] != receipt["receipt_sha256"]
                or recovered["outcome"]["resourceType"] != "OperationOutcome"
                or recovered["outcome"]["issue"][-1]["severity"] != "warning"
            ):
                raise ValueError("synthetic_structural_reopen_verification_refused")
            issue_count = len(recovered["outcome"]["issue"])
    if Path(directory).exists():
        raise ValueError("synthetic_structural_temp_cleanup_refused")
    return {
        "schema": "medorigin-synthetic-encrypted-r4-structural-demo/v1",
        "status": "SYNTHETIC_ENCRYPTED_R4_STRUCTURAL_RECEIPT_PASS",
        "structural_status": receipt["structural_status"],
        "source_content_sha256": receipt["source_content_sha256"],
        "receipt_sha256": receipt["receipt_sha256"],
        "audit_head_digest": receipt["audit_head_digest"],
        "encrypted_objects": 11,
        "outcome_issues": issue_count,
        "audit_events_verified": 2,
        "verified_reopen": True,
        "ephemeral_store_removed": True,
        "payload_included": False,
        "fhir_conformance_validated": False,
        "clinical_use_authorized": False,
        "release_authorized": False,
    }


def receipt_json(archive: Path) -> str:
    return json.dumps(
        run_ephemeral_encrypted_structural_demo(archive),
        sort_keys=True,
        separators=(",", ":"),
    )
