"""One real Core command: synthetic local Bundle relationships + official R4 shape.

The generated result deliberately does NOT claim full FHIR R4, profiles,
terminology, FHIRPath invariants, clinical safety, EHR use or PHI clearance.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import zipfile
from pathlib import Path

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit import r4_schema
from medscale.fhirkit.bundle_assessment import (
    SyntheticBundleAssessmentError,
    assess_synthetic_bundle_offline,
    synthetic_bundle_assessment_json,
)
from medscale.fhirkit.workspace_demo import _fictional_bundle

NEVER_ECHO = "Fictional Example Only"


def _test_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, impossible: bool = False
) -> Path:
    """Fake source for unit testing only; never a qualified official schema."""
    schema = {
        "$schema": r4_schema.OFFICIAL_R4_DRAFT,
        "id": r4_schema.OFFICIAL_R4_SCHEMA_ID,
        "definitions": {
            "Bundle": {
                "type": "object",
                "required": ["resourceType", "type", "entry"],
                "properties": {
                    "resourceType": {"const": "Bundle"},
                    "type": {"const": "document" if impossible else "collection"},
                    "entry": {"type": "array", "minItems": 1},
                    "meta": {"type": "object"},
                },
                "additionalProperties": False,
            }
        },
        "$ref": "#/definitions/Bundle",
    }
    encoded = json.dumps(schema).encode()
    archive = tmp_path / "fictional-unit-test-r4-zip.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(r4_schema.OFFICIAL_R4_SCHEMA_MEMBER, encoded)
    monkeypatch.setattr(
        r4_schema,
        "OFFICIAL_R4_SCHEMA_ZIP_SHA256",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_BYTES", len(encoded))
    monkeypatch.setattr(r4_schema, "OFFICIAL_R4_SCHEMA_DEFINITIONS", 1)
    monkeypatch.setattr(r4_schema, "version", lambda _: r4_schema.PINNED_JSONSCHEMA_VERSION)
    return archive


def _source(tmp_path: Path, obj: dict | None = None) -> Path:
    path = tmp_path / "synthetic-case.json"
    path.write_text(json.dumps(obj if obj is not None else _fictional_bundle()), encoding="utf-8")
    return path


def _cli(source: Path, archive: Path) -> list[str]:
    return [
        "fhir",
        "bundle-assess",
        "--synthetic-only",
        "--offline-r4-schema",
        str(archive),
        str(source),
    ]


@pytest.mark.skipif(
    importlib.util.find_spec("jsonschema") is None,
    reason="optional pinned jsonschema not installed",
)
@pytest.mark.parametrize("impossible", [False, True])
def test_real_partial_dual_result_is_source_bound_and_never_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, impossible: bool
) -> None:
    archive = _test_schema(tmp_path, monkeypatch, impossible=impossible)
    payload = _fictional_bundle()
    receipt = assess_synthetic_bundle_offline(payload, archive, synthetic_only=True)
    assert receipt["schema"] == "medorigin-synthetic-fhir-bundle-dual-assessment/v1"
    assert receipt["status"] == "SYNTHETIC_R4_BUNDLE_PRECHECK_ONLY"
    assert receipt["resource_count"] == 3
    assert receipt["resource_counts"] == {"Encounter": 1, "Observation": 1, "Patient": 1}
    assert receipt["local_references_checked"] == 3
    assert receipt["synthetic_marker_verified_as_assertion_only"] is True
    assert len(receipt["source_content_sha256"]) == 64
    assert receipt["relationship_status"] == "local_relationship_preflight_only"
    assert receipt["r4_structural_status"] == ("invalid" if impossible else "not_validated")
    issues = receipt["r4_operation_outcome"]["issue"]
    assert [i["severity"] for i in issues] == (["error", "warning"] if impossible else ["warning"])
    assert receipt["official_r4_archive_sha256"] == (
        "75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6"
    )
    for key in (
        "payload_included",
        "output_persisted",
        "network_access_performed",
        "fhir_r4_conformance_validated",
        "terminology_profiles_invariants_verified",
        "clinical_use_authorized",
        "publication_authorized",
    ):
        assert receipt[key] is False
    dumped = synthetic_bundle_assessment_json(payload, archive, synthetic_only=True)
    assert NEVER_ECHO not in dumped
    assert "fictional-patient-001" not in dumped
    assert "urn:uuid:" not in dumped
    assert "not_validated" in dumped or "invalid" in dumped
    assert json.loads(dumped) == receipt


@pytest.mark.skipif(
    importlib.util.find_spec("jsonschema") is None,
    reason="optional pinned jsonschema not installed",
)
def test_real_public_dispatcher_both_outcomes_exit_nonzero_no_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _source(tmp_path)
    archive = _test_schema(tmp_path, monkeypatch)
    assert public_cli(_cli(source, archive)) == 2
    out = capsys.readouterr()
    receipt = json.loads(out.out)
    assert receipt["r4_structural_status"] == "not_validated"
    assert out.err == ""
    assert str(source) not in out.out
    assert str(archive) not in out.out
    assert NEVER_ECHO not in out.out
    assert sorted(tmp_path.iterdir()) == sorted([source, archive])
    archive = _test_schema(tmp_path, monkeypatch, impossible=True)
    assert public_cli(_cli(source, archive)) == 2
    out = capsys.readouterr()
    receipt = json.loads(out.out)
    assert receipt["r4_structural_status"] == "invalid"
    assert [i["code"] for i in receipt["r4_operation_outcome"]["issue"]] == [
        "structure",
        "informational",
    ]
    assert NEVER_ECHO not in out.out


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--synthetic-only"],
        ["--offline-r4-schema", "private", "source"],
        ["--synthetic-only", "--offline-r4-schema", "private"],
        ["--synthetic-only", "--offline-r4-schema", "private", "--bad"],
        ["--synthetic-only", "--offline-r4-schema", "--bad", "source"],
        ["--synthetic-only", "--offline-r4-schema", "private", "source", "extra"],
        ["--synthetic-only", "--synthetic-only", "private", "source"],
    ],
)
def test_exact_flags_required_no_input_echo(
    capsys: pytest.CaptureFixture[str], args: list[str]
) -> None:
    assert public_cli(["fhir", "bundle-assess", *args]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.strip().endswith("explicit_synthetic_offline_schema_flags_required")
    assert "private" not in output.err


def test_missing_or_unreadable_input_refuses_no_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / NEVER_ECHO
    archive = tmp_path / "schema.zip"
    assert public_cli(_cli(source, archive)) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "source_input_refused" in output.err
    assert NEVER_ECHO not in output.err


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b.pop("meta"),
        lambda b: b["entry"][0]["resource"]["subject"].update(
            reference="https://private.example/fhir/Patient/secret"
        ),
        lambda b: b["entry"][0]["resource"].update({"diagnosticReport": NEVER_ECHO}),
        lambda b: b["entry"][0]["resource"]["subject"].update(
            reference="urn:uuid:00000000-0000-4000-8000-000000000099"
        ),
        lambda b: b["entry"][1]["resource"].update(
            {"resourceType": "UnknownResourceWithPrivateIdentifier"}
        ),
    ],
)
def test_failed_relationship_check_never_runs_fake_validator_or_reports_patient(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mutate
) -> None:
    payload = _fictional_bundle()
    mutate(payload)
    source = _source(tmp_path, payload)
    archive = tmp_path / "does-not-exist.zip"
    assert public_cli(_cli(source, archive)) == 2
    result = capsys.readouterr()
    if "meta" not in payload:
        # Without the exact synthetic fixture marker, do not produce
        # a FHIR-looking outcome from unknown/unapproved source data.
        assert result.out == ""
        assert "relationship_preflight_refused" in result.err
    else:
        assert result.err == ""
        issue = json.loads(result.out)
        assert issue["resourceType"] == "OperationOutcome"
        assert [item["severity"] for item in issue["issue"]] == ["error", "warning"]
        assert [item["code"] for item in issue["issue"]] == ["structure", "informational"]
        assert set(issue) == {"resourceType", "issue"}
    assert NEVER_ECHO not in result.err + result.out
    assert "fictional-patient-001" not in result.out
    assert "private.example" not in result.out
    assert sorted(tmp_path.iterdir()) == [source]


def test_unqualified_official_archive_refuses_before_any_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _source(tmp_path)
    archive = tmp_path / "not-approved.zip"
    archive.write_bytes(b"not official HL7")
    assert public_cli(_cli(source, archive)) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "qualified_offline_schema_missing" in result.err
    assert NEVER_ECHO not in result.err
    assert not list(tmp_path.rglob("report.json"))


def test_direct_api_refuses_missing_synthetic_attestation() -> None:
    with pytest.raises(SyntheticBundleAssessmentError):
        assess_synthetic_bundle_offline(
            _fictional_bundle(), Path("not-an-official.zip"), synthetic_only=False
        )


def test_duplicate_source_json_key_is_rejected_before_dual_processing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "ambiguous.json"
    source.write_text(
        '{"resourceType":"Bundle","resourceType":"Patient","name":"' + NEVER_ECHO + '"}',
        encoding="utf-8",
    )
    assert public_cli(_cli(source, tmp_path / "schema.zip")) == 1
    result = capsys.readouterr()
    assert result.out == ""
    assert "source_input_refused" in result.err
    assert NEVER_ECHO not in result.err


def test_help_is_nonclinical_and_does_not_read_any_source(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert public_cli(["fhir", "bundle-assess", "--help"]) == 0
    result = capsys.readouterr()
    assert "synthetic-only" in result.out
    assert "NOT full FHIR/clinical validation" in result.out
    assert result.err == ""


def test_official_hl7_schema_opt_in_with_hardcoded_fictional_bundle() -> None:
    path = os.environ.get("MEDORIGIN_OFFICIAL_R4_SCHEMA_ZIP")
    if not path:
        pytest.skip("official offline R4 schema must be explicitly supplied")
    archive = Path(path)
    result = assess_synthetic_bundle_offline(_fictional_bundle(), archive, synthetic_only=True)
    assert result["r4_structural_status"] == "not_validated"
    assert result["r4_operation_outcome"]["issue"][-1]["severity"] == "warning"
    assert result["fhir_r4_conformance_validated"] is False
    assert result["clinical_use_authorized"] is False
    # A FHIR field that the narrow relationship preflight deliberately does
    # not type-check must still be caught by the independently qualified
    # official R4 Bundle JSON Schema. No false preflight equivalence.
    structurally_wrong = copy.deepcopy(_fictional_bundle())
    structurally_wrong["entry"][1]["resource"]["active"] = "true"
    failed = assess_synthetic_bundle_offline(structurally_wrong, archive, synthetic_only=True)
    assert failed["relationship_status"] == "local_relationship_preflight_only"
    assert failed["r4_structural_status"] == "invalid"
    assert failed["r4_operation_outcome"]["issue"][0]["severity"] == "error"
    assert failed["fhir_r4_conformance_validated"] is False
    assert NEVER_ECHO not in json.dumps(failed)
