"""Core FHIR input admission: no ambiguous JSON or artifact on refusal."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from medscale.cli import fhir as fhir_cli
from medscale.fhirkit.input import (
    MAX_FHIR_INPUT_BYTES,
    FhirInputError,
    read_fhir_json_document,
)


def _fixture(tmp_path: Path, raw: bytes) -> Path:
    source = tmp_path / "fictional-fhir.json"
    source.write_bytes(raw)
    return source


def test_valid_synthetic_nested_object_and_unicode(tmp_path: Path) -> None:
    obj = {"resourceType": "Patient", "id": "synthetic", "meta": {"tag": [{"code": "تجريبي"}]}}
    source = _fixture(tmp_path, json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    assert read_fhir_json_document(source) == obj


@pytest.mark.parametrize(
    ("name", "raw", "code"),
    [
        (
            "duplicate_top",
            b'{"resourceType":"Patient","resourceType":"Observation"}',
            "duplicate_json_key",
        ),
        (
            "duplicate_nested",
            b'{"resourceType":"Patient","meta":{"tag":1,"tag":2}}',
            "duplicate_json_key",
        ),
        (
            "duplicate_list",
            b'{"resourceType":"Patient","entry":[{"id":1,"id":2}]}',
            "duplicate_json_key",
        ),
        ("constant_nan", b'{"resourceType":"Patient","x":NaN}', "nonfinite_json_number"),
        ("constant_infinity", b'{"resourceType":"Patient","x":Infinity}', "nonfinite_json_number"),
        ("exponent_overflow", b'{"resourceType":"Patient","x":1e999}', "nonfinite_json_number"),
        (
            "negative_exponent_overflow",
            b'{"resourceType":"Patient","x":-1e999}',
            "nonfinite_json_number",
        ),
        (
            "constant_negative_infinity",
            b'{"resourceType":"Patient","x":-Infinity}',
            "nonfinite_json_number",
        ),
        ("scalar_string", b'"Patient"', "json_root_not_object"),
        ("scalar_null", b"null", "json_root_not_object"),
        ("root_array", b'[{"resourceType":"Patient"}]', "json_root_not_object"),
        ("root_boolean", b"true", "json_root_not_object"),
        (
            "utf8_bom",
            bytes.fromhex("efbbbf") + b'{"resourceType":"Patient"}',
            "utf8_bom_not_allowed",
        ),
        (
            "invalid_utf8",
            b'{"resourceType":"Patient","id":"' + bytes.fromhex("ff") + b'"}',
            "input_not_utf8",
        ),
        ("malformed", b'{"resourceType":', "malformed_json"),
    ],
)
def test_reject_ambiguous_or_invalid_document(
    tmp_path: Path, name: str, raw: bytes, code: str
) -> None:
    del name
    with pytest.raises(FhirInputError, match=code):
        read_fhir_json_document(_fixture(tmp_path, raw))


def test_refuse_oversized_without_parsing(tmp_path: Path) -> None:
    source = _fixture(tmp_path, b"x" * (MAX_FHIR_INPUT_BYTES + 1))
    with pytest.raises(FhirInputError, match="input_size_limit_exceeded"):
        read_fhir_json_document(source)


def test_refuse_directory(tmp_path: Path) -> None:
    with pytest.raises(FhirInputError, match=r"input_not_regular_file|input_file_unavailable"):
        read_fhir_json_document(tmp_path)


def test_refuse_input_symlink_when_supported(tmp_path: Path) -> None:
    original = _fixture(tmp_path, b'{"resourceType":"Patient"}')
    link = tmp_path / "alias.json"
    try:
        link.symlink_to(original)
    except (OSError, NotImplementedError):
        pytest.skip("host does not grant symlink privilege")
    with pytest.raises(FhirInputError, match="symlink_input_refused"):
        read_fhir_json_document(link)


def test_json_nesting_over_limit_is_rejected(tmp_path: Path) -> None:
    deep = '{"resourceType":"Patient","x":' + ("[" * 70) + "1" + ("]" * 70) + "}"
    with pytest.raises(FhirInputError, match="json_nesting_too_deep"):
        read_fhir_json_document(_fixture(tmp_path, deep.encode("utf-8")))


@pytest.mark.parametrize("summary_only", [False, True])
@pytest.mark.parametrize(
    "raw",
    [
        b'{"resourceType":"Patient","resourceType":"Observation"}',
        b'{"resourceType":"Patient","active":NaN}',
        b'[{"resourceType":"Patient"}]',
        b'{"resourceType":"Patient","id":"\\xff"}',
    ],
)
def test_rejected_cli_input_never_writes_report_or_echoes_contents(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    raw: bytes,
    summary_only: bool,
) -> None:
    source = _fixture(tmp_path, raw)
    output = tmp_path / "reports"
    argv = [str(source), "--output-dir", str(output)]
    if summary_only:
        argv.append("--summary-only")
    assert fhir_cli.main(argv) == 1
    printed = capsys.readouterr()
    assert not printed.out
    assert "input read error:" in printed.err
    assert "resourceType" not in printed.err
    assert not output.exists()


def test_normal_fictional_cli_still_records_unverified_provenance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _fixture(tmp_path, b'{"resourceType":"Patient","id":"synthetic"}')
    output = tmp_path / "reports"
    assert fhir_cli.main([str(source), "--output-dir", str(output)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "not_validated"
    reports = list(output.rglob("report.json"))
    assert len(reports) == 1


def test_summary_only_synthetic_valid_json_remains_compatible(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _fixture(tmp_path, b'{"resourceType":"Patient","id":"synthetic"}')
    assert fhir_cli.main(["validate", str(source), "--summary-only"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "synthetic"


def test_refuse_huge_json_integer_before_provenance(tmp_path: Path) -> None:
    raw = b'{"resourceType":"Patient","value":' + (b"9" * 200) + b"}"
    with pytest.raises(FhirInputError, match="json_integer_too_long"):
        read_fhir_json_document(_fixture(tmp_path, raw))


def test_reject_unicode_escaped_duplicate_key(tmp_path: Path) -> None:
    # The JSON decoder normalizes escaped member names before duplicate checks.
    raw = b'{"resourceType":"Patient","r' + bytes.fromhex("5c") + b'u0065sourceType":"Observation"}'
    with pytest.raises(FhirInputError, match="duplicate_json_key"):
        read_fhir_json_document(_fixture(tmp_path, raw))


def test_rejected_cli_precedes_optional_schema_lookup(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _fixture(tmp_path, b'{"resourceType":"Patient","resourceType":"Observation"}')
    output = tmp_path / "reports"
    assert (
        fhir_cli.main(
            [
                str(source),
                "--offline-r4-schema",
                str(tmp_path / "nonexistent-official-r4.zip"),
                "--output-dir",
                str(output),
            ]
        )
        == 1
    )
    stderr = capsys.readouterr().err
    assert "duplicate_json_key" in stderr
    assert "schema" not in stderr
    assert not output.exists()
