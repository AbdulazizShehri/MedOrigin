"""Unqualified external FHIR output must never certify patient data.

This explicit caller-supplied local tool adapter is not a qualified validator.
Tests only invoke tiny local Python emitters, no network or real PHI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from medscale.fhirkit import (
    FhirMissingDependencyError,
    InvalidReportError,
    UnavailableValidatorError,
    report_to_json,
    validate_fhir_with_validator,
)
from medscale.fhirkit.validate import (
    EXTERNAL_UNQUALIFIED_ERROR,
    EXTERNAL_UNQUALIFIED_VALIDATOR_NAME,
    EXTERNAL_UNQUALIFIED_WARNING,
)

SENTINEL = "PRIVATE_FICTIONAL_PATIENT_NAME_CANNOT_ESCAPE"
SOURCE = {"resourceType": "Patient", "id": "invented", "name": [{"text": SENTINEL}]}


def _emit(payload: object) -> list[str]:
    encoded = json.dumps(payload, sort_keys=True)
    return [sys.executable, "-c", "print(" + repr(encoded) + ")"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"resourceType": "OperationOutcome", "status": "valid"},
        {
            "validator_name": "authoritative-official-validator",
            "validator_version": "FHIR R4 full",
            "validated": True,
            "warnings": [SENTINEL],
        },
        {"errors": [], "warnings": [SENTINEL]},
        {"issue": [{"severity": "warning", "diagnostics": SENTINEL}]},
        {"issue": [{"severity": "information", "diagnostics": SENTINEL}]},
    ],
)
def test_empty_or_claimed_success_never_becomes_valid(payload: object) -> None:
    report = validate_fhir_with_validator(SOURCE, command=_emit(payload))
    assert report.status == "not_validated"
    assert report.errors == ()
    assert report.validator_name == EXTERNAL_UNQUALIFIED_VALIDATOR_NAME
    assert report.warnings == (EXTERNAL_UNQUALIFIED_WARNING,)
    assert "not source-qualified" in report.warnings[0]
    printed = report_to_json(report)
    assert SENTINEL not in printed
    assert "authoritative-official-validator" not in printed
    assert '"status":"valid"' not in printed


@pytest.mark.parametrize(
    "payload",
    [
        {"errors": [SENTINEL]},
        {"issue": [{"severity": "error", "diagnostics": SENTINEL}]},
        {"issue": [{"severity": "fatal", "details": {"text": SENTINEL}}]},
        {"errors": [SENTINEL], "warnings": [SENTINEL]},
    ],
)
def test_untrusted_errors_are_only_fixed_negative_tokens(payload: object) -> None:
    report = validate_fhir_with_validator(SOURCE, command=_emit(payload))
    assert report.status == "invalid"
    assert report.errors == (EXTERNAL_UNQUALIFIED_ERROR,)
    assert report.warnings == (EXTERNAL_UNQUALIFIED_WARNING,)
    assert SENTINEL not in report_to_json(report)


@pytest.mark.parametrize(
    "payload",
    [
        [],
        None,
        "false-positive",
        {"errors": SENTINEL},
        {"errors": None},
        {"issue": [SENTINEL]},
        {"issue": [{"severity": "success", "diagnostics": SENTINEL}]},
        {"warnings": SENTINEL},
        {"errors": [SENTINEL] * 33},
        {"issue": [{"severity": "warning"}] * 33},
    ],
)
def test_malformed_unqualified_output_refused_without_patient_text(
    payload: object,
) -> None:
    with pytest.raises(InvalidReportError) as exc:
        validate_fhir_with_validator(SOURCE, command=_emit(payload))
    assert SENTINEL not in str(exc.value)


def test_malformed_non_json_stays_redacted() -> None:
    with pytest.raises(InvalidReportError) as exc:
        validate_fhir_with_validator(
            SOURCE,
            command=[sys.executable, "-c", f"print({SENTINEL!r})"],
        )
    assert SENTINEL not in str(exc.value)


def test_nonzero_external_command_never_returns_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(UnavailableValidatorError) as exc:
        validate_fhir_with_validator(
            SOURCE,
            command=[
                sys.executable,
                "-c",
                f"import sys; print({SENTINEL!r}, file=sys.stderr); sys.exit(7)",
            ],
        )
    assert SENTINEL not in str(exc.value)
    assert not (tmp_path / "medscale-fhirkit-input.json").exists()


def test_external_output_size_limit_refuses_giant_diagnostics() -> None:
    with pytest.raises(InvalidReportError, match="output_bounds_refused"):
        validate_fhir_with_validator(
            SOURCE,
            command=[sys.executable, "-c", "print('X'*65000)"],
        )


@pytest.mark.parametrize(
    "command",
    [
        [],
        ["python", ""],
        ["python", "bad\x00arg"],
        ["python", "a" * 2050],
    ],
)
def test_bad_external_commands_fail_closed_and_redacted(command: list[str]) -> None:
    with pytest.raises(UnavailableValidatorError):
        validate_fhir_with_validator(SOURCE, command=command)


def test_missing_validator_explicitly_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MEDSCALE_FHIR_VALIDATOR", raising=False)
    with pytest.raises(FhirMissingDependencyError, match="No source-qualified"):
        validate_fhir_with_validator(SOURCE)


def test_source_content_hash_still_bound_without_exposing_payload() -> None:
    from medscale.reproducibility import content_hash

    a = validate_fhir_with_validator(SOURCE, command=_emit({}))
    b = validate_fhir_with_validator({**SOURCE, "id": "different-invented-id"}, command=_emit({}))
    assert a.input_hash == content_hash(SOURCE)
    assert b.input_hash != a.input_hash
    assert a.status == b.status == "not_validated"
    assert SENTINEL not in report_to_json(a)
