"""Core-only, synthetic R4 structural-schema option; never clinical conformance."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

from medscale.cli import fhir as fhir_cli
from medscale.fhirkit import r4_schema
from medscale.fhirkit.errors import FhirMissingDependencyError, UnavailableValidatorError


def _fake_r4_schema_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Test a local, artificial schema, NEVER an approved official fixture."""
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
    archive = tmp_path / "synthetic-test-only.zip"
    with zipfile.ZipFile(archive, mode="w") as z:
        z.writestr(r4_schema.OFFICIAL_R4_SCHEMA_MEMBER, json.dumps(schema))
    raw = archive.read_bytes()
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_ZIP_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_BYTES", len(json.dumps(schema).encode()))
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_DEFINITIONS", 1)
    return archive


def test_pinned_official_archive_sha256_from_qa_906() -> None:
    assert (
        r4_schema.OFFICIAL_R4_SCHEMA_ZIP_SHA256
        == "75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6"
    )
    assert r4_schema.OFFICIAL_R4_SCHEMA_DEFINITIONS == 680


@pytest.mark.parametrize("value", [b"", b"fake-r4-schema", b"PK\\x03\\x04"])
def test_refuse_nonofficial_archive(tmp_path: Path, value: bytes) -> None:
    path = tmp_path / "fake.zip"
    path.write_bytes(value)
    with pytest.raises(UnavailableValidatorError, match="sha256_mismatch"):
        r4_schema._load_official_r4_json_schema(path)


def test_refuse_missing_archive(tmp_path: Path) -> None:
    with pytest.raises(UnavailableValidatorError, match="missing_or_symlink"):
        r4_schema._load_official_r4_json_schema(tmp_path / "missing.zip")


def test_refuse_directory_as_archive(tmp_path: Path) -> None:
    with pytest.raises(UnavailableValidatorError, match="missing_or_symlink"):
        r4_schema._load_official_r4_json_schema(tmp_path)


def test_refuse_overlarge_archive_before_read(tmp_path: Path) -> None:
    path = tmp_path / "large.zip"
    with path.open("wb") as fp:
        fp.truncate(r4_schema.MAX_ARCHIVE_BYTES + 1)
    with pytest.raises(UnavailableValidatorError, match="too_large"):
        r4_schema._load_official_r4_json_schema(path)


def test_missing_schema_zip_cli_does_not_write_report(tmp_path: Path) -> None:
    source = tmp_path / "synthetic.json"
    source.write_text('{"resourceType":"Patient","id":"fictional"}', encoding="utf-8")
    output = tmp_path / "reports"
    assert (
        fhir_cli.main(
            [
                str(source),
                "--offline-r4-schema",
                str(tmp_path / "absent.zip"),
                "--output-dir",
                str(output),
            ]
        )
        == 2
    )
    assert not output.exists()


@pytest.mark.skipif(
    importlib.util.find_spec("jsonschema") is None,
    reason="optional jsonschema package intentionally absent from base Core",
)
def test_synthetic_schema_proves_partial_not_validated_and_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _fake_r4_schema_archive(tmp_path, monkeypatch)
    monkeypatch.setattr(r4_schema, "version", lambda name: r4_schema.PINNED_JSONSCHEMA_VERSION)
    accepted = r4_schema.validate_offline_r4_json_structure(
        {"resourceType": "Patient", "id": "synthetic", "active": True}, archive
    )
    assert accepted.status == "not_validated"
    assert accepted.errors == ()
    assert accepted.warnings and "NOT full FHIR R4" in accepted.warnings[0]
    assert accepted.validator_name == "hl7-fhir-r4-json-schema-structural-only"

    wrong_type = r4_schema.validate_offline_r4_json_structure(
        {"resourceType": "Patient", "id": "synthetic", "active": "true"}, archive
    )
    assert wrong_type.status == "invalid"
    assert wrong_type.errors
    unknown = r4_schema.validate_offline_r4_json_structure(
        {"resourceType": "UnknownFictionalResource", "id": "synthetic"}, archive
    )
    assert unknown.status == "invalid"
    assert unknown.errors


@pytest.mark.skipif(
    importlib.util.find_spec("jsonschema") is None,
    reason="optional jsonschema package intentionally absent from base Core",
)
def test_synthetic_cli_report_persists_without_full_valid_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = _fake_r4_schema_archive(tmp_path, monkeypatch)
    monkeypatch.setattr(r4_schema, "version", lambda name: r4_schema.PINNED_JSONSCHEMA_VERSION)
    source = tmp_path / "fictional.json"
    source.write_text('{"resourceType":"Patient","id":"synthetic","active":true}', encoding="utf-8")
    output = tmp_path / "reports"
    assert (
        fhir_cli.main(
            [str(source), "--offline-r4-schema", str(archive), "--output-dir", str(output)]
        )
        == 2
    )
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "not_validated"
    assert printed["errors"] == []
    reports = list(output.rglob("report.json"))
    assert len(reports) == 1
    assert json.loads(reports[0].read_text(encoding="utf-8"))["status"] == "not_validated"


@pytest.mark.skipif(
    importlib.util.find_spec("jsonschema") is None,
    reason="optional jsonschema package intentionally absent from base Core",
)
def test_unqualified_jsonschema_version_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = _fake_r4_schema_archive(tmp_path, monkeypatch)
    monkeypatch.setattr(r4_schema, "version", lambda name: "999.0")
    with pytest.raises(FhirMissingDependencyError, match="version_not_qualified"):
        r4_schema.validate_offline_r4_json_structure({"resourceType": "Patient"}, archive)


def test_actual_official_r4_zip_opt_in_only() -> None:
    """Optional local E2E: never download a schema or invent full conformance."""
    import os

    archive_path = os.environ.get("MEDORIGIN_OFFICIAL_R4_SCHEMA_ZIP")
    if not archive_path:
        pytest.skip("official offline schema not supplied by local QA")
    archive = Path(archive_path)
    accepted = r4_schema.validate_offline_r4_json_structure(
        {"resourceType": "Patient", "id": "fictional", "active": True}, archive
    )
    assert accepted.status == "not_validated"
    assert accepted.errors == ()
    for invalid in (
        {"resourceType": "Patient", "id": "fictional", "active": "true"},
        {"resourceType": "UnknownFictionalResource", "id": "fictional"},
        {"resourceType": "Observation", "id": "fictional"},
    ):
        report = r4_schema.validate_offline_r4_json_structure(invalid, archive)
        assert report.status == "invalid"
        assert report.errors
    # Real blind spot observed in the official published FHIR R4 JSON Schema:
    # schema acceptance of this incomplete resource is NOT clinical validity.
    incomplete = r4_schema.validate_offline_r4_json_structure(
        {"resourceType": "StructureDefinition", "id": "fictional"}, archive
    )
    assert incomplete.status == "not_validated"
    assert incomplete.errors == ()
    assert "incomplete StructureDefinition" in incomplete.warnings[0]
