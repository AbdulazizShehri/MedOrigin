"""Real encrypted Workspace synthetic R4 structural report: source, audit, and readback.

The official-validator contract is faked *only* for fast source tests.
A separate opt-in test uses the exact SHA-pinned published HL7 R4 ZIP.
All FHIR data is fictional and no plaintext report export is permitted.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "workspace" / "src"))

from medscale_workspace.audit import AuditTrail  # noqa: E402
from medscale_workspace.binding import ObjectBinding  # noqa: E402
from medscale_workspace.fhir_structural_receipt import (  # noqa: E402
    SyntheticStructuralReceiptError,
    commit_verified_synthetic_structural_outcome,
)
from medscale_workspace.identity import (  # noqa: E402
    WorkspaceObjectType,
    synthetic_identity,
)
from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret  # noqa: E402
from medscale_workspace.storage import WorkspaceStore  # noqa: E402

from medscale.fhirkit import r4_schema  # noqa: E402
from medscale.fhirkit.workspace_demo import _fictional_bundle  # noqa: E402
from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic  # noqa: E402
from medscale.fhirkit.workspace_structural import (  # noqa: E402
    SyntheticStructuralStoreError,
    read_imported_synthetic_structural_result,
    validate_and_store_imported_synthetic_bundle_structure,
)

WID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
ACTOR = "fictional-validator-owner"
TIME = "2026-11-04T04:00:00+03:00"
LATER = "2026-11-04T04:03:00+03:00"
SECRET = "DO_NOT_SHOW_THIS_FICTIONAL_IDENTIFIER"


def _open(root: Path, provider: InMemoryTestKeyProvider) -> WorkspaceStore:
    root.mkdir(parents=True, exist_ok=True)
    return WorkspaceStore.open(
        store_root=str(root),
        workspace_id=WID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    )


def _source() -> dict[str, object]:
    return _fictional_bundle()


def _import(store, provider):
    return ingest_synthetic_bundle_atomic(
        _source(),
        store,
        test_key_provider=provider,
        actor_id=ACTOR,
        occurred_at=TIME,
        synthetic_only=True,
    )


def _report(store, provider, receipt, archive, **kwargs):
    args = {
        "store": store,
        "test_key_provider": provider,
        "source_content_sha256": receipt["source_content_sha256"],
        "import_audit_event_digest": receipt["audit_head_digest"],
        "expected_current_audit_head_digest": receipt["audit_head_digest"],
        "official_r4_schema_archive": archive,
        "actor_id": ACTOR,
        "occurred_at": LATER,
        "synthetic_only": True,
        "allow_encrypted_receipt_write": True,
    }
    args.update(kwargs)
    return validate_and_store_imported_synthetic_bundle_structure(**args)


def _read(store, provider, imported, saved, **kwargs):
    args = {
        "store": store,
        "test_key_provider": provider,
        "source_content_sha256": imported["source_content_sha256"],
        "import_audit_event_digest": imported["audit_head_digest"],
        "expected_current_audit_head_digest": saved["audit_head_digest"],
        "expected_receipt_sha256": saved["receipt_sha256"],
        "actor_id": ACTOR,
        "synthetic_only": True,
        "allow_in_memory_readback": True,
    }
    args.update(kwargs)
    return read_imported_synthetic_structural_result(**args)


def _fake_official_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, invalid=False):
    schema = {
        "$schema": r4_schema.OFFICIAL_R4_DRAFT,
        "id": r4_schema.OFFICIAL_R4_SCHEMA_ID,
        "definitions": {
            "Bundle": {
                "type": "object",
                "required": ["resourceType"],
                "properties": {
                    "resourceType": {"const": "IntentionallyImpossible"}
                    if invalid
                    else {"const": "Bundle"}
                },
            }
        },
        "$ref": "#/definitions/Bundle",
    }
    blob = json.dumps(schema).encode("utf-8")
    path = tmp_path / "synthetic-only-r4.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(r4_schema.OFFICIAL_R4_SCHEMA_MEMBER, blob)
    monkeypatch.setattr(
        r4_schema, "OFFICIAL_R4_SCHEMA_ZIP_SHA256", hashlib.sha256(path.read_bytes()).hexdigest()
    )
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_BYTES", len(blob))
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_DEFINITIONS", 1)
    monkeypatch.setattr(r4_schema, "version", lambda package: r4_schema.PINNED_JSONSCHEMA_VERSION)
    return path


@pytest.mark.parametrize("invalid", [False, True])
def test_actual_encrypted_import_source_verified_r4_outcome_atomic_and_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: bool
) -> None:
    archive = _fake_official_schema(tmp_path, monkeypatch, invalid=invalid)
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "workspace", provider) as store:
        imported = _import(store, provider)
        assert store.object_count() == 8
        receipt = _report(store, provider, imported, archive)
        assert store.object_count() == 11
        assert receipt["encrypted_objects_written"] == 3
        assert receipt["outcome_payload_included"] is False
        assert receipt["structural_status"] == ("invalid" if invalid else "not_validated")
        assert receipt["fhir_conformance_validated"] is False
        assert receipt["clinical_use_authorized"] is False
        assert receipt["release_authorized"] is False
        assert (
            AuditTrail(store)
            .verify(expected_head_event_digest=receipt["audit_head_digest"])
            .events_verified
            == 2
        )
        raw_db = Path(store.store_path).read_bytes()
        assert b"OperationOutcome" not in raw_db
        assert b"FHIR R4 JSON Schema" not in raw_db
        assert b"urn:uuid" not in raw_db
    with _open(tmp_path / "workspace", provider) as reopened:
        recovered = _read(reopened, provider, imported, receipt)
        assert recovered["structural_status"] == receipt["structural_status"]
        assert recovered["source_content_sha256"] == imported["source_content_sha256"]
        assert recovered["receipt_sha256"] == receipt["receipt_sha256"]
        assert recovered["outcome"]["resourceType"] == "OperationOutcome"
        severities = [item["severity"] for item in recovered["outcome"]["issue"]]
        assert severities == (["error", "warning"] if invalid else ["warning"])
        assert SECRET not in json.dumps(recovered)
        assert recovered["fhir_conformance_validated"] is False


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"synthetic_only": False}, "explicit_synthetic_attestation_required"),
        ({"allow_encrypted_receipt_write": False}, "explicit_encrypted_receipt_write_required"),
        ({"source_content_sha256": "a" * 64}, "encrypted_source_import_verification_refused"),
        ({"import_audit_event_digest": "b" * 64}, "encrypted_source_import_verification_refused"),
        (
            {"expected_current_audit_head_digest": "c" * 64},
            "encrypted_source_import_verification_refused",
        ),
        ({"actor_id": "fictional-unknown"}, "encrypted_source_import_verification_refused"),
        (
            {"official_r4_schema_archive": Path("not-a-real-schema.zip")},
            "official_r4_structural_check_unavailable",
        ),
    ],
)
def test_bad_attestations_and_unapproved_schema_never_create_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, overrides: dict, reason: str
) -> None:
    archive = _fake_official_schema(tmp_path, monkeypatch)
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "workspace", provider) as store:
        imported = _import(store, provider)
        with pytest.raises(SyntheticStructuralStoreError, match=reason):
            _report(store, provider, imported, archive, **overrides)
        assert store.object_count() == 8
        assert (
            AuditTrail(store)
            .verify(expected_head_event_digest=imported["audit_head_digest"])
            .events_verified
            == 1
        )


def test_repeated_commit_is_immutable_and_keeps_existing_valid_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _fake_official_schema(tmp_path, monkeypatch)
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "workspace", provider) as store:
        imported = _import(store, provider)
        receipt = _report(store, provider, imported, archive)
        with pytest.raises(
            SyntheticStructuralStoreError, match="encrypted_structural_receipt_refused"
        ):
            _report(
                store,
                provider,
                imported,
                archive,
                expected_current_audit_head_digest=receipt["audit_head_digest"],
            )
        assert store.object_count() == 11
        assert (
            _read(store, provider, imported, receipt)["outcome"]["resourceType"]
            == "OperationOutcome"
        )


def test_wrong_sha_wrong_head_and_wrong_test_key_refuse_stored_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _fake_official_schema(tmp_path, monkeypatch)
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "workspace", provider) as store:
        imported = _import(store, provider)
        receipt = _report(store, provider, imported, archive)
        for field, value in (
            ("expected_receipt_sha256", "0" * 64),
            ("expected_current_audit_head_digest", imported["audit_head_digest"]),
            ("test_key_provider", InMemoryTestKeyProvider(new_root_secret())),
        ):
            with pytest.raises(
                SyntheticStructuralStoreError, match="encrypted_structural_receipt_read_refused"
            ):
                _read(store, provider, imported, receipt, **{field: value})
        assert store.object_count() == 11


def test_forged_outcome_extra_field_or_false_valid_rejected_before_write(tmp_path: Path):
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "workspace", provider) as store:
        imported = _import(store, provider)
        warning = {
            "severity": "warning",
            "code": "informational",
            "details": {
                "text": (
                    "Structural-only JSON Schema result; not FHIR R4 conformance. "
                    "Profiles, terminology, invariants, cross-references and clinical "
                    "safety remain unverified."
                )
            },
        }
        for shape, status in (
            (
                {"resourceType": "OperationOutcome", "issue": [warning], "patientName": SECRET},
                "not_validated",
            ),
            ({"resourceType": "OperationOutcome", "issue": [warning]}, "valid"),
            (
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {"severity": "error", "code": "structure", "details": {"text": SECRET}},
                        warning,
                    ],
                },
                "invalid",
            ),
        ):
            with pytest.raises(SyntheticStructuralReceiptError):
                commit_verified_synthetic_structural_outcome(
                    store=store,
                    test_key_provider=provider,
                    source_content_sha256=imported["source_content_sha256"],
                    import_audit_event_digest=imported["audit_head_digest"],
                    expected_current_audit_head_digest=imported["audit_head_digest"],
                    outcome=shape,
                    structural_status=status,
                    actor_id=ACTOR,
                    occurred_at=LATER,
                    synthetic_only=True,
                    allow_encrypted_receipt_write=True,
                )
            assert store.object_count() == 8


def test_missing_provenance_record_denies_recovered_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _fake_official_schema(tmp_path, monkeypatch)
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "workspace", provider) as store:
        imported = _import(store, provider)
        receipt = _report(store, provider, imported, archive)
        identity = synthetic_identity(
            WID,
            WorkspaceObjectType.FHIR_STRUCTURAL_OUTCOME,
            imported["source_content_sha256"] + ":" + imported["audit_head_digest"],
        )
        from medscale_workspace.provenance import provenance_binding_for

        binding = ObjectBinding(
            WID, identity.object_id, WorkspaceObjectType.FHIR_STRUCTURAL_OUTCOME, "1"
        )
        assert store.delete_object(provenance_binding_for(binding))
        with pytest.raises(
            SyntheticStructuralStoreError, match="encrypted_structural_receipt_read_refused"
        ):
            _read(store, provider, imported, receipt)


def test_real_official_archive_opt_in_proves_stored_structural_truth(tmp_path: Path) -> None:
    archive_path = os.environ.get("MEDORIGIN_OFFICIAL_R4_SCHEMA_ZIP")
    if not archive_path:
        pytest.skip("exact official HL7 R4 archive not supplied to source tests")
    archive = Path(archive_path)
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "workspace", provider) as store:
        imported = _import(store, provider)
        receipt = _report(store, provider, imported, archive)
        assert receipt["structural_status"] in ("invalid", "not_validated")
    with _open(tmp_path / "workspace", provider) as reopened:
        result = _read(reopened, provider, imported, receipt)
        assert result["outcome"]["resourceType"] == "OperationOutcome"
        assert result["outcome"]["issue"][-1]["severity"] == "warning"
        assert result["fhir_conformance_validated"] is False


def test_public_core_ephemeral_encrypted_structural_cli_returns_only_redacted_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from medscale.cli import main as cli_main

    archive = _fake_official_schema(tmp_path, monkeypatch)
    assert (
        cli_main(
            [
                "fhir",
                "encrypted-structural-demo",
                "--synthetic-only",
                "--ephemeral-demo",
                "--offline-r4-schema",
                str(archive),
            ]
        )
        == 0
    )
    stdout = capsys.readouterr()
    assert stdout.err == ""
    report = json.loads(stdout.out)
    assert report["schema"] == "medorigin-synthetic-encrypted-r4-structural-demo/v1"
    assert report["status"] == "SYNTHETIC_ENCRYPTED_R4_STRUCTURAL_RECEIPT_PASS"
    assert report["structural_status"] == "not_validated"
    assert report["encrypted_objects"] == 11
    assert report["audit_events_verified"] == 2
    assert report["outcome_issues"] == 1
    assert report["verified_reopen"] is True
    assert report["ephemeral_store_removed"] is True
    assert report["payload_included"] is False
    assert report["fhir_conformance_validated"] is False
    assert report["clinical_use_authorized"] is False
    assert report["release_authorized"] is False
    assert "Fictional Example Only" not in stdout.out
    assert "urn:uuid:" not in stdout.out
    assert str(archive) not in stdout.out


@pytest.mark.parametrize(
    "tokens",
    [
        [],
        ["--synthetic-only"],
        ["--synthetic-only", "--ephemeral-demo"],
        ["--synthetic-only", "--offline-r4-schema", SECRET],
        ["--synthetic-only", "--ephemeral-demo", "--offline-r4-schema"],
        ["--synthetic-only", "--ephemeral-demo", "--offline-r4-schema", "--malicious"],
        ["--synthetic-only", "--ephemeral-demo", "--offline-r4-schema", SECRET, SECRET],
        ["--synthetic-only", "--synthetic-only", "--offline-r4-schema", SECRET],
    ],
)
def test_public_cli_refuses_unsafe_flags_without_echo(
    capsys: pytest.CaptureFixture[str], tokens: list[str]
) -> None:
    from medscale.cli import main as cli_main

    assert cli_main(["fhir", "encrypted-structural-demo", *tokens]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert SECRET not in output.err
    assert "exact_synthetic_demo_schema_flags_required" in output.err


def test_public_cli_unqualified_zip_never_claims_demo_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from medscale.cli import main as cli_main

    assert (
        cli_main(
            [
                "fhir",
                "encrypted-structural-demo",
                "--synthetic-only",
                "--ephemeral-demo",
                "--offline-r4-schema",
                str(tmp_path / SECRET),
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert SECRET not in output.err
    assert "synthetic_structural_receipt_blocked" in output.err


def test_public_cli_help_never_runs_a_source_import(capsys: pytest.CaptureFixture[str]) -> None:
    from medscale.cli import main as cli_main

    assert cli_main(["fhir", "encrypted-structural-demo", "--help"]) == 0
    output = capsys.readouterr()
    assert "NOT full FHIR/clinical conformance" in output.out
    assert output.err == ""


def test_later_benign_event_allowed_but_later_receipt_touch_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from medscale_workspace.audit import AuditEventType, AuditObjectRef

    archive = _fake_official_schema(tmp_path, monkeypatch)
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "workspace", provider) as store:
        imported = _import(store, provider)
        receipt = _report(store, provider, imported, archive)
        safe = AuditTrail(store).append(
            event_type=AuditEventType.WORKSPACE_OPEN,
            actor_id=ACTOR,
            occurred_at="2026-11-04T04:04:00+03:00",
        )
        recovered = _read(
            store,
            provider,
            imported,
            receipt,
            expected_current_audit_head_digest=safe.event_digest,
        )
        assert recovered["structural_status"] == "not_validated"
        identity = synthetic_identity(
            WID,
            WorkspaceObjectType.FHIR_STRUCTURAL_OUTCOME,
            imported["source_content_sha256"] + ":" + imported["audit_head_digest"],
        )
        changed = AuditTrail(store).append(
            event_type=AuditEventType.OBJECT_CREATE,
            actor_id=ACTOR,
            occurred_at="2026-11-04T04:05:00+03:00",
            object_refs=(
                AuditObjectRef(
                    object_id=identity.object_id,
                    object_type=WorkspaceObjectType.FHIR_STRUCTURAL_OUTCOME,
                    object_revision="1",
                ),
            ),
        )
        with pytest.raises(
            SyntheticStructuralStoreError, match="encrypted_structural_receipt_read_refused"
        ):
            _read(
                store,
                provider,
                imported,
                receipt,
                expected_current_audit_head_digest=changed.event_digest,
            )
