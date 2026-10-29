"""M5 — FHIR boundary contracts and integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from medscale.fhirkit import (
    FHIR_VALIDATOR_NAME,
    FhirStorageError,
    InvalidReportError,
    ValidationReport,
    load_report_from_json,
    report_hash,
    report_to_json,
    store_report,
    validate_fhir,
    validate_report_schema,
)
from medscale.fhirkit.storage import fhirkit_reports_dir, load_report
from medscale.reproducibility import content_hash

_SRC = Path(__file__).resolve().parents[1] / "src" / "medscale"


def _rule_input() -> dict[str, object]:
    return {
        "resourceType": "StructureDefinition",
        "id": "test-rule",
        "name": "TestRule",
        "status": "draft",
    }


def test_validate_fhir_always_available() -> None:
    report = validate_fhir(_rule_input())
    assert report.status == "valid"
    assert report.validator_name == FHIR_VALIDATOR_NAME
    assert report.format_version == "fhirkit-validation-report/v1"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"resourceType": None},
        {"resourceType": ""},
        {"resourceType": " "},
        {"resourceType": "patient"},
        {"resourceType": 4},
        {"resourceType": []},
    ],
)
def test_local_fhir_validator_never_marks_missing_resource_type_valid(
    payload: dict[str, object],
) -> None:
    """The public Python API must not make the CLI's rejected input look valid."""
    report = validate_fhir(payload)
    assert report.status == "invalid"
    assert report.validator_name == FHIR_VALIDATOR_NAME
    assert report.errors == ("invalid or missing FHIR resourceType",)
    assert report.input_hash == content_hash(payload)


def test_local_fhir_validator_rejects_non_object_python_input() -> None:
    from medscale.fhirkit import FhirValidationError

    with pytest.raises(FhirValidationError, match="FHIR resource must be a JSON object"):
        validate_fhir([])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "invalid_value",
    [
        float("nan"),
        float("inf"),
        -float("inf"),
        {"nested": float("nan")},
        {7: "non-string key"},
        ["valid", object()],
        ("tuples", "are not JSON arrays"),
    ],
)
def test_public_fhir_apis_reject_non_json_values_before_reporting_or_execution(
    invalid_value: object,
) -> None:
    from medscale.fhirkit import FhirValidationError, validate_fhir_with_validator

    payload = {"resourceType": "Patient", "extension": invalid_value}
    with pytest.raises(FhirValidationError, match="JSON"):
        validate_fhir(payload)
    # A fictional executable must not even be invoked after rejecting input.
    with pytest.raises(FhirValidationError, match="JSON"):
        validate_fhir_with_validator(payload, command=["fictional-never-launch"])


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"status": "approved"},
        {"status": 1},
        {"report_id": 123},
        {"input_hash": 9},
        {"validator_name": 7},
        {"validator_version": []},
        {"created_at": 22},
        {"errors": ("valid", 7)},
        {"warnings": ("valid", False)},
        {"errors": "text-is-not-an-array"},
        {"warnings": ["not-a-tuple"]},
    ],
)
def test_report_contract_rejects_invalid_python_fields(
    invalid_fields: dict[str, object],
) -> None:
    with pytest.raises(InvalidReportError):
        ValidationReport(**invalid_fields)  # type: ignore[arg-type]


def test_report_schema_rechecks_tampered_frozen_instance() -> None:
    report = ValidationReport(status="valid")
    object.__setattr__(report, "status", "fictional-drift")
    with pytest.raises(InvalidReportError):
        validate_report_schema(report)


def test_report_never_claims_valid_with_diagnostic_errors() -> None:
    with pytest.raises(InvalidReportError, match="valid report cannot contain errors"):
        ValidationReport(status="valid", errors=("fictional fatal error",))


def test_serialization_rejects_mutated_false_valid_report() -> None:
    report = ValidationReport(status="invalid", errors=("fictional fatal error",))
    object.__setattr__(report, "status", "valid")
    with pytest.raises(InvalidReportError, match="valid report cannot contain errors"):
        report_hash(report)
    with pytest.raises(InvalidReportError, match="valid report cannot contain errors"):
        report_to_json(report)


def test_report_loader_rejects_false_valid_errors_even_with_canonical_shape() -> None:
    valid = ValidationReport(status="invalid", errors=("fictional fatal error",))
    raw = report_to_json(valid).replace('"status":"invalid"', '"status":"valid"')
    with pytest.raises(InvalidReportError, match="valid report cannot contain errors"):
        load_report_from_json(raw)


def test_report_hash_is_deterministic() -> None:
    report = validate_fhir(_rule_input())
    assert report_hash(report) == report_hash(report)
    assert len(report_hash(report)) == 64


@pytest.mark.parametrize(
    "bad_report_json",
    [
        "{",
        '{"status":"valid","status":"invalid"}',
        '{"warnings":[NaN]}',
        '{"warnings":[Infinity]}',
        '{"warnings":[1e999]}',
        '{"errors":"not-an-array"}',
        '{"warnings":{"not":"an array"}}',
        '{"errors":[{"private":"not a message"}]}',
        '{"errors":[false]}',
        '{"warnings":[4]}',
    ],
)
def test_load_report_rejects_malformed_or_ambiguous_json(
    bad_report_json: str,
) -> None:
    with pytest.raises(InvalidReportError) as exc:
        load_report_from_json(bad_report_json)
    assert bad_report_json not in str(exc.value)


def test_load_report_rejects_duplicate_status_without_leaking_storage_details(
    tmp_path: Path,
) -> None:
    report = validate_fhir(_rule_input())
    saved = store_report(report, root=tmp_path)
    clean = saved.read_text(encoding="utf-8")
    assert '"status":"valid"' in clean
    saved.write_text(
        clean.replace('"status":"valid"', '"status":"invalid","status":"valid"'),
        encoding="utf-8",
    )
    with pytest.raises(FhirStorageError, match="invalid or noncanonical") as exc:
        load_report(report_hash(report), root=tmp_path)
    assert 'invalid","status' not in str(exc.value)


def test_nullable_v1_report_roundtrips_with_canonical_status_encoding(
    tmp_path: Path,
) -> None:
    # A nullable in-memory status is part of the public v1 report contract.
    report = ValidationReport()
    canonical = report_to_json(report)
    assert '"status":""' in canonical
    loaded = load_report_from_json(canonical)
    assert loaded.status is None
    assert report_to_json(loaded) == canonical
    assert report_hash(loaded) == report_hash(report)
    path = store_report(report, root=tmp_path)
    assert load_report(report_hash(report), root=tmp_path) == path.read_text(encoding="utf-8")


def test_report_round_trip_storage(tmp_path: Path) -> None:
    report = validate_fhir(_rule_input())
    stored = store_report(report, root=tmp_path)
    expected_dir = fhirkit_reports_dir(tmp_path) / report_hash(report)
    assert stored == expected_dir / "report.json"
    loaded = load_report_from_json(stored.read_text(encoding="utf-8"))
    assert loaded.format_version == report.format_version
    assert loaded.input_hash == report.input_hash


def test_existing_report_artifact_cannot_be_overwritten(tmp_path: Path) -> None:
    report = validate_fhir(_rule_input())
    target = store_report(report, root=tmp_path)
    target.write_text("preserve these existing bytes", encoding="utf-8")

    with pytest.raises(FhirStorageError):
        store_report(report, root=tmp_path)
    assert target.read_text(encoding="utf-8") == "preserve these existing bytes"


def test_repeat_store_preserves_original_file_timestamp(tmp_path: Path) -> None:
    import os

    report = validate_fhir(_rule_input())
    target = store_report(report, root=tmp_path)
    preserved_ns = 946684800_000_000_000
    os.utime(target, ns=(preserved_ns, preserved_ns))
    assert store_report(report, root=tmp_path) == target
    assert target.stat().st_mtime_ns == preserved_ns


def test_existing_symlink_artifact_cannot_overwrite_target(tmp_path: Path) -> None:
    report = validate_fhir(_rule_input())
    target = fhirkit_reports_dir(tmp_path) / report_hash(report) / "report.json"
    target.parent.mkdir(parents=True)
    victim = tmp_path / "unrelated-user-file.txt"
    victim.write_text("preserve unrelated data", encoding="utf-8")
    try:
        target.symlink_to(victim)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation not supported by this host: {exc}")

    with pytest.raises(FhirStorageError):
        store_report(report, root=tmp_path)
    assert target.is_symlink()
    assert victim.read_text(encoding="utf-8") == "preserve unrelated data"


def test_load_report_blocks_absolute_directory_escape(tmp_path: Path) -> None:
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    private = unrelated / "report.json"
    private.write_text("fictional unrelated bytes", encoding="utf-8")

    with pytest.raises(FhirStorageError, match="canonical SHA-256"):
        load_report(str(unrelated), root=tmp_path / "safe")
    assert private.read_text(encoding="utf-8") == "fictional unrelated bytes"


@pytest.mark.parametrize("invalid_hash", ["../private", "f" * 63, "Z" * 64, "0" * 65, ""])
def test_load_report_rejects_noncanonical_hash_input(tmp_path: Path, invalid_hash: str) -> None:
    with pytest.raises(FhirStorageError, match="canonical SHA-256"):
        load_report(invalid_hash, root=tmp_path)


def test_load_report_verifies_canonical_content(tmp_path: Path) -> None:
    report = validate_fhir(_rule_input())
    target = store_report(report, root=tmp_path)
    digest = report_hash(report)
    assert load_report(digest, root=tmp_path) == report_to_json(report)

    target.write_text("fictional corrupted bytes", encoding="utf-8")
    with pytest.raises(FhirStorageError, match="invalid or noncanonical"):
        load_report(digest, root=tmp_path)


def test_load_report_rejects_symlinked_report(tmp_path: Path) -> None:
    report = validate_fhir(_rule_input())
    digest = report_hash(report)
    target = fhirkit_reports_dir(tmp_path) / digest / "report.json"
    target.parent.mkdir(parents=True)
    unrelated = tmp_path / "external-report.json"
    unrelated.write_text(report_to_json(report), encoding="utf-8")
    try:
        target.symlink_to(unrelated)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation not supported by this host: {exc}")
    with pytest.raises(FhirStorageError, match="symlink"):
        load_report(digest, root=tmp_path)


def _redirect_report_parent(root: Path, digest: str, outside: Path, layer: str) -> Path:
    """Create only fictional symlinked report ancestors in a temporary root."""
    base = fhirkit_reports_dir(root)
    ancestor = {
        "fhirkit": root / "fhirkit",
        "reports": base,
        "digest": base / digest,
    }[layer]
    ancestor.parent.mkdir(parents=True, exist_ok=True)
    outside.mkdir()
    try:
        ancestor.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")
    if layer == "fhirkit":
        return outside / "reports" / digest / "report.json"
    if layer == "reports":
        return outside / digest / "report.json"
    return outside / "report.json"


@pytest.mark.parametrize("layer", ["fhirkit", "reports", "digest"])
def test_store_rejects_symlinked_report_ancestors(tmp_path: Path, layer: str) -> None:
    report = validate_fhir(_rule_input())
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    target = _redirect_report_parent(root, report_hash(report), outside, layer)

    with pytest.raises(FhirStorageError, match="symlinked report directory"):
        store_report(report, root=root)
    assert not target.exists(), "store must not write outside the report root"


@pytest.mark.parametrize("layer", ["fhirkit", "reports", "digest"])
def test_load_rejects_symlinked_report_ancestors(tmp_path: Path, layer: str) -> None:
    report = validate_fhir(_rule_input())
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    digest = report_hash(report)
    target = _redirect_report_parent(root, digest, outside, layer)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report_to_json(report), encoding="utf-8")

    with pytest.raises(FhirStorageError, match="symlinked report directory"):
        load_report(digest, root=root)
    assert target.read_text(encoding="utf-8") == report_to_json(report)


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

    return [_sys.executable, "-c", 'print(\'{"status":"valid","errors":[]}\')']


def _echo_input_path_command() -> list[str]:
    import sys as _sys

    return [
        _sys.executable,
        "-c",
        "import json, sys; "
        "print(json.dumps({'status':'valid', 'errors': [], 'warnings': [sys.argv[1]]}))",
    ]


@pytest.mark.parametrize(
    ("stream", "exit_code"),
    [("stdout", 0), ("stdout", 2), ("stderr", 0), ("stderr", 2)],
)
def test_external_validator_rejects_undecodable_output_without_leaking_bytes(
    stream: str,
    exit_code: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys as _sys

    from medscale.fhirkit import UnavailableValidatorError, validate_fhir_with_validator

    code = f"import sys; sys.{stream}.buffer.write(bytes([255])); sys.exit({exit_code})"
    monkeypatch.setattr("medscale.fhirkit.validate.tempfile.tempdir", str(tmp_path))
    with pytest.raises(UnavailableValidatorError, match="undecodable output") as exc:
        validate_fhir_with_validator(_rule_input(), command=[_sys.executable, "-c", code])
    assert str(tmp_path) not in str(exc.value)
    assert "255" not in str(exc.value)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_external_validator_bounds_untrusted_output_and_cleans_scratch(
    stream: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys as _sys

    from medscale.fhirkit import UnavailableValidatorError, validate_fhir_with_validator

    code = f"import sys; sys.{stream}.buffer.write(b'X' * (2 * 1024 * 1024)); sys.exit(0)"
    monkeypatch.setattr("medscale.fhirkit.validate.tempfile.tempdir", str(tmp_path))
    with pytest.raises(UnavailableValidatorError, match="output limit") as exc:
        validate_fhir_with_validator(_rule_input(), command=[_sys.executable, "-c", code])
    assert str(tmp_path) not in str(exc.value)
    assert "XXXXX" not in str(exc.value)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_external_validator_output_limit_terminates_live_subprocess(
    stream: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys as _sys

    from medscale.fhirkit import UnavailableValidatorError, validate_fhir_with_validator

    code = (
        "import sys, time; "
        f"sys.{stream}.buffer.write(b'X' * (2 * 1024 * 1024)); "
        f"sys.{stream}.flush(); "
        "time.sleep(30)"
    )
    monkeypatch.setattr("medscale.fhirkit.validate.tempfile.tempdir", str(tmp_path))
    monkeypatch.setattr("medscale.fhirkit.validate._VALIDATOR_TIMEOUT_SECONDS", 5)
    with pytest.raises(UnavailableValidatorError, match="output limit"):
        validate_fhir_with_validator(_rule_input(), command=[_sys.executable, "-c", code])
    assert list(tmp_path.iterdir()) == []


def test_external_validator_timeout_is_bounded_and_redacted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import sys as _sys

    from medscale.fhirkit import UnavailableValidatorError, validate_fhir_with_validator

    monkeypatch.setattr("medscale.fhirkit.validate.tempfile.tempdir", str(tmp_path))
    monkeypatch.setattr("medscale.fhirkit.validate._VALIDATOR_TIMEOUT_SECONDS", 0.1)
    with pytest.raises(UnavailableValidatorError, match="timed out") as exc:
        validate_fhir_with_validator(
            _rule_input(), command=[_sys.executable, "-c", "import time; time.sleep(5)"]
        )
    assert str(tmp_path) not in str(exc.value)
    assert list(tmp_path.iterdir()) == []


def test_external_validator_spawn_failure_is_redacted_and_cleans_scratch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from medscale.fhirkit import UnavailableValidatorError, validate_fhir_with_validator

    monkeypatch.setattr("medscale.fhirkit.validate.tempfile.tempdir", str(tmp_path))
    missing_executable = tmp_path / "fictional-no-such-validator"
    with pytest.raises(UnavailableValidatorError, match="could not be started") as exc:
        validate_fhir_with_validator(_rule_input(), command=[str(missing_executable)])
    assert str(tmp_path) not in str(exc.value)
    assert list(tmp_path.iterdir()) == []


def test_external_validator_nonzero_exit_does_not_echo_tool_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import sys as _sys

    from medscale.fhirkit import UnavailableValidatorError, validate_fhir_with_validator

    monkeypatch.setattr("medscale.fhirkit.validate.tempfile.tempdir", str(tmp_path))
    command = [
        _sys.executable,
        "-c",
        "import sys; print('fictional PRIVATE_STDOUT'); "
        "sys.stderr.write('fictional PRIVATE_STDERR'); sys.exit(2)",
    ]
    with pytest.raises(UnavailableValidatorError, match="nonzero exit") as exc:
        validate_fhir_with_validator(_rule_input(), command=command)
    assert "PRIVATE" not in str(exc.value)
    assert str(tmp_path) not in str(exc.value)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "unqualified_output",
    [
        "",
        "{}",
        "[]",
        "42",
        '{"status":"unknown"}',
        '{"resourceType":"OperationOutcome","issue":[]}',
    ],
)
def test_external_validator_requires_explicit_supported_status(
    unqualified_output: str,
) -> None:
    import sys as _sys

    from medscale.fhirkit import InvalidReportError, validate_fhir_with_validator

    command = [_sys.executable, "-c", f"print({unqualified_output!r})"]
    with pytest.raises(InvalidReportError, match="explicit valid or invalid status"):
        validate_fhir_with_validator(_rule_input(), command=command)


def test_external_validator_honors_invalid_status_without_errors() -> None:
    import sys as _sys

    from medscale.fhirkit import validate_fhir_with_validator

    response = '{"status":"invalid","errors":[]}'
    command = [_sys.executable, "-c", f"print({response!r})"]
    report = validate_fhir_with_validator(_rule_input(), command=command)
    assert report.status == "invalid"
    assert report.errors == ()


@pytest.mark.parametrize(
    "invalid_validator_output",
    [
        '{"status":"invalid","status":"valid","errors":[]}',
        '{"status":"valid","errors":[],"errors":[]}',
        '{"status":"valid","meta":{"marker":1,"marker":2}}',
        '{"status":"valid","warnings":[NaN]}',
        '{"status":"valid","warnings":[Infinity]}',
        '{"status":"valid","warnings":[-Infinity]}',
        '{"status":"valid","meta":{"overflow":1e999}}',
    ],
)
def test_external_validator_rejects_ambiguous_or_nonfinite_json_output(
    invalid_validator_output: str,
) -> None:
    import sys as _sys

    from medscale.fhirkit import InvalidReportError, validate_fhir_with_validator

    command = [_sys.executable, "-c", f"print({invalid_validator_output!r})"]
    with pytest.raises(InvalidReportError, match="external validator output") as exc:
        validate_fhir_with_validator(_rule_input(), command=command)
    assert invalid_validator_output not in str(exc.value)


@pytest.mark.parametrize(
    "invalid_output",
    [
        '{"status":"valid","errors":"fictional confidential error"}',
        '{"status":"valid","errors":{"detail":"fictional confidential error"}}',
        '{"status":"valid","errors":[1]}',
        '{"status":"valid","errors":[false]}',
        '{"status":"valid","errors":[{"severity":"error"}]}',
        '{"status":"valid","warnings":"fictional confidential warning"}',
        '{"status":"valid","warnings":[{"detail":"fictional confidential warning"}]}',
        '{"status":"valid","warnings":[null]}',
        '{"status":"invalid","issue":{"detail":"fictional confidential issue"}}',
        '{"status":"valid","errors":[],"issue":[false]}',
    ],
)
def test_external_validator_rejects_untyped_diagnostics_without_echo(
    invalid_output: str,
) -> None:
    import sys as _sys

    from medscale.fhirkit import InvalidReportError, validate_fhir_with_validator

    command = [_sys.executable, "-c", f"print({invalid_output!r})"]
    with pytest.raises(InvalidReportError, match="diagnostics") as exc:
        validate_fhir_with_validator(_rule_input(), command=command)
    assert invalid_output not in str(exc.value)
    assert "confidential" not in str(exc.value)


@pytest.mark.parametrize(
    ("payload", "expected_status", "expected_errors", "expected_warnings"),
    [
        ('{"status":"valid","warnings":["fictional notice"]}', "valid", (), ("fictional notice",)),
        ('{"status":"invalid","errors":["fictional error"]}', "invalid", ("fictional error",), ()),
        ('{"status":"valid","issue":["fictional issue"]}', "invalid", ("fictional issue",), ()),
    ],
)
def test_external_validator_preserves_text_diagnostic_protocol(
    payload: str,
    expected_status: str,
    expected_errors: tuple[str, ...],
    expected_warnings: tuple[str, ...],
) -> None:
    import sys as _sys

    from medscale.fhirkit import validate_fhir_with_validator

    report = validate_fhir_with_validator(
        _rule_input(), command=[_sys.executable, "-c", f"print({payload!r})"]
    )
    assert report.status == expected_status
    assert report.errors == expected_errors
    assert report.warnings == expected_warnings


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
    from medscale.fhirkit import validate_fhir_with_validator

    monkeypatch.chdir(tmp_path)
    report = validate_fhir_with_validator(_rule_input(), command=_echo_input_path_command())

    scratch = Path(report.warnings[0])
    assert scratch.name == "medscale-fhirkit-input.json"
    assert scratch.parent.resolve() != tmp_path.resolve(), "scratch file must not live in CWD"
    assert not scratch.exists(), "scratch file must be removed after validation"
    assert not scratch.parent.exists(), "scratch directory must be removed after validation"
