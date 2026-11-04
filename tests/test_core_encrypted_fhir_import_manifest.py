"""Synthetic encrypted source manifest admission and same-transaction persistence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "workspace" / "src"))

from medscale_workspace.binding import ObjectBinding  # noqa: E402
from medscale_workspace.fhir_batch import (  # noqa: E402
    SyntheticFhirBatchError,
    commit_synthetic_fhir_batch_atomic,
)
from medscale_workspace.identity import WorkspaceObjectType, synthetic_identity  # noqa: E402
from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret  # noqa: E402
from medscale_workspace.storage import WorkspaceStore  # noqa: E402

from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic  # noqa: E402

WORKSPACE_ID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
FIXTURE = ROOT / "examples" / "synthetic_fhir_bundle_preflight" / "fictional_bundle.json"


def test_original_uuid_manifest_is_encrypted_and_bound_to_source_digest(tmp_path: Path) -> None:
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    canonical = json.dumps(
        original, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    provider = InMemoryTestKeyProvider(new_root_secret())
    with WorkspaceStore.open(
        store_root=str(tmp_path),
        workspace_id=WORKSPACE_ID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    ) as store:
        receipt = ingest_synthetic_bundle_atomic(
            original,
            store,
            test_key_provider=provider,
            actor_id="fictional-actor",
            occurred_at="2026-11-04T04:00:00+03:00",
            synthetic_only=True,
        )
        assert receipt["source_content_sha256"] == digest
        assert receipt["encrypted_import_manifests_written"] == 1
        assert store.object_count() == 8
        identity = synthetic_identity(
            WORKSPACE_ID,
            WorkspaceObjectType.FHIR_IMPORT_MANIFEST,
            digest,
        )
        binding = ObjectBinding(
            WORKSPACE_ID,
            identity.object_id,
            WorkspaceObjectType.FHIR_IMPORT_MANIFEST,
            "1",
        )
        assert store.get_object(binding) == canonical
        assert canonical not in Path(store.store_path).read_bytes()
        assert b"urn:uuid:" not in Path(store.store_path).read_bytes()
    with WorkspaceStore.open(
        store_root=str(tmp_path),
        workspace_id=WORKSPACE_ID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    ) as reopened:
        assert reopened.get_object(binding) == canonical


def test_manifest_digest_mismatch_refuses_all_writes(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with WorkspaceStore.open(
        store_root=str(tmp_path),
        workspace_id=WORKSPACE_ID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    ) as store:
        with pytest.raises(SyntheticFhirBatchError, match="synthetic_source_manifest_refused"):
            commit_synthetic_fhir_batch_atomic(
                store=store,
                test_key_provider=provider,
                resources=({"resourceType": "Patient", "id": "fictional"},),
                source_content_sha256="a" * 64,
                source_bundle={"resourceType": "Bundle", "entry": []},
                actor_id="fictional-actor",
                occurred_at="2026-11-04T04:00:00+03:00",
                synthetic_only=True,
            )
        assert store.object_count() == 0


def test_manifest_identity_mismatch_refuses_all_writes(tmp_path: Path) -> None:
    source = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000001",
                "resource": {"resourceType": "Patient", "id": "fictional-one"},
            }
        ],
    }
    canonical = json.dumps(
        source, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    provider = InMemoryTestKeyProvider(new_root_secret())
    with WorkspaceStore.open(
        store_root=str(tmp_path),
        workspace_id=WORKSPACE_ID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    ) as store:
        with pytest.raises(SyntheticFhirBatchError, match="synthetic_source_manifest_refused"):
            commit_synthetic_fhir_batch_atomic(
                store=store,
                test_key_provider=provider,
                resources=({"resourceType": "Patient", "id": "fictional-other"},),
                source_content_sha256=digest,
                source_bundle=source,
                actor_id="fictional-actor",
                occurred_at="2026-11-04T04:00:00+03:00",
                synthetic_only=True,
            )
        assert store.object_count() == 0
