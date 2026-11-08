"""Real, synthetic-only encrypted FHIR import catalog product acceptance.

No patient data, clinical authority, network, plain-text export or external
file input is permitted by the catalog. All test fixtures are fictional.
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

from medscale_workspace import fhir_r4 as fhir  # noqa: E402
from medscale_workspace.audit import (  # noqa: E402
    AuditEventType,
    AuditObjectRef,
    AuditTrail,
)
from medscale_workspace.binding import ObjectBinding  # noqa: E402
from medscale_workspace.identity import WorkspaceObjectType, synthetic_identity  # noqa: E402
from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret  # noqa: E402
from medscale_workspace.storage import WorkspaceStore  # noqa: E402

from medscale.fhirkit.workspace_catalog import (  # noqa: E402
    SyntheticWorkspaceCatalogError,
    list_synthetic_bundle_imports,
)
from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic  # noqa: E402
from medscale.fhirkit.workspace_readback import read_synthetic_bundle_in_memory  # noqa: E402

WORKSPACE = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
ACTOR = "fictional-catalog-owner"
TIME = "2026-11-04T04:00:00+03:00"
FIXTURE = ROOT / "examples" / "synthetic_fhir_bundle_preflight" / "fictional_bundle.json"
SENTINEL = "NEVER_RETURN_THIS_FAKE_PATIENT_NAME"


def _open(root: Path, provider: InMemoryTestKeyProvider) -> WorkspaceStore:
    return WorkspaceStore.open(
        store_root=str(root),
        workspace_id=WORKSPACE,
        key_provider=provider,
        application_version="0.1.0.dev1",
    )


def _one_patient(index: int, text: str = SENTINEL) -> dict[str, object]:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {"tag": [{"system": "urn:medorigin:fixture-classification", "code": "synthetic"}]},
        "entry": [
            {
                "fullUrl": f"urn:uuid:00000000-0000-4000-8000-{index:012d}",
                "resource": {
                    "resourceType": "Patient",
                    "id": f"fictional-catalog-patient-{index}",
                    "name": [{"text": text}],
                    "active": True,
                },
            }
        ],
    }


def _ingest(
    store: WorkspaceStore,
    provider: InMemoryTestKeyProvider,
    bundle: dict[str, Any],
    *,
    actor: str = ACTOR,
) -> dict[str, Any]:
    return ingest_synthetic_bundle_atomic(
        bundle,
        store,
        test_key_provider=provider,
        actor_id=actor,
        occurred_at=TIME,
        synthetic_only=True,
    )


def _catalog(
    store: WorkspaceStore,
    provider: InMemoryTestKeyProvider,
    head: str,
    *,
    actor: str = ACTOR,
    **kwargs: Any,
) -> dict[str, Any]:
    args: dict[str, Any] = {
        "test_key_provider": provider,
        "actor_id": actor,
        "expected_current_audit_head_digest": head,
        "synthetic_only": True,
        "allow_in_memory_listing": True,
    }
    args.update(kwargs)
    return list_synthetic_bundle_imports(store, **args)


def test_original_and_recent_imports_catalog_real_encrypted_reopen_and_selection(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    original["entry"][1]["resource"]["name"][0]["text"] = SENTINEL
    other = _one_patient(42)
    with _open(tmp_path, provider) as store:
        first = _ingest(store, provider, original)
        AuditTrail(store).append(
            event_type=AuditEventType.WORKSPACE_OPEN,
            actor_id="fictional-ui",
            occurred_at="2026-11-04T04:01:00+03:00",
        )
        second = _ingest(store, provider, other)
        assert store.object_count() == 13
    with _open(tmp_path, provider) as reopened:
        listing = _catalog(reopened, provider, second["audit_head_digest"])
        assert listing["schema"] == "medorigin-core-synthetic-import-catalog/v1"
        assert listing["status"] == "verified_synthetic_import_catalog"
        assert listing["import_count"] == 2
        assert listing["payload_included"] is False
        assert listing["filesystem_export_performed"] is False
        assert listing["clinical_use_authorized"] is False
        assert listing["full_fhir_r4_conformance_established"] is False
        assert listing["release_authorized"] is False
        assert listing["current_audit_head_digest"] == second["audit_head_digest"]
        assert listing["imports"] == [
            {
                "source_content_sha256": first["source_content_sha256"],
                "import_audit_event_digest": first["audit_head_digest"],
                "audit_sequence": 1,
                "resource_count": 3,
            },
            {
                "source_content_sha256": second["source_content_sha256"],
                "import_audit_event_digest": second["audit_head_digest"],
                "audit_sequence": 3,
                "resource_count": 1,
            },
        ]
        safe_text = json.dumps(listing, sort_keys=True)
        assert SENTINEL not in safe_text
        assert "urn:uuid:" not in safe_text
        for entry, expected in zip(listing["imports"], (original, other), strict=True):
            source = read_synthetic_bundle_in_memory(
                reopened,
                test_key_provider=provider,
                actor_id=ACTOR,
                source_content_sha256=entry["source_content_sha256"],
                expected_audit_head_digest=entry["import_audit_event_digest"],
                expected_current_audit_head_digest=listing["current_audit_head_digest"],
                synthetic_only=True,
                allow_in_memory_readback=True,
            )
            assert source["bundle"] == expected
        encrypted = Path(reopened.store_path).read_bytes()
        assert SENTINEL.encode() not in encrypted
        assert b"urn:uuid:" not in encrypted


def test_catalog_scope_to_actor_is_empty_not_an_authentication_claim(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _one_patient(11), actor="fictional-other")
        listing = _catalog(store, provider, receipt["audit_head_digest"])
        assert listing["import_count"] == 0
        assert listing["imports"] == []
        assert listing["clinical_use_authorized"] is False


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"synthetic_only": False}, "explicit_synthetic_attestation_required"),
        ({"allow_in_memory_listing": False}, "explicit_in_memory_listing_required"),
        ({"expected_current_audit_head_digest": "0" * 64}, "catalog_audit_head_anchor_mismatch"),
        ({"expected_current_audit_head_digest": "bad"}, "current_audit_anchor_refused"),
        ({"expected_current_audit_head_digest": ""}, "current_audit_anchor_refused"),
        ({"max_imports": 0}, "catalog_limit_refused"),
        ({"max_imports": 17}, "catalog_limit_refused"),
        ({"max_imports": True}, "catalog_limit_refused"),
        ({"max_imports": 1}, "catalog_limit_exceeded_no_partial_result"),
    ],
)
def test_catalog_refuses_invalid_permissions_anchors_and_silent_truncation(
    tmp_path: Path, overrides: dict[str, Any], reason: str
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        _ingest(store, provider, _one_patient(111))
        last = _ingest(store, provider, _one_patient(222))
        with pytest.raises(SyntheticWorkspaceCatalogError, match=reason):
            _catalog(store, provider, last["audit_head_digest"], **overrides)


def test_catalog_denies_mismatched_test_key_provider(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _one_patient(111))
        other = InMemoryTestKeyProvider(new_root_secret())
        with pytest.raises(SyntheticWorkspaceCatalogError, match="workspace_key_provider_mismatch"):
            _catalog(store, other, receipt["audit_head_digest"])


def test_catalog_denies_missing_original_encrypted_manifest(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _one_patient(111))
        manifest = synthetic_identity(
            WORKSPACE, WorkspaceObjectType.FHIR_IMPORT_MANIFEST, receipt["source_content_sha256"]
        )
        binding = ObjectBinding(
            WORKSPACE, manifest.object_id, WorkspaceObjectType.FHIR_IMPORT_MANIFEST, "1"
        )
        assert store.delete_object(binding)
        with pytest.raises(SyntheticWorkspaceCatalogError, match="catalog_integrity_refused"):
            _catalog(store, provider, receipt["audit_head_digest"])


def test_catalog_denies_post_import_reference_to_protected_patient(tmp_path: Path) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path, provider) as store:
        receipt = _ingest(store, provider, _one_patient(111))
        patient_id = fhir.resource_id_for(
            WORKSPACE, fhir.FhirResourceType.PATIENT, "fictional-catalog-patient-111", "1"
        )
        later = AuditTrail(store).append(
            event_type=AuditEventType.OBJECT_CREATE,
            actor_id=ACTOR,
            occurred_at=TIME,
            object_refs=(
                AuditObjectRef(
                    patient_id,
                    WorkspaceObjectType.FHIR_RESOURCE,
                    fhir.resource_binding(WORKSPACE, patient_id).object_revision,
                ),
            ),
        )
        assert later.event_digest != receipt["audit_head_digest"]
        with pytest.raises(SyntheticWorkspaceCatalogError, match="catalog_integrity_refused"):
            _catalog(store, provider, later.event_digest)
