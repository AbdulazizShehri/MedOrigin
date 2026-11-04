"""Real two-file Core FHIR batch CLI; fictional-only, redacted R4 partial checks."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import zipfile
from importlib.metadata import version
from pathlib import Path

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit import r4_schema
from medscale.fhirkit.bundle_batch_assessment import (
    SyntheticBatchAssessmentError,
    assess_synthetic_bundle_batch_offline,
    synthetic_bundle_batch_assessment_json,
)
from medscale.fhirkit.workspace_demo import _fictional_bundle

_SECRET = "PRIVATE_FICTIONAL_PERSON_NAME_NEVER_OUTPUT"
_SHA = r4_schema.OFFICIAL_R4_SCHEMA_ZIP_SHA256


def _cases() -> list[dict]:
    first = _fictional_bundle()
    first["entry"][1]["resource"]["name"][0]["text"] = _SECRET
    second = copy.deepcopy(first)
    second["entry"][0]["resource"]["valueString"] = "Other invented observation"
    assert first != second
    return [first, second]


def _schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, reject: bool = False) -> Path:
    """Only a local unit-test schema, NEVER claim this is the real HL7 R4 ZIP."""
    schema = {
        "$schema": r4_schema.OFFICIAL_R4_DRAFT,
        "id": r4_schema.OFFICIAL_R4_SCHEMA_ID,
        "definitions": {
            "Bundle": {
                "type": "object",
                "required": ["resourceType", "type", "entry"],
                "properties": {
                    "resourceType": {"const": "Bundle"},
                    "type": {"const": "document" if reject else "collection"},
                    "entry": {"type": "array", "minItems": 1},
                    "meta": {"type": "object"},
                },
                "additionalProperties": False,
            }
        },
        "$ref": "#/definitions/Bundle",
    }
    raw = json.dumps(schema).encode()
    archive = tmp_path / "unit-test-fake-offline-schema.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(r4_schema.OFFICIAL_R4_SCHEMA_MEMBER, raw)
    monkeypatch.setattr(
        r4_schema, "OFFICIAL_R4_SCHEMA_ZIP_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest()
    )
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_BYTES", len(raw))
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_DEFINITIONS", 1)
    monkeypatch.setattr(r4_schema, "version", lambda _: r4_schema.PINNED_JSONSCHEMA_VERSION)
    return archive


def _cli(tmp_path: Path, archive: Path, sources: list[dict]) -> tuple[list[str], list[Path]]:
    paths = []
    for i, source in enumerate(sources, 1):
        item = tmp_path / f"{_SECRET}-{i}.json"
        item.write_text(json.dumps(source), encoding="utf-8")
        paths.append(item)
    return (
        [
            "fhir",
            "batch-bundle-assess",
            "--synthetic-only",
            "--offline-r4-schema",
            str(archive),
            *(str(path) for path in paths),
        ],
        paths,
    )


@pytest.mark.skipif(
    importlib.util.find_spec("jsonschema") is None,
    reason="optional jsonschema not installed",
)
@pytest.mark.parametrize("reject", [False, True])
def test_actual_two_source_offline_batch_uses_redacted_per_source_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    reject: bool,
) -> None:
    cases = _cases()
    archive = _schema(tmp_path, monkeypatch, reject=reject)
    tokens, paths = _cli(tmp_path, archive, cases)
    assert public_cli(tokens) == 2
    output = capsys.readouterr()
    assert output.err == ""
    report = json.loads(output.out)
    assert report["schema"] == "medorigin-core-synthetic-fhir-batch-dual-assessment/v1"
    assert report["status"] == "SYNTHETIC_BATCH_PARTIAL_R4_PRECHECK_ONLY"
    assert report["document_count"] == 2
    assert report["total_resource_count"] == 6
    assert report["structural_invalid_count"] == (2 if reject else 0)
    assert report["structural_not_validated_count"] == (0 if reject else 2)
    assert [item["document_ordinal"] for item in report["documents"]] == [1, 2]
    assert len({item["source_content_sha256"] for item in report["documents"]}) == 2
    assert [item["resource_count"] for item in report["documents"]] == [3, 3]
    assert [item["local_references_checked"] for item in report["documents"]] == [3, 3]
    assert [item["r4_structural_status"] for item in report["documents"]] == [
        "invalid" if reject else "not_validated"
    ] * 2
    assert [
        [issue["severity"] for issue in item["r4_operation_outcome"]["issue"]]
        for item in report["documents"]
    ] == [["error", "warning"] if reject else ["warning"]] * 2
    assert report["official_r4_archive_sha256"] == _SHA
    for flag in (
        "source_filenames_included",
        "resource_payload_included",
        "result_persisted",
        "network_access_performed",
        "cross_bundle_patient_join_performed",
        "fhir_r4_conformance_validated",
        "clinical_use_authorized",
        "publication_authorized",
    ):
        assert report[flag] is False
    for token in (
        _SECRET,
        "fictional-patient",
        "urn:uuid:",
        str(archive),
        *(str(p) for p in paths),
    ):
        assert token not in output.err + output.out
    assert set(tmp_path.iterdir()) == {archive, *paths}


@pytest.mark.parametrize(
    "edit",
    [
        lambda x: x.pop("meta"),
        lambda x: x["entry"][0]["resource"].update({"unreviewedPatientData": _SECRET}),
        lambda x: x["entry"][0]["resource"]["subject"].update(
            {"reference": "https://private.invalid/fhir/Patient/" + _SECRET}
        ),
    ],
)
def test_no_partial_success_or_patient_leak_when_later_source_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    edit,
) -> None:
    archive = _schema(tmp_path, monkeypatch)
    sources = _cases()
    edit(sources[1])
    args, paths = _cli(tmp_path, archive, sources)
    assert public_cli(args) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "verified_batch_contract_refused" in output.err
    assert _SECRET not in output.err
    assert str(paths[1]) not in output.err


def test_repeated_source_never_admitted_as_two_independent_bundles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _schema(tmp_path, monkeypatch)
    same = _cases()[0]
    with pytest.raises(SyntheticBatchAssessmentError, match="batch_assessment_contract_refused"):
        assess_synthetic_bundle_batch_offline(
            [same, copy.deepcopy(same)], archive, synthetic_only=True
        )


@pytest.mark.parametrize(
    "sources,marker",
    [
        ([], "batch_document_count_refused"),
        ([{}], "batch_document_count_refused"),
        ([{}] * 9, "batch_document_count_refused"),
        ([{}, None], "batch_source_type_refused"),
    ],
)
def test_api_explicit_admission_before_schema(
    sources,
    marker: str,
) -> None:
    with pytest.raises(SyntheticBatchAssessmentError, match=marker):
        assess_synthetic_bundle_batch_offline(sources, Path("never-loaded"), synthetic_only=True)


def test_api_refuses_no_explicit_synthetic_attestation() -> None:
    with pytest.raises(SyntheticBatchAssessmentError, match="batch_synthetic_attestation_required"):
        synthetic_bundle_batch_assessment_json(_cases(), Path("unused"), synthetic_only=False)


@pytest.mark.parametrize(
    "tokens",
    [
        [],
        ["--synthetic-only"],
        ["--synthetic-only", "--offline-r4-schema", "schema", "one"],
        ["--synthetic-only", "--offline-r4-schema", "schema", "--secret", "two"],
        ["--synthetic-only", "--offline-r4-schema", "schema", "one", "two", "--bad"],
        ["--synthetic-only", "--offline-r4-schema", "schema", *[str(i) for i in range(9)]],
        ["--offline-r4-schema", "schema", "one", "two"],
        ["--synthetic-only", "--synthetic-only", "schema", "one", "two"],
    ],
)
def test_cli_exact_argument_admission_without_echo(
    tokens: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert public_cli(["fhir", "batch-bundle-assess", *tokens]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.strip().endswith("explicit_synthetic_offline_batch_flags_required")
    assert "schema" not in output.err


def test_missing_second_source_refuses_without_first_source_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first = tmp_path / "fictional-first.json"
    first.write_text(json.dumps(_cases()[0]), encoding="utf-8")
    assert (
        public_cli(
            [
                "fhir",
                "batch-bundle-assess",
                "--synthetic-only",
                "--offline-r4-schema",
                str(tmp_path / "unused-official-schema.zip"),
                str(first),
                str(tmp_path / _SECRET),
            ]
        )
        == 1
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.strip().endswith("source_input_refused")
    assert _SECRET not in output.err


def test_invalid_official_schema_does_not_create_partial_batch_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = tmp_path / "not-official.zip"
    fake.write_bytes(b"NOT OFFICIAL HL7")
    args, _ = _cli(tmp_path, fake, _cases())
    assert public_cli(args) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "qualified_offline_schema_missing" in output.err


def test_help_is_explicit_about_partial_conformance_and_fictional_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert public_cli(["fhir", "batch-bundle-assess", "--help"]) == 0
    output = capsys.readouterr()
    assert "PARTIAL" not in output.out or "structural" in output.out.lower()
    assert "full FHIR R4" in output.out
    assert "FICTIONAL_BUNDLE_8" in output.out
    assert output.err == ""


def test_forged_diagnostic_cannot_escape_through_batch_even_if_prefix_looks_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import medscale.fhirkit.bundle_batch_assessment as batch

    archive = _schema(tmp_path, monkeypatch)
    original = batch.assess_synthetic_bundle_offline

    def fake_one(*args, **kwargs):
        document = original(*args, **kwargs)
        document["r4_operation_outcome"]["issue"][-1]["details"]["text"] += _SECRET
        return document

    monkeypatch.setattr(batch, "assess_synthetic_bundle_offline", fake_one)
    with pytest.raises(SyntheticBatchAssessmentError, match="batch_outcome_contract_refused") as e:
        batch.assess_synthetic_bundle_batch_offline(_cases(), archive, synthetic_only=True)
    assert _SECRET not in str(e.value)


def test_forged_extra_downstream_payload_key_is_never_passed_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import medscale.fhirkit.bundle_batch_assessment as batch

    archive = _schema(tmp_path, monkeypatch)
    original = batch.assess_synthetic_bundle_offline

    def fake_one(*args, **kwargs):
        report = original(*args, **kwargs)
        report["source_patient_payload"] = _SECRET
        return report

    monkeypatch.setattr(batch, "assess_synthetic_bundle_offline", fake_one)
    safe = batch.assess_synthetic_bundle_batch_offline(_cases(), archive, synthetic_only=True)
    assert _SECRET not in json.dumps(safe)
    assert all("source_patient_payload" not in item for item in safe["documents"])


def test_official_hl7_r4_401_schema_mixed_structural_result_when_opted_in() -> None:
    """No fake schema or pinned-version monkeypatch: actual official file only."""
    name = os.environ.get("MEDORIGIN_R4_OFFICIAL_SCHEMA_ZIP")
    if not name:
        pytest.skip("Exact official R4 schema ZIP must be explicitly supplied")
    archive = Path(name)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == _SHA
    assert version("jsonschema") == r4_schema.PINNED_JSONSCHEMA_VERSION
    first, second = _cases()
    second["entry"][0]["resource"]["valueString"] = 12345
    report = assess_synthetic_bundle_batch_offline([first, second], archive, synthetic_only=True)
    assert report["document_count"] == 2
    assert report["structural_not_validated_count"] == 1
    assert report["structural_invalid_count"] == 1
    assert [x["r4_structural_status"] for x in report["documents"]] == [
        "not_validated",
        "invalid",
    ]
    assert _SECRET not in json.dumps(report)
    assert report["fhir_r4_conformance_validated"] is False
    assert report["publication_authorized"] is False
