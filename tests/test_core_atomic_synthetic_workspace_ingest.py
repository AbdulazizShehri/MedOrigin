"""Real encrypted synthetic WorkspaceStore + Core Bundle end-to-end tests.

No production protected root-key provider, patient data, EHR or network I/O.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_SRC = ROOT / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))

from medscale_workspace import fhir_r4 as fhir_mod  # noqa: E402
from medscale_workspace.audit import AuditTrail  # noqa: E402
from medscale_workspace.errors import KeyProviderUnavailableError  # noqa: E402
from medscale_workspace.keyprovider import (  # noqa: E402
    InMemoryTestKeyProvider,
    new_root_secret,
    resolve_platform_key_provider,
)
from medscale_workspace.provenance import read_provenance, verify_provenance  # noqa: E402
from medscale_workspace.storage import WorkspaceStore  # noqa: E402

from medscale.fhirkit.workspace_ingest import (  # noqa: E402
    SyntheticWorkspaceImportError,
    ingest_synthetic_bundle_atomic,
)

WORKSPACE_ID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
ACTOR = "synthetic-import-test"
OCCURRED = "2026-11-04T04:00:00+03:00"
PATIENT_ID = "synthetic-patient-001"
OBS_ID = "synthetic-observation-001"
ENC_ID = "synthetic-encounter-001"
FIXTURE = ROOT / "examples" / "synthetic_fhir_bundle_preflight" / "fictional_bundle.json"


def _bundle() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _store(tmp_path: Path, provider: InMemoryTestKeyProvider) -> WorkspaceStore:
    return WorkspaceStore.open(
        store_root=str(tmp_path),
        workspace_id=WORKSPACE_ID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    )


def _ingest(payload: dict, store: WorkspaceStore, provider, **kw):
    return ingest_synthetic_bundle_atomic(
        payload,
        store,
        test_key_provider=provider,
        actor_id=ACTOR,
        occurred_at=OCCURRED,
        synthetic_only=True,
        **kw,
    )


def test_true_atomic_encrypted_bundle_ingest_reopen_and_audit(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        assert store.object_count() == 0
        receipt = _ingest(_bundle(), store, provider)
        assert receipt["status"] == "synthetic_test_store_committed"
        assert receipt["resource_count"] == 3
        assert receipt["provenance_records_written"] == 3
        assert receipt["audit_events_written"] == 1
        assert receipt["payload_included"] is False
        assert receipt["production_key_provider_used"] is False
        assert receipt["clinical_use_authorized"] is False
        assert receipt["full_fhir_r4_conformance_established"] is False
        assert "Synthetic Example Only" not in json.dumps(receipt)
        assert PATIENT_ID not in json.dumps(receipt)
        # Three encrypted resource records, three encrypted provenance
        # records, one encrypted audit event, all in one transaction.
        assert store.object_count() == 8
        trail = AuditTrail(store)
        verified = trail.verify()
        assert verified.events_verified == 1
        assert verified.head_event_digest == receipt["audit_head_digest"]
        assert len(trail.events()[0].object_refs) == 3
        for kind, fhir_id in (
            (fhir_mod.FhirResourceType.PATIENT, PATIENT_ID),
            (fhir_mod.FhirResourceType.ENCOUNTER, ENC_ID),
            (fhir_mod.FhirResourceType.OBSERVATION, OBS_ID),
        ):
            identity = fhir_mod.resource_id_for(WORKSPACE_ID, kind, fhir_id, "1")
            resource = fhir_mod.read_resource(store, identity)
            assert resource.fhir_id == fhir_id
            binding = fhir_mod.resource_binding(WORKSPACE_ID, identity)
            stored_provenance = read_provenance(store, binding)
            assert stored_provenance.binding == binding
            assert verify_provenance(store, binding) == stored_provenance
        # SQLite stores ciphertext, not the original fictional name or ID.
        binary = Path(store.store_path).read_bytes()
        assert b"Synthetic Example Only" not in binary
        assert PATIENT_ID.encode("ascii") not in binary
    with _store(tmp_path, provider) as reopened:
        assert reopened.object_count() == 8
        assert (
            AuditTrail(reopened)
            .verify(expected_head_event_digest=receipt["audit_head_digest"])
            .events_verified
            == 1
        )
        identity = fhir_mod.resource_id_for(
            WORKSPACE_ID, fhir_mod.FhirResourceType.OBSERVATION, OBS_ID, "1"
        )
        observation = fhir_mod.read_resource(reopened, identity)
        assert observation.patient_id == PATIENT_ID


def test_prepare_failure_in_last_resource_leaves_zero_objects(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    payload = _bundle()
    # Core relationship preflight permits source-owned text, but Workspace
    # bounded field validator must refuse a string over its 1024-char cap.
    payload["entry"][0]["resource"]["valueString"] = "F" * 1025
    with _store(tmp_path, provider) as store:
        with pytest.raises(SyntheticWorkspaceImportError, match="workspace_atomic_prepare_refused"):
            _ingest(payload, store, provider)
        assert store.object_count() == 0
        assert AuditTrail(store).events() == ()


def test_missing_local_reference_never_starts_write(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    payload = _bundle()
    payload["entry"][0]["resource"]["subject"] = {
        "reference": "urn:uuid:00000000-0000-4000-8000-000000000099"
    }
    with _store(tmp_path, provider) as store:
        with pytest.raises(
            SyntheticWorkspaceImportError, match="synthetic_bundle_preflight_refused"
        ):
            _ingest(payload, store, provider)
        assert store.object_count() == 0
        assert AuditTrail(store).events() == ()


def test_replaying_batch_atomic_conflict_leaves_snapshot_unchanged(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        initial = _ingest(_bundle(), store, provider)
        with pytest.raises(SyntheticWorkspaceImportError, match="workspace_atomic_commit_refused"):
            _ingest(_bundle(), store, provider)
        assert store.object_count() == 8
        assert AuditTrail(store).verify().head_event_digest == initial["audit_head_digest"]


def test_explicit_synthetic_attestation_and_exact_test_provider_required(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    other = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        with pytest.raises(
            SyntheticWorkspaceImportError, match="explicit_synthetic_attestation_required"
        ):
            ingest_synthetic_bundle_atomic(
                _bundle(),
                store,
                test_key_provider=provider,
                actor_id=ACTOR,
                occurred_at=OCCURRED,
            )
        with pytest.raises(
            SyntheticWorkspaceImportError, match="workspace_test_key_provider_mismatch"
        ):
            _ingest(_bundle(), store, other)
        with pytest.raises(
            SyntheticWorkspaceImportError, match="in_memory_test_key_provider_required"
        ):
            _ingest(_bundle(), store, resolve_platform_key_provider())
        assert store.object_count() == 0


def test_production_platform_key_resolver_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(KeyProviderUnavailableError):
        _store(tmp_path, resolve_platform_key_provider())  # type: ignore[arg-type]
    assert not list(tmp_path.rglob("*.db"))


def test_bad_resource_type_without_exposure_refused(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    payload = _bundle()
    payload["entry"][1]["resource"]["resourceType"] = "DiagnosticReport"
    with _store(tmp_path, provider) as store:
        with pytest.raises(
            SyntheticWorkspaceImportError, match="synthetic_bundle_preflight_refused"
        ):
            _ingest(payload, store, provider)
        assert store.object_count() == 0


def test_resource_reference_target_type_checks_before_commit(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    payload = _bundle()
    payload["entry"][0]["resource"]["subject"] = {
        "reference": "urn:uuid:00000000-0000-4000-8000-000000000003"
    }
    with _store(tmp_path, provider) as store:
        with pytest.raises(
            SyntheticWorkspaceImportError, match="synthetic_bundle_preflight_refused"
        ):
            _ingest(payload, store, provider)
        assert store.object_count() == 0


def test_store_only_accepts_workspace_instance(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with pytest.raises(SyntheticWorkspaceImportError, match="workspace_store_required"):
        _ingest(_bundle(), object(), provider)


def test_fault_during_third_encrypted_write_rolls_back_everything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        original_insert = store._insert_object
        calls = 0

        def simulated_insert(binding, envelope):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("synthetic injected failure after two encrypted object writes")
            original_insert(binding, envelope)

        with monkeypatch.context() as patch:
            patch.setattr(store, "_insert_object", simulated_insert)
            with pytest.raises(
                SyntheticWorkspaceImportError, match="workspace_atomic_commit_refused"
            ):
                _ingest(_bundle(), store, provider)
        assert calls == 3
        assert store.object_count() == 0
        assert AuditTrail(store).events() == ()
        store.integrity_check()

    with _store(tmp_path, provider) as reopened:
        assert reopened.object_count() == 0
        assert AuditTrail(reopened).events() == ()


def test_existing_audit_chain_remains_contiguous_after_atomic_import(tmp_path: Path) -> None:
    from medscale_workspace.audit import AuditEventType

    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        trail = AuditTrail(store)
        first = trail.append(
            event_type=AuditEventType.WORKSPACE_OPEN,
            actor_id=ACTOR,
            occurred_at=OCCURRED,
        )
        receipt = _ingest(_bundle(), store, provider)
        assert store.object_count() == 9
        events = trail.events()
        assert len(events) == 2
        assert events[0] == first
        assert events[1].previous_event_digest == first.event_digest
        assert events[1].event_digest == receipt["audit_head_digest"]
        assert trail.verify().events_verified == 2


def test_wrong_test_secret_cannot_reopen_encrypted_store(tmp_path: Path) -> None:
    from medscale_workspace.errors import WorkspaceStoreError

    provider = InMemoryTestKeyProvider(new_root_secret())
    with _store(tmp_path, provider) as store:
        _ingest(_bundle(), store, provider)
    with pytest.raises(WorkspaceStoreError):
        _store(tmp_path, InMemoryTestKeyProvider(new_root_secret()))
    with _store(tmp_path, provider) as reopened:
        assert reopened.object_count() == 8


def test_policy_failures_do_not_even_read_unsupported_store(tmp_path: Path) -> None:
    # An untrusted caller cannot activate this in a conventional Core
    # installation or without passing an explicit in-memory test provider.
    from medscale_workspace.keyprovider import UnavailablePlatformKeyProvider

    with pytest.raises(SyntheticWorkspaceImportError, match="workspace_store_required"):
        ingest_synthetic_bundle_atomic(
            _bundle(),
            None,
            test_key_provider=UnavailablePlatformKeyProvider(),
            actor_id=ACTOR,
            occurred_at=OCCURRED,
            synthetic_only=True,
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "unexpected",
    [float("nan"), float("inf"), float("-inf"), object()],
)
def test_programmatic_non_json_values_never_reach_encrypted_store(
    tmp_path: Path, unexpected: object
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    payload = _bundle()
    payload["entry"][0]["resource"]["valueString"] = unexpected
    with _store(tmp_path, provider) as store:
        with pytest.raises(
            SyntheticWorkspaceImportError, match="synthetic_bundle_json_snapshot_refused"
        ):
            _ingest(payload, store, provider)
        assert store.object_count() == 0
        assert AuditTrail(store).events() == ()


def test_source_dict_mutation_after_preflight_does_not_change_committed_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from medscale.fhirkit import workspace_ingest as import_module

    provider = InMemoryTestKeyProvider(new_root_secret())
    payload = _bundle()
    original_inspect = import_module.inspect_synthetic_bundle
    original_sha = original_inspect(payload)["source_content_sha256"]

    def mutate_caller_after_preflight(snapshot):
        inspected = original_inspect(snapshot)
        payload["entry"][1]["resource"]["id"] = "synthetic-poisoned-after-preflight"
        return inspected

    monkeypatch.setattr(import_module, "inspect_synthetic_bundle", mutate_caller_after_preflight)
    with _store(tmp_path, provider) as store:
        receipt = _ingest(payload, store, provider)
        assert receipt["source_content_sha256"] == original_sha
        identity = fhir_mod.resource_id_for(
            WORKSPACE_ID, fhir_mod.FhirResourceType.PATIENT, PATIENT_ID, "1"
        )
        assert fhir_mod.read_resource(store, identity).fhir_id == PATIENT_ID
        assert store.object_count() == 8
        assert "poisoned" not in json.dumps(receipt)
