"""Real encrypted Workspace synthetic FHIR readback, with source/audit checks.

All fixtures and identities are invented. Test-only in-memory key providers,
no clinical data, external destination, network, or full FHIR-R4 claims.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "workspace" / "src"))

from medscale_workspace.binding import ObjectBinding  # noqa: E402
from medscale_workspace.fhir_readback import (  # noqa: E402
    SyntheticFhirReadbackError,
    read_synthetic_fhir_bundle_in_memory,
)
from medscale_workspace.identity import WorkspaceObjectType  # noqa: E402
from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret  # noqa: E402
from medscale_workspace.storage import (  # noqa: E402
    ObjectWrite,
    WorkspaceStore,
)

from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic  # noqa: E402
from medscale.fhirkit.workspace_readback import (  # noqa: E402
    SyntheticWorkspaceReadbackError,
    read_synthetic_bundle_in_memory,
)

WORKSPACE = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
TIME = "2026-11-04T04:00:00+03:00"
ACTOR = "fictional-actor"
FIXTURE = ROOT / "examples" / "synthetic_fhir_bundle_preflight" / "fictional_bundle.json"


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _store(root: Path, provider: InMemoryTestKeyProvider) -> WorkspaceStore:
    return WorkspaceStore.open(
        store_root=str(root),
        workspace_id=WORKSPACE,
        key_provider=provider,
        application_version="0.1.0.dev1",
    )


def _ingest(store: WorkspaceStore, provider: InMemoryTestKeyProvider, value: dict):
    return ingest_synthetic_bundle_atomic(
        value,
        store,
        test_key_provider=provider,
        actor_id=ACTOR,
        occurred_at=TIME,
        synthetic_only=True,
    )


def _read(
    store: WorkspaceStore,
    provider: object,
    receipt: dict[str, object],
    **overrides: object,
):
    args = {
        "test_key_provider": provider,
        "source_content_sha256": receipt["source_content_sha256"],
        "expected_audit_head_digest": receipt["audit_head_digest"],
        "actor_id": ACTOR,
        "synthetic_only": True,
        "allow_in_memory_readback": True,
    }
    args.update(overrides)
    return read_synthetic_bundle_in_memory(store, **args)


def test_roundtrip_original_uuid_bundle_source_digest_and_encryption(tmp_path: Path) -> None:
    original = _fixture()
    expected = _canonical(original)
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _ingest(store, provider, original)
        assert store.object_count() == 8
        original["entry"][0]["resource"]["valueString"] = "CHANGED AFTER COMMIT"
    with _store(tmp_path, provider) as reopened:
        result = _read(reopened, provider, receipt)
        assert result["schema"] == "medorigin-core-synthetic-fhir-memory-readback/v1"
        assert _canonical(result["bundle"]) == expected
        assert (
            hashlib.sha256(_canonical(result["bundle"])).hexdigest()
            == receipt["source_content_sha256"]
        )
        assert result["resource_count"] == 3
        assert result["filesystem_export_performed"] is False
        assert result["clinical_use_authorized"] is False
        assert result["full_fhir_r4_conformance_established"] is False
        assert result["release_authorized"] is False
        # Returning an intentionally authorized in-memory object is different
        # from printing, logging, or exporting it. The DB stays ciphertext.
        assert b"Synthetic Example Only" not in Path(reopened.store_path).read_bytes()
        assert b"urn:uuid" not in Path(reopened.store_path).read_bytes()
        assert all(entry["fullUrl"].startswith("urn:uuid:") for entry in result["bundle"]["entry"])


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"synthetic_only": False}, "explicit_synthetic_attestation_required"),
        ({"allow_in_memory_readback": False}, "explicit_in_memory_readback_required"),
        ({"actor_id": "different-actor"}, "source_import_event_anchor_mismatch"),
        ({"source_content_sha256": "f" * 64}, "source_manifest_missing"),
        ({"source_content_sha256": "not-a-digest"}, "source_or_audit_anchor_refused"),
        ({"expected_audit_head_digest": "0" * 64}, "audit_head_anchor_mismatch"),
        ({"expected_audit_head_digest": ""}, "source_or_audit_anchor_refused"),
    ],
)
def test_refuses_unauthorized_actor_attestation_or_anchors(
    tmp_path: Path, change: dict[str, object], reason: str
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _fixture())
        with pytest.raises(SyntheticWorkspaceReadbackError, match=reason):
            _read(store, provider, receipt, **change)
        assert store.object_count() == 8


def test_refuses_different_in_memory_key_provider_even_if_store_is_open(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _fixture())
        other = InMemoryTestKeyProvider(new_root_secret())
        with pytest.raises(
            SyntheticWorkspaceReadbackError, match="workspace_key_provider_mismatch"
        ):
            _read(store, other, receipt)
        assert store.object_count() == 8


def test_direct_workspace_boundary_requires_separate_explicit_authorization(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _fixture())
        with pytest.raises(
            SyntheticFhirReadbackError,
            match="explicit_in_memory_readback_authorization_required",
        ):
            read_synthetic_fhir_bundle_in_memory(
                store=store,
                test_key_provider=provider,
                source_content_sha256=receipt["source_content_sha256"],
                expected_audit_head_digest=receipt["audit_head_digest"],
                actor_id=ACTOR,
                synthetic_only=True,
            )


def test_deleted_manifest_cannot_be_reconstructed_from_normalized_resources(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _fixture())
        from medscale_workspace.identity import synthetic_identity

        manifest = synthetic_identity(
            WORKSPACE, WorkspaceObjectType.FHIR_IMPORT_MANIFEST, receipt["source_content_sha256"]
        )
        binding = ObjectBinding(
            WORKSPACE, manifest.object_id, WorkspaceObjectType.FHIR_IMPORT_MANIFEST, "1"
        )
        assert store.delete_object(binding)
        with pytest.raises(SyntheticWorkspaceReadbackError, match="source_manifest_missing"):
            _read(store, provider, receipt)


def test_missing_resource_or_provenance_blocks_readback(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _fixture())
        from medscale_workspace import fhir_r4 as fhir
        from medscale_workspace.provenance import provenance_binding_for

        patient_id = fhir.resource_id_for(
            WORKSPACE, fhir.FhirResourceType.PATIENT, "synthetic-patient-001", "1"
        )
        patient_binding = fhir.resource_binding(WORKSPACE, patient_id)
        assert store.delete_object(provenance_binding_for(patient_binding))
        with pytest.raises(SyntheticWorkspaceReadbackError):
            _read(store, provider, receipt)


def test_extra_revision_for_member_is_not_silently_preferred(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _fixture())
        from medscale_workspace import fhir_r4 as fhir

        patient_id = fhir.resource_id_for(
            WORKSPACE, fhir.FhirResourceType.PATIENT, "synthetic-patient-001", "1"
        )
        store.put_objects_atomic(
            (
                ObjectWrite(
                    ObjectBinding(WORKSPACE, patient_id, WorkspaceObjectType.FHIR_RESOURCE, "2"),
                    b'{"fictional":"conflicting revision"}',
                ),
            )
        )
        with pytest.raises(
            SyntheticWorkspaceReadbackError, match="unapproved_resource_revision_present"
        ):
            _read(store, provider, receipt)


def test_in_memory_modified_snapshot_fails_provenance_or_audit_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _fixture())
        actual = store.export_snapshot()
        old = next(
            item
            for item in actual.objects
            if item.binding.object_type is WorkspaceObjectType.FHIR_RESOURCE
        )
        corrupted = replace(old, payload=old.payload.replace(b"fictional result", b"wrong data"))
        changed = replace(
            actual, objects=tuple(corrupted if item is old else item for item in actual.objects)
        )
        monkeypatch.setattr(store, "export_snapshot", lambda: changed)
        with pytest.raises(SyntheticWorkspaceReadbackError):
            _read(store, provider, receipt)


def test_direct_manifest_sha_matches_canonical_original_and_not_normalized(
    tmp_path: Path,
) -> None:
    original = _fixture()
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _ingest(store, provider, original)
        value = read_synthetic_fhir_bundle_in_memory(
            store=store,
            test_key_provider=provider,
            source_content_sha256=receipt["source_content_sha256"],
            expected_audit_head_digest=receipt["audit_head_digest"],
            actor_id=ACTOR,
            synthetic_only=True,
            allow_in_memory_readback=True,
        )
        assert value["source_content_sha256"] == hashlib.sha256(_canonical(original)).hexdigest()
        assert _canonical(value["bundle"]) == _canonical(original)
        assert value["filesystem_export_performed"] is False
