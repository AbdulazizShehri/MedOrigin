"""M5 — FHIR boundary contracts and integration tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from medscale.fhirkit import (
    FHIR_VALIDATOR_NAME,
    InvalidReportError,
    ValidationReport,
    load_report_from_json,
    report_hash,
    report_to_json,
    store_report,
    validate_fhir,
    validate_report_schema,
)
from medscale.fhirkit.storage import fhirkit_reports_dir
from medscale.reproducibility import content_hash

_SRC = Path(__file__).resolve().parents[1] / "src" / "medscale"


def _rule_input() -> dict[str, object]:
    return {
        "resourceType": "StructureDefinition",
        "id": "test-rule",
        "name": "TestRule",
        "status": "draft",
    }


def test_local_fhir_boundary_is_available_but_never_claims_full_validation() -> None:
    report = validate_fhir(_rule_input())
    assert report.status == "not_validated"
    assert report.errors == ()
    assert report.warnings and "not performed" in report.warnings[0]
    assert report.validator_name == FHIR_VALIDATOR_NAME
    assert report.format_version == "fhirkit-validation-report/v1"


@pytest.mark.parametrize(
    "payload",
    [
        {"resourceType": "UnknownFictionalResource", "id": "synthetic-bogus"},
        {"resourceType": "Bundle", "type": "collection", "entry": []},
    ],
)
def test_local_fhir_boundary_never_grants_schema_validity(
    payload: dict[str, object],
) -> None:
    report = validate_fhir(payload)
    assert report.status == "not_validated"
    assert report.errors == ()
    assert report.warnings and "FHIR R4 schema" in report.warnings[0]
    assert report.input_hash == content_hash(payload)


def test_report_hash_is_deterministic() -> None:
    report = validate_fhir(_rule_input())
    assert report_hash(report) == report_hash(report)
    assert len(report_hash(report)) == 64


def test_report_round_trip_storage(tmp_path: Path) -> None:
    report = validate_fhir(_rule_input())
    stored = store_report(report, root=tmp_path)
    expected_dir = fhirkit_reports_dir(tmp_path) / report_hash(report)
    assert stored == expected_dir / "report.json"
    loaded = load_report_from_json(stored.read_text(encoding="utf-8"))
    assert loaded.format_version == report.format_version
    assert loaded.input_hash == report.input_hash


def test_validate_report_schema_rejects_invalid_shape() -> None:
    with pytest.raises(InvalidReportError):
        validate_report_schema(ValidationReport(format_version="wrong"))


def test_content_addressed_storage_is_idempotent() -> None:
    report = validate_fhir(_rule_input())
    text = report_to_json(report)
    assert text == report_to_json(validate_fhir(_rule_input()))


def test_no_absolute_path_leakage_in_storage() -> None:
    report = validate_fhir(_rule_input())
    json_text = report_to_json(report)
    for path_fragment in ["C:\\", "C:/", "/home/", "/Users/", "/tmp/"]:
        assert path_fragment not in json_text


def test_fhir_boundary_does_not_import_forbidden_modules() -> None:
    forbidden = {"dataset", "research", "backends", "bench"}
    for py in (_SRC / "fhirkit").rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for token in forbidden:
            assert f"medscale.{token}" not in text


def test_fhir_public_api_is_complete() -> None:
    import medscale.fhirkit as fhirkit

    expected_public = {
        "FHIR_VALIDATOR_NAME",
        "FhirBoundaryError",
        "FhirMissingDependencyError",
        "FhirStorageError",
        "FhirValidationError",
        "FORMAT_VERSION",
        "InvalidReportError",
        "UnavailableValidatorError",
        "ValidationReport",
        "load_report_from_json",
        "report_hash",
        "report_to_json",
        "store_report",
        "validate_fhir",
        "validate_report_schema",
    }
    assert expected_public.issubset(set(fhirkit.__all__))


def test_report_hash_matches_content_hash() -> None:
    report = validate_fhir(_rule_input())
    assert report_hash(report) == content_hash(json.loads(report_to_json(report)))


def test_explicit_timestamp_policy() -> None:
    report = validate_fhir(_rule_input(), created_at="2026-07-13T00:00:00+01:00")
    assert report.created_at == "2026-07-13T00:00:00+01:00"
    data = json.loads(report_to_json(report))
    assert data["created_at"] == "2026-07-13T00:00:00+01:00"


def test_storage_contract_is_content_addressed() -> None:
    report = validate_fhir(_rule_input())
    json_text = report_to_json(report)
    assert json_text == report_to_json(report)


# ---------------------------------------------------------------------------
# External-validator scratch-file safety (regression: the scratch payload used
# to be written to a RELATIVE path in the caller's CWD and then deleted,
# destroying any pre-existing user file of the same name).
# ---------------------------------------------------------------------------


def _echo_empty_report_command() -> list[str]:
    import sys as _sys

    return [_sys.executable, "-c", "print('{}')"]


def _echo_input_path_command() -> list[str]:
    import sys as _sys

    return [
        _sys.executable,
        "-c",
        "import json, sys; print(json.dumps({'warnings': [sys.argv[1]]}))",
    ]


def test_external_validator_never_clobbers_cwd_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from medscale.fhirkit import validate_fhir_with_validator

    monkeypatch.chdir(tmp_path)
    victim = tmp_path / "medscale-fhirkit-input.json"
    victim.write_text("precious user data", encoding="utf-8", newline="\n")

    report = validate_fhir_with_validator(_rule_input(), command=_echo_empty_report_command())

    assert report.input_hash
    assert victim.exists(), "pre-existing user file must survive external validation"
    assert victim.read_text(encoding="utf-8") == "precious user data"


def test_external_validator_scratch_file_is_isolated_and_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    from medscale.fhirkit import report_to_json, validate_fhir_with_validator

    monkeypatch.chdir(tmp_path)
    roots: list[Path] = []
    original_mkdtemp = tempfile.mkdtemp

    def captured_mkdtemp(*args: Any, **kwargs: Any) -> str:
        root = Path(original_mkdtemp(*args, **kwargs))
        roots.append(root)
        return str(root)

    monkeypatch.setattr(tempfile, "mkdtemp", captured_mkdtemp)
    report = validate_fhir_with_validator(_rule_input(), command=_echo_input_path_command())

    assert report.status == "not_validated"
    assert report.errors == ()
    assert report.warnings and "not source-qualified" in report.warnings[0]
    assert len(roots) == 1
    assert roots[0].resolve() != tmp_path.resolve(), "scratch directory cannot be CWD"
    assert not roots[0].exists(), "the disposable source file and directory were removed"
    assert str(roots[0]) not in report_to_json(report), "validator paths are never mirrored"
