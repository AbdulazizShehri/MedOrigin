"""Strict optional official R4 STRUCTURAL gate before encrypted synthetic files.

The unit double below exercises facade contracts only; opt-in test with
genuine pinned HL7 ZIP performs actual offline JSON Schema validation.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit.r4_outcome import _WARNING
from medscale.fhirkit.r4_schema import OFFICIAL_R4_SCHEMA_ZIP_SHA256
from medscale.fhirkit.workspace_demo import _fictional_bundle
from medscale.fhirkit.workspace_file_batch_demo import (
    SyntheticFileImportDemoError,
    _freeze_and_preflight,
    run_fictional_file_batch_encrypted_demo,
)
from medscale.fhirkit.workspace_multi_timeline_demo import _second_fictional_timeline_bundle

_SECRET = "INVENTED_PATIENT_NAME_DO_NOT_LEAK"


def _two() -> list[dict[str, Any]]:
    first: dict[str, Any] = _fictional_bundle()
    first["entry"][1]["resource"]["name"][0]["text"] = _SECRET
    second: dict[str, Any] = _second_fictional_timeline_bundle()
    second["entry"][1]["resource"]["name"][0]["text"] = _SECRET + "_SECOND"
    return [first, second]


def _source_files(tmp_path: Path) -> list[Path]:
    output: list[Path] = []
    for n, bundle in enumerate(_two(), 1):
        name = tmp_path / f"{_SECRET}-{n}.json"
        name.write_text(json.dumps(bundle), encoding="utf-8")
        output.append(name)
    return output


def _qualified_fake_batch(
    sources: list[dict[str, Any]], *_args: object, **_kwargs: object
) -> dict[str, Any]:
    """Explicit CONTRACT DOUBLE, never proof of an actual schema check."""
    _, preflights = _freeze_and_preflight(sources)
    return {
        "schema": "medorigin-core-synthetic-fhir-batch-dual-assessment/v1",
        "status": "SYNTHETIC_BATCH_PARTIAL_R4_PRECHECK_ONLY",
        "document_count": len(preflights),
        "total_resource_count": sum(p["resource_count"] for p in preflights),
        "structural_not_validated_count": len(preflights),
        "structural_invalid_count": 0,
        "documents": [
            {
                "document_ordinal": i,
                "source_content_sha256": p["source_content_sha256"],
                "resource_count": p["resource_count"],
                "resource_counts": {"Patient": 1, "Encounter": 1, "Observation": 1},
                "local_references_checked": 3,
                "relationship_status": "local_relationship_preflight_only",
                "r4_structural_status": "not_validated",
                "r4_operation_outcome": {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "warning",
                            "code": "informational",
                            "details": {"text": _WARNING},
                        }
                    ],
                },
            }
            for i, p in enumerate(preflights, 1)
        ],
        "official_r4_archive_sha256": OFFICIAL_R4_SCHEMA_ZIP_SHA256,
        "source_filenames_included": False,
        "resource_payload_included": False,
        "result_persisted": False,
        "network_access_performed": False,
        "cross_bundle_patient_join_performed": False,
        "fhir_r4_conformance_validated": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }


def test_contract_double_proves_optional_wiring_before_encrypted_reopen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import medscale.fhirkit.workspace_file_r4_gate as gate

    monkeypatch.setattr(gate, "assess_synthetic_bundle_batch_offline", _qualified_fake_batch)
    paths = _source_files(tmp_path)
    args = [
        "fhir",
        "file-batch-encrypted-demo",
        "--synthetic-only",
        "--ephemeral-demo",
        "--offline-r4-schema",
        str(tmp_path / "stub-not-a-real-zip"),
        *[str(path) for path in paths],
    ]
    assert public_cli(args) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["verified_audit_events"] == 2
    assert report["ephemeral_store_removed"] is True
    assert report["import_count"] == 2
    assert report["official_r4_structural_gate"] == {
        "schema": "medorigin-core-fictional-file-official-r4-structural-gate/v1",
        "status": "OFFICIAL_R4_JSON_SCHEMA_STRUCTURE_ONLY_NOT_VALIDATED",
        "official_r4_archive_sha256": OFFICIAL_R4_SCHEMA_ZIP_SHA256,
        "source_count": 2,
        "structural_not_validated_count": 2,
        "structural_invalid_count": 0,
        "fhir_r4_conformance_validated": False,
        "terminology_profiles_invariants_verified": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }
    assert _SECRET not in captured.out + captured.err
    assert all(str(p) not in captured.out + captured.err for p in paths)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x.update({"structural_invalid_count": 1}),
        lambda x: x["documents"][1].update({"r4_structural_status": "valid"}),
        lambda x: x["documents"][1].update({"source_content_sha256": "0" * 64}),
        lambda x: x["documents"][0].update({"patient_name": _SECRET}),
        lambda x: x["documents"][1]["r4_operation_outcome"]["issue"][0]["details"].update(
            {"text": _SECRET}
        ),
        lambda x: x["documents"].reverse(),
        lambda x: x.update({"unapproved_payload": _SECRET}),
        lambda x: x.update({"fhir_r4_conformance_validated": True}),
        lambda x: x.update({"document_count": 3}),
    ],
)
def test_forged_downstream_report_blocks_all_storage_before_allocation(
    monkeypatch: pytest.MonkeyPatch, mutation: Callable[[dict[str, Any]], object]
) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as importer
    import medscale.fhirkit.workspace_file_r4_gate as gate

    def poisoned(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = _qualified_fake_batch(*args, **kwargs)
        mutation(result)
        return result

    def forbid_storage(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("MUST refuse before allocating any temporary Workspace")

    monkeypatch.setattr(gate, "assess_synthetic_bundle_batch_offline", poisoned)
    monkeypatch.setattr(importer, "TemporaryDirectory", forbid_storage)
    with pytest.raises(
        SyntheticFileImportDemoError, match="fictional_import_official_r4_structural_gate_refused"
    ) as error:
        run_fictional_file_batch_encrypted_demo(
            _two(),
            synthetic_only=True,
            ephemeral_demo=True,
            offline_r4_schema=Path("invented-untrusted-zip"),
        )
    assert _SECRET not in str(error.value)


def test_missing_exact_archive_refuses_before_workspace_allocation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as importer

    def forbid_storage(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("MUST refuse before allocating")

    monkeypatch.setattr(importer, "TemporaryDirectory", forbid_storage)
    with pytest.raises(SyntheticFileImportDemoError, match="official_r4_structural_gate_refused"):
        run_fictional_file_batch_encrypted_demo(
            _two(),
            synthetic_only=True,
            ephemeral_demo=True,
            offline_r4_schema=tmp_path / f"{_SECRET}.zip",
        )


def test_wrong_archive_even_if_it_is_zip_refuses_before_storage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import zipfile

    import medscale.fhirkit.workspace_file_batch_demo as importer

    archive = tmp_path / f"{_SECRET}.zip"
    with zipfile.ZipFile(archive, "w") as members:
        members.writestr("fhir.schema.json", json.dumps({"definitions": {}}))

    def forbid_storage(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("MUST refuse before allocating")

    monkeypatch.setattr(importer, "TemporaryDirectory", forbid_storage)
    with pytest.raises(SyntheticFileImportDemoError, match="official_r4_structural_gate_refused"):
        run_fictional_file_batch_encrypted_demo(
            _two(),
            synthetic_only=True,
            ephemeral_demo=True,
            offline_r4_schema=archive,
        )


@pytest.mark.parametrize(
    "flags",
    [
        ["--offline-r4-schema"],
        ["--offline-r4-schema", "--unknown"],
        ["--offline-r4-schema", "first.zip", "--offline-r4-schema", "again.zip"],
        ["--offline-r4-schema", "first.zip", "--mystery", _SECRET],
    ],
)
def test_bad_cli_flags_do_not_echo_source_or_archive_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], flags: list[str]
) -> None:
    files = _source_files(tmp_path)
    assert (
        public_cli(
            [
                "fhir",
                "file-batch-encrypted-demo",
                "--synthetic-only",
                "--ephemeral-demo",
                *flags,
                *(str(p) for p in files),
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert "exact_fictional_ephemeral_file_flags_required" in output.err
    assert _SECRET not in output.err


def test_without_schema_option_backward_compatible_original_receipt() -> None:
    report = run_fictional_file_batch_encrypted_demo(
        _two(), synthetic_only=True, ephemeral_demo=True
    )
    assert report["import_count"] == 2
    assert report["ephemeral_store_removed"] is True
    assert "official_r4_structural_gate" not in report


def test_real_official_hl7_r4_zip_required_for_actual_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Actual downloaded HL7 4.0.1 ZIP and pinned jsonschema, NOT a double."""
    import hashlib
    from importlib.metadata import version

    from medscale.fhirkit.r4_schema import PINNED_JSONSCHEMA_VERSION

    path = os.environ.get("MEDORIGIN_R4_OFFICIAL_SCHEMA_ZIP")
    if not path:
        pytest.skip("Official HL7 R4 ZIP must be explicitly supplied")
    archive = Path(path)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == OFFICIAL_R4_SCHEMA_ZIP_SHA256
    assert version("jsonschema") == PINNED_JSONSCHEMA_VERSION

    report: dict[str, Any] = run_fictional_file_batch_encrypted_demo(
        _two(),
        synthetic_only=True,
        ephemeral_demo=True,
        offline_r4_schema=archive,
    )
    assert report["verified_audit_events"] == 2
    assert report["ephemeral_store_removed"] is True
    assert report["official_r4_structural_gate"]["structural_not_validated_count"] == 2
    assert report["official_r4_structural_gate"]["structural_invalid_count"] == 0
    assert report["clinical_use_authorized"] is False

    changed = _two()
    changed[1]["entry"][0]["resource"]["valueString"] = 57
    import medscale.fhirkit.workspace_file_batch_demo as importer

    def forbid_storage(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("Must refuse malformed official schema document first")

    monkeypatch.setattr(importer, "TemporaryDirectory", forbid_storage)
    with pytest.raises(SyntheticFileImportDemoError, match="official_r4_structural_gate_refused"):
        run_fictional_file_batch_encrypted_demo(
            changed,
            synthetic_only=True,
            ephemeral_demo=True,
            offline_r4_schema=archive,
        )
