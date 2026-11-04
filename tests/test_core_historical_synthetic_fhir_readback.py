"""Bounded historical synthetic Bundle readback with two outside audit anchors.

All payloads are fictional. No PHI, plaintext disk export, general FHIR
conformance or production access is authorized by this test fixture.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "workspace" / "src"))

from medscale_workspace import fhir_r4 as fhir  # noqa: E402
from medscale_workspace.audit import (  # noqa: E402
    AuditEventType,
    AuditObjectRef,
    AuditTrail,
)
from medscale_workspace.identity import WorkspaceObjectType  # noqa: E402
from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret  # noqa: E402
from medscale_workspace.storage import ObjectWrite, WorkspaceStore  # noqa: E402

from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic  # noqa: E402
from medscale.fhirkit.workspace_readback import (  # noqa: E402
    SyntheticWorkspaceReadbackError,
    read_synthetic_bundle_in_memory,
)

WORKSPACE = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
ACTOR = "fictional-actor"
TIME = "2026-11-04T04:00:00+03:00"
ORIGINAL = ROOT / "examples" / "synthetic_fhir_bundle_preflight" / "fictional_bundle.json"


def _open(root: Path, provider: InMemoryTestKeyProvider) -> WorkspaceStore:
    return WorkspaceStore.open(
        store_root=str(root),
        workspace_id=WORKSPACE,
        key_provider=provider,
        application_version="0.1.0.dev1",
    )


def _initial_bundle() -> dict[str, object]:
    return json.loads(ORIGINAL.read_text(encoding="utf-8"))


def _ingest(store: WorkspaceStore, provider: InMemoryTestKeyProvider, bundle: dict):
    return ingest_synthetic_bundle_atomic(
        bundle,
        store,
        test_key_provider=provider,
        actor_id=ACTOR,
        occurred_at=TIME,
        synthetic_only=True,
    )


def _read(store, provider, receipt, **extra):
    args = {
        "test_key_provider": provider,
        "source_content_sha256": receipt["source_content_sha256"],
        "expected_audit_head_digest": receipt["audit_head_digest"],
        "actor_id": ACTOR,
        "synthetic_only": True,
        "allow_in_memory_readback": True,
    }
    args.update(extra)
    return read_synthetic_bundle_in_memory(store, **args)


def _append(store, event_type=AuditEventType.WORKSPACE_OPEN, refs=()):
    return AuditTrail(store).append(
        event_type=event_type,
        actor_id="fictional-workspace-operator",
        occurred_at="2026-11-04T04:01:00+03:00",
        object_refs=refs,
    )


def test_historical_readback_after_unrelated_workspace_audit_and_reopen(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    original = _initial_bundle()
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, original)
        later = _append(store)
        assert later.event_digest != receipt["audit_head_digest"]
        assert store.object_count() == 9

    with _open(tmp_path, provider) as reopened:
        with pytest.raises(SyntheticWorkspaceReadbackError, match="audit_head_anchor_mismatch"):
            _read(reopened, provider, receipt)  # Old API still fail-closed.

        recovered = _read(
            reopened,
            provider,
            receipt,
            expected_current_audit_head_digest=later.event_digest,
        )
        assert recovered["bundle"] == original
        assert recovered["audit_head_digest"] == receipt["audit_head_digest"]
        assert recovered["current_audit_head_digest"] == later.event_digest
        assert recovered["filesystem_export_performed"] is False
        assert recovered["clinical_use_authorized"] is False
        assert recovered["full_fhir_r4_conformance_established"] is False
        assert recovered["release_authorized"] is False
        assert store_is_ciphertext(reopened)


def store_is_ciphertext(store: WorkspaceStore) -> bool:
    data = Path(store.store_path).read_bytes()
    return b"Synthetic Example Only" not in data and b"urn:uuid" not in data


def test_second_disjoint_encrypted_import_does_not_break_first_bundle(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    first = _initial_bundle()
    second = {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {"tag": [{"system": "urn:medorigin:fixture-classification", "code": "synthetic"}]},
        "entry": [
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000004",
                "resource": {
                    "resourceType": "Patient",
                    "id": "fictional-other-patient",
                    "active": True,
                    "name": [{"text": "Another Fictional Example"}],
                },
            }
        ],
    }
    with _open(tmp_path, provider) as store:
        first_receipt = _ingest(store, provider, first)
        second_receipt = _ingest(store, provider, second)
        assert store.object_count() == 12  # 8 + (1 resource + provenance + audit + manifest)
        current_anchor = second_receipt["audit_head_digest"]
    with _open(tmp_path, provider) as reopened:
        old = _read(
            reopened,
            provider,
            first_receipt,
            expected_current_audit_head_digest=current_anchor,
        )
        recent = _read(reopened, provider, second_receipt)
        assert old["bundle"] == first
        assert recent["bundle"] == second
        assert old["current_audit_head_digest"] == current_anchor
        assert recent["current_audit_head_digest"] == current_anchor


@pytest.mark.parametrize("invalid", [True, "", "x" * 64, "0" * 63, 3, []])
def test_current_audit_anchor_must_be_exact_sha256(tmp_path: Path, invalid: object) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _initial_bundle())
        with pytest.raises(SyntheticWorkspaceReadbackError, match="current_audit_anchor_refused"):
            _read(store, provider, receipt, expected_current_audit_head_digest=invalid)


def test_wrong_current_head_does_not_accept_historical_copy(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _initial_bundle())
        _append(store)
        with pytest.raises(SyntheticWorkspaceReadbackError, match="audit_head_anchor_mismatch"):
            _read(
                store,
                provider,
                receipt,
                expected_current_audit_head_digest="a" * 64,
            )


def test_current_anchor_does_not_override_original_import_anchor(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _initial_bundle())
        later = _append(store)
        with pytest.raises(
            SyntheticWorkspaceReadbackError,
            match="source_import_event_anchor_mismatch",
        ):
            _read(
                store,
                provider,
                receipt,
                expected_audit_head_digest="b" * 64,
                expected_current_audit_head_digest=later.event_digest,
            )


def test_later_audit_touching_imported_resource_is_not_treated_as_read_only(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _initial_bundle())
        patient = fhir.resource_id_for(
            WORKSPACE, fhir.FhirResourceType.PATIENT, "synthetic-patient-001", "1"
        )
        binding = fhir.resource_binding(WORKSPACE, patient)
        later = _append(
            store,
            AuditEventType.OBJECT_CREATE,
            (
                AuditObjectRef(
                    object_id=patient,
                    object_type=WorkspaceObjectType.FHIR_RESOURCE,
                    object_revision=binding.object_revision,
                ),
            ),
        )
        with pytest.raises(
            SyntheticWorkspaceReadbackError,
            match="post_import_resource_audit_refused",
        ):
            _read(
                store,
                provider,
                receipt,
                expected_current_audit_head_digest=later.event_digest,
            )


def test_later_destructive_audit_type_is_denied_even_without_refs(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _initial_bundle())
        later = _append(store, AuditEventType.OBJECT_DELETE)
        with pytest.raises(
            SyntheticWorkspaceReadbackError,
            match="post_import_audit_event_not_admitted",
        ):
            _read(
                store,
                provider,
                receipt,
                expected_current_audit_head_digest=later.event_digest,
            )


def test_new_resource_version_with_distinct_object_uuid_refuses_old_readback(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _initial_bundle())
        prior_id = fhir.resource_id_for(
            WORKSPACE, fhir.FhirResourceType.PATIENT, "synthetic-patient-001", "1"
        )
        old_binding = fhir.resource_binding(WORKSPACE, prior_id)
        old = fhir.FhirResource.from_document(
            json.loads(store.get_object(old_binding).decode("ascii"))
        )
        newer_id = fhir.resource_id_for(
            WORKSPACE, fhir.FhirResourceType.PATIENT, "synthetic-patient-001", "2"
        )
        assert newer_id != prior_id
        newer = replace(old, resource_id=newer_id, resource_version="2").validated()
        store.put_objects_atomic(
            (
                ObjectWrite(
                    binding=fhir.resource_binding(WORKSPACE, newer_id),
                    payload=fhir._canonical_bytes(newer.to_document()),
                ),
            )
        )
        with pytest.raises(
            SyntheticWorkspaceReadbackError,
            match="unapproved_logical_resource_revision_present",
        ):
            _read(store, provider, receipt)
