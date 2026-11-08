"""Direct public Workspace batch contract, independently of Core preflight.

This supplements the real Core -> encrypted Workspace integration tests.
All records are invented; in-memory test keys, no PHI or cloud activity.
"""

from __future__ import annotations

# mypy: disable-error-code="import-not-found"
# The Workspace package under apps/workspace is deliberately outside strict mypy's
# file set while Issue #464 item 1 is open; it is imported at runtime. Declaring
# the missing import here keeps that deferral explicit.
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "workspace" / "src"))

from medscale_workspace.audit import AuditTrail  # noqa: E402
from medscale_workspace.fhir_batch import (  # noqa: E402
    SyntheticFhirBatchError,
    commit_synthetic_fhir_batch_atomic,
)
from medscale_workspace.keyprovider import (  # noqa: E402
    InMemoryTestKeyProvider,
    new_root_secret,
)
from medscale_workspace.storage import WorkspaceStore  # noqa: E402

WORKSPACE = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
SHA = "a" * 64
TIME = "2026-11-04T04:30:00+03:00"


def _store(tmp_path: Path, provider: InMemoryTestKeyProvider) -> WorkspaceStore:
    return WorkspaceStore.open(
        store_root=str(tmp_path),
        workspace_id=WORKSPACE,
        key_provider=provider,
        application_version="0.1.0.dev1",
    )


def _items() -> tuple[dict[str, object], ...]:
    return (
        {
            "resourceType": "Observation",
            "id": "synthetic-observation-001",
            "status": "final",
            "code": {"text": "fictional test code"},
            "subject": {"reference": "Patient/synthetic-patient-001"},
            "encounter": {"reference": "Encounter/synthetic-encounter-001"},
        },
        {
            "resourceType": "Encounter",
            "id": "synthetic-encounter-001",
            "status": "finished",
            "class": {"code": "AMB"},
            "subject": {"reference": "Patient/synthetic-patient-001"},
        },
        {
            "resourceType": "Patient",
            "id": "synthetic-patient-001",
            "active": True,
            "name": [{"text": "Synthetic Fiction"}],
        },
    )


def _commit(
    store: WorkspaceStore,
    provider: InMemoryTestKeyProvider,
    resources: tuple[dict[str, object], ...],
    **changes: object,
) -> Any:
    params: dict[str, object] = {
        "store": store,
        "test_key_provider": provider,
        "resources": resources,
        "source_content_sha256": SHA,
        "actor_id": "fictional-test-actor",
        "occurred_at": TIME,
        "synthetic_only": True,
    }
    params.update(changes)
    return commit_synthetic_fhir_batch_atomic(**params)


def test_public_workspace_boundary_is_atomic_without_core_helper(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        receipt = _commit(store, provider, _items())
        assert receipt["resource_count"] == 3
        assert receipt["provenance_records_written"] == 3
        assert receipt["audit_events_written"] == 1
        assert store.object_count() == 7
        assert AuditTrail(store).verify().head_event_digest == receipt["audit_head_digest"]
        assert "synthetic-patient" not in json.dumps(receipt)


def test_reference_cannot_escape_to_existing_store_object(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        patient = _items()[2]
        _commit(store, provider, (patient,))
        before_count = store.object_count()
        before_head = AuditTrail(store).verify().head_event_digest
        # A Patient exists in this SAME workspace, but batch admission
        # requires Encounter's reference to be in this batch as well.
        encounter = _items()[1]
        with pytest.raises(SyntheticFhirBatchError, match="batch_reference_target_missing"):
            _commit(store, provider, (encounter,), source_content_sha256="b" * 64)
        assert store.object_count() == before_count == 3
        assert AuditTrail(store).verify().head_event_digest == before_head


def test_missing_target_rejected_in_standalone_batch(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        with pytest.raises(SyntheticFhirBatchError, match="batch_reference_target_missing"):
            _commit(store, provider, (_items()[0],))
        assert store.object_count() == 0


def test_duplicate_resource_identity_refused_before_write(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    patient = _items()[2]
    with _store(tmp_path, provider) as store:
        with pytest.raises(
            SyntheticFhirBatchError, match="duplicate_workspace_batch_resource_identity"
        ):
            _commit(store, provider, (patient, patient))
        assert store.object_count() == 0


@pytest.mark.parametrize(
    "data, digest, reason",
    [
        ((), SHA, "atomic_test_batch_out_of_range"),
        ((_items()[2],) * 17, SHA, "atomic_test_batch_out_of_range"),
        ((_items()[2],), "not-a-digest", "invalid_synthetic_source_digest"),
    ],
)
def test_public_batch_rejects_out_of_contract(
    data: tuple[dict[str, object], ...], digest: str, reason: str, tmp_path: Path
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        with pytest.raises(SyntheticFhirBatchError, match=reason):
            _commit(store, provider, data, source_content_sha256=digest)
        assert store.object_count() == 0


def test_reject_subclassed_test_provider_even_when_same_store_instance(tmp_path: Path) -> None:
    # The base is Any while apps/workspace is outside strict mypy (Issue #464).
    class UnapprovedTestProvider(InMemoryTestKeyProvider):  # type: ignore[misc]
        pass

    provider = UnapprovedTestProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        with pytest.raises(SyntheticFhirBatchError, match="in_memory_test_key_provider_required"):
            _commit(store, provider, (_items()[2],))
        assert store.object_count() == 0


def test_unadmitted_resource_structure_cannot_write(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    unexpected = {**_items()[2], "customOverride": "ignore me"}
    with _store(tmp_path, provider) as store:
        with pytest.raises(SyntheticFhirBatchError, match="workspace_atomic_prepare_refused"):
            _commit(store, provider, (unexpected,))
        assert store.object_count() == 0


def test_direct_public_workspace_batch_requires_explicit_synthetic_attestation(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        with pytest.raises(
            SyntheticFhirBatchError, match="explicit_synthetic_attestation_required"
        ):
            _commit(store, provider, (_items()[2],), synthetic_only=False)
        assert store.object_count() == 0
