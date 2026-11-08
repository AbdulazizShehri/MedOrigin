"""Portable offline structural FHIR R4 OperationOutcome, nonclinical and redacted."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from medscale.cli import main as core_main
from medscale.fhirkit import r4_schema
from medscale.fhirkit.r4_outcome import (
    StructuralOutcomeError,
    structural_outcome_for_report,
    structural_outcome_to_json,
)
from medscale.fhirkit.report import ValidationReport

PRIVATE = "NEVER_DISCLOSE_FICTIONAL_PRIVATE_NAME_OR_HOST_PATH"
VALID_CAVEAT = r4_schema.PARTIAL_COVERAGE_WARNING
PINNED_VERSION = "R4-4.0.1/jsonschema-4.25.1"
VALIDATOR_NAME = "hl7-fhir-r4-json-schema-structural-only"


def _report(*, status: str, errors: tuple[str, ...] = ()) -> ValidationReport:
    return ValidationReport(
        input_hash=PRIVATE,
        validator_name=VALIDATOR_NAME,
        validator_version=PINNED_VERSION,
        status=status,
        warnings=(VALID_CAVEAT,),
        errors=errors,
        created_at=PRIVATE,
    )


def _fake_offline_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """SYNTHETIC test schema, explicitly not a qualified official R4 schema."""
    schema = {
        "$schema": r4_schema.OFFICIAL_R4_DRAFT,
        "id": r4_schema.OFFICIAL_R4_SCHEMA_ID,
        "definitions": {
            "Patient": {
                "type": "object",
                "required": ["resourceType"],
                "properties": {
                    "resourceType": {"const": "Patient"},
                    "id": {"type": "string"},
                    "active": {"type": "boolean"},
                },
                "additionalProperties": False,
            }
        },
        "$ref": "#/definitions/Patient",
    }
    raw_schema = json.dumps(schema).encode("utf-8")
    archive = tmp_path / "fictional-schema-only.zip"
    with zipfile.ZipFile(archive, mode="w") as z:
        z.writestr(r4_schema.OFFICIAL_R4_SCHEMA_MEMBER, raw_schema)
    monkeypatch.setattr(
        r4_schema,
        "OFFICIAL_R4_SCHEMA_ZIP_SHA256",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_BYTES", len(raw_schema))
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_DEFINITIONS", 1)
    monkeypatch.setattr(r4_schema, "version", lambda name: r4_schema.PINNED_JSONSCHEMA_VERSION)
    return archive


def test_realistic_structural_pass_yields_warning_and_never_valid() -> None:
    outcome = structural_outcome_for_report(_report(status="not_validated"))
    assert outcome == {
        "resourceType": "OperationOutcome",
        "issue": [
            {
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
        ],
    }
    assert PRIVATE not in structural_outcome_to_json(_report(status="not_validated"))


def test_invalid_schema_outcome_emits_bounded_fhir_structure_issues() -> None:
    raw = structural_outcome_to_json(
        _report(status="invalid", errors=("r4_json_schema_structural_error:type",))
    )
    outcome = json.loads(raw)
    assert outcome["resourceType"] == "OperationOutcome"
    assert [item["severity"] for item in outcome["issue"]] == ["error", "warning"]
    assert [item["code"] for item in outcome["issue"]] == ["structure", "informational"]
    assert outcome["issue"][0]["details"]["text"].endswith("type")
    assert PRIVATE not in raw
    assert "valid" not in json.dumps(outcome["issue"][0])


def test_truncation_stays_bounded_to_12_plus_warning() -> None:
    report = _report(
        status="invalid",
        errors=("r4_json_schema_structural_error:type",) * 12
        + ("r4_json_schema_additional_errors_not_reported",),
    )
    outcome: dict[str, Any] = structural_outcome_for_report(report)
    assert len(outcome["issue"]) == 14
    assert outcome["issue"][-2]["details"]["text"] == (
        "Further structural errors were omitted after the fixed limit."
    )
    assert outcome["issue"][-1]["severity"] == "warning"


@pytest.mark.parametrize(
    "report",
    [
        _report(status="valid"),
        _report(status="invalid"),
        _report(status="not_validated", errors=("r4_json_schema_structural_error:type",)),
        _report(status="invalid", errors=(PRIVATE,)),
        _report(status="invalid", errors=("r4_json_schema_structural_error:" + PRIVATE,)),
        _report(status="invalid", errors=("r4_json_schema_additional_errors_not_reported",)),
        _report(status="invalid", errors=("r4_json_schema_structural_error:type",) * 14),
        ValidationReport(status="not_validated", warnings=(VALID_CAVEAT,)),
        ValidationReport(
            validator_name=VALIDATOR_NAME,
            validator_version=PINNED_VERSION,
            status="not_validated",
            warnings=(PRIVATE,),
        ),
    ],
)
def test_refuse_unqualified_forged_or_source_leaking_reports(report: ValidationReport) -> None:
    with pytest.raises(StructuralOutcomeError):
        structural_outcome_for_report(report)


@pytest.mark.skipif(
    importlib.util.find_spec("jsonschema") is None,
    reason="pinned optional jsonschema not installed in base interpreter",
)
@pytest.mark.parametrize(
    "source,expected_severities",
    [
        ({"resourceType": "Patient", "id": "fictional", "active": True}, ["warning"]),
        ({"resourceType": "Patient", "id": "fictional", "active": "true"}, ["error", "warning"]),
        ({"resourceType": "OtherFictionalResource", "id": "fictional"}, ["error", "warning"]),
    ],
)
def test_real_cli_dispatcher_fake_offline_schema_exit_nonzero_and_source_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    source: dict[str, Any],
    expected_severities: list[str],
) -> None:
    archive = _fake_offline_archive(tmp_path, monkeypatch)
    data = tmp_path / PRIVATE
    data.write_text(json.dumps(source), encoding="utf-8")
    assert (
        core_main(
            [
                "fhir",
                "structural-outcome",
                "--synthetic-only",
                "--offline-r4-schema",
                str(archive),
                str(data),
            ]
        )
        == 2
    )
    printed = capsys.readouterr()
    outcome = json.loads(printed.out)
    assert printed.err == ""
    assert outcome["resourceType"] == "OperationOutcome"
    assert [issue["severity"] for issue in outcome["issue"]] == expected_severities
    assert PRIVATE not in printed.out
    assert str(archive) not in printed.out
    assert str(data) not in printed.out
    assert "fictional" not in printed.out
    assert not (tmp_path / "data").exists()
    assert list(tmp_path.rglob("report.json")) == []


@pytest.mark.parametrize(
    "tokens",
    [
        [],
        ["--synthetic-only"],
        ["--offline-r4-schema", PRIVATE, PRIVATE],
        ["--synthetic-only", "--offline-r4-schema", PRIVATE],
        ["--synthetic-only", "--offline-r4-schema", PRIVATE, PRIVATE, PRIVATE],
        ["--synthetic-only", "--offline-r4-schema", "--", PRIVATE],
        ["--synthetic-only", "--offline-r4-schema", PRIVATE, "--"],
        ["--synthetic-only", "--synthetic-only", PRIVATE, PRIVATE],
    ],
)
def test_cli_refuses_ambiguous_tokens_without_echo(
    capsys: pytest.CaptureFixture[str], tokens: list[str]
) -> None:
    assert core_main(["fhir", "structural-outcome", *tokens]) == 2
    printed = capsys.readouterr()
    assert printed.out == ""
    assert "explicit_synthetic_offline_schema_flags_required" in printed.err
    assert PRIVATE not in printed.err


def test_cli_help_never_reads_patient_file(capsys: pytest.CaptureFixture[str]) -> None:
    assert core_main(["fhir", "structural-outcome", "--help"]) == 0
    output = capsys.readouterr()
    assert "synthetic-only" in output.out
    assert "NOT full FHIR R4" in output.out
    assert output.err == ""


def test_cli_missing_source_keeps_no_report_and_redacts_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        core_main(
            [
                "fhir",
                "structural-outcome",
                "--synthetic-only",
                "--offline-r4-schema",
                str(tmp_path / "schema.zip"),
                str(tmp_path / PRIVATE),
            ]
        )
        == 1
    )
    printed = capsys.readouterr()
    assert printed.out == ""
    assert PRIVATE not in printed.err
    assert "source_input_refused" in printed.err


def test_cli_missing_official_schema_refuses_without_fake_outcome(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "synthetic.json"
    source.write_text('{"resourceType":"Patient","id":"fictional"}', encoding="utf-8")
    assert (
        core_main(
            [
                "fhir",
                "structural-outcome",
                "--synthetic-only",
                "--offline-r4-schema",
                str(tmp_path / PRIVATE),
                str(source),
            ]
        )
        == 2
    )
    printed = capsys.readouterr()
    assert printed.out == ""
    assert PRIVATE not in printed.err
    assert "qualified_offline_schema_missing" in printed.err


def test_optional_actual_official_r4_archive_and_derived_outcome() -> None:
    """Optional task-owned offline official source; no schema auto-download."""
    import os

    configured = os.environ.get("MEDORIGIN_OFFICIAL_R4_SCHEMA_ZIP")
    if not configured:
        pytest.skip("official R4 JSON Schema archive not supplied by the local QA")
    archive = Path(configured)
    for source, severities in (
        ({"resourceType": "Patient", "id": "fictional", "active": True}, ["warning"]),
        ({"resourceType": "Patient", "id": "fictional", "active": "true"}, ["error", "warning"]),
        ({"resourceType": "InventedNotFHIR", "id": "fictional"}, ["error", "warning"]),
        ({"resourceType": "StructureDefinition", "id": "fictional"}, ["warning"]),
    ):
        report = r4_schema.validate_offline_r4_json_structure(source, archive)
        outcome: dict[str, Any] = structural_outcome_for_report(report)
        assert [item["severity"] for item in outcome["issue"]] == severities
        assert isinstance(source["id"], str)
        assert source["id"] not in json.dumps(outcome)
        # Even the generated *OperationOutcome* must pass the same official
        # structural-only check; this does NOT establish full FHIR conformance.
        outcome_report = r4_schema.validate_offline_r4_json_structure(outcome, archive)
        assert outcome_report.status == "not_validated"
        assert outcome_report.errors == ()
