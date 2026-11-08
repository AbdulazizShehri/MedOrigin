"""End-to-end synthetic FHIR Bundle preflight through shipped Core CLI."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from medscale.cli import fhir as fhir_cli
from medscale.cli import main as public_cli_main
from medscale.fhirkit.bundle import BundlePreflightError, inspect_synthetic_bundle

PRIVATE_SENTINEL = "NEVER_ECHO_SYNTHETIC_PERSON_NAME"
MARKER = {
    "system": "urn:medorigin:fixture-classification",
    "code": "synthetic",
}


def _bundle() -> dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {"tag": [MARKER]},
        "entry": [
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000001",
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-001",
                    "status": "final",
                    "code": {"text": "synthetic-code"},
                    "subject": {"reference": "urn:uuid:00000000-0000-4000-8000-000000000002"},
                    "encounter": {"reference": "urn:uuid:00000000-0000-4000-8000-000000000003"},
                },
            },
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000002",
                "resource": {
                    "resourceType": "Patient",
                    "id": "pat-001",
                    "active": True,
                    "name": [{"text": PRIVATE_SENTINEL}],
                },
            },
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000003",
                "resource": {
                    "resourceType": "Encounter",
                    "id": "enc-001",
                    "status": "finished",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                    },
                    "subject": {"reference": "urn:uuid:00000000-0000-4000-8000-000000000002"},
                },
            },
        ],
    }


def _write(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "synthetic-bundle.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_forward_reference_multi_resource_core_preflight() -> None:
    summary: dict[str, Any] = inspect_synthetic_bundle(_bundle())
    assert summary["status"] == "local_relationship_preflight_only"
    assert summary["resource_count"] == 3
    assert summary["resource_counts"] == {"Encounter": 1, "Observation": 1, "Patient": 1}
    assert summary["local_references_checked"] == 3
    assert summary["payload_content_included"] is False
    assert summary["input_persisted"] is False
    assert summary["network_access_performed"] is False
    assert summary["full_fhir_r4_conformance_established"] is False
    assert summary["clinical_use_authorized"] is False
    assert PRIVATE_SENTINEL not in json.dumps(summary)
    assert "pat-001" not in json.dumps(summary)
    assert len(summary["source_content_sha256"]) == 64


def test_preflight_is_deterministic_under_object_key_reordering() -> None:
    payload = _bundle()
    reordered = json.loads(json.dumps(payload, sort_keys=True))
    assert inspect_synthetic_bundle(payload) == inspect_synthetic_bundle(reordered)


@pytest.mark.parametrize(
    "mutate, expected_error",
    [
        (lambda b: b.pop("meta"), "explicit_synthetic_fixture_marker_required"),
        (lambda b: b.update({"type": "transaction"}), "only_collection_bundle_supported"),
        (lambda b: b.update({"type": "document"}), "only_collection_bundle_supported"),
        (lambda b: b.update({"entry": []}), "bundle_entry_count_out_of_range"),
        (lambda b: b.update({"total": 3}), "unreviewed_bundle_field_refused"),
        (
            lambda b: b["entry"][0].update({"request": {"method": "POST"}}),
            "bundle_entry_structure_refused",
        ),
        (
            lambda b: b["entry"][0].update({"fullUrl": "https://ehr.invalid/1"}),
            "nonlocal_or_invalid_fullurl",
        ),
        (
            lambda b: b["entry"][0].update({"fullUrl": "urn:uuid:BAD"}),
            "nonlocal_or_invalid_fullurl",
        ),
        (
            lambda b: b["entry"][0].update({"fullUrl": b["entry"][1]["fullUrl"]}),
            "duplicate_bundle_fullurl",
        ),
        (
            lambda b: b["entry"][0]["resource"].update({"id": "bad/id"}),
            "invalid_bundle_resource_id",
        ),
        (
            lambda b: b["entry"][0]["resource"].update({"resourceType": "UnknownThing"}),
            "unsupported_bundle_resource_type",
        ),
        (
            lambda b: b["entry"][0]["resource"].update({"basedOn": []}),
            "unreviewed_bundle_resource_field_refused",
        ),
        (
            lambda b: b["entry"][0]["resource"].update(
                {"subject": {"reference": "urn:uuid:00000000-0000-4000-8000-000000000099"}}
            ),
            "unresolved_local_patient_reference",
        ),
        (
            lambda b: b["entry"][0]["resource"].update(
                {"subject": {"reference": "https://remote.invalid/p"}}
            ),
            "external_or_invalid_reference_refused",
        ),
        (
            lambda b: b["entry"][0]["resource"].update(
                {"encounter": {"reference": "urn:uuid:00000000-0000-4000-8000-000000000098"}}
            ),
            "unresolved_local_encounter_reference",
        ),
        (lambda b: b["entry"][0]["resource"].pop("code"), "incomplete_observation_subset"),
        (lambda b: b["entry"][2]["resource"].pop("class"), "incomplete_encounter_subset"),
        (
            lambda b: b["entry"][2]["resource"].update({"subject": None}),
            "required_local_reference_missing_or_malformed",
        ),
        (
            lambda b: b["entry"][0]["resource"].update({"meta": "untrusted"}),
            "invalid_bundle_resource_meta",
        ),
        (
            lambda b: b["entry"][1]["resource"].update({"id": "pat-001" * 25}),
            "invalid_bundle_resource_id",
        ),
    ],
)
def test_fail_closed_on_unreviewed_or_broken_bundle(
    mutate: Callable[[dict[str, Any]], object], expected_error: str
) -> None:
    b = _bundle()
    mutate(b)
    with pytest.raises(BundlePreflightError, match=expected_error):
        inspect_synthetic_bundle(b)


def test_duplicate_resource_identity_refused_even_with_distinct_fullurls() -> None:
    b = _bundle()
    b["entry"].append(copy.deepcopy(b["entry"][1]))
    b["entry"][-1]["fullUrl"] = "urn:uuid:00000000-0000-4000-8000-000000000004"
    with pytest.raises(BundlePreflightError, match="duplicate_bundle_resource_identity"):
        inspect_synthetic_bundle(b)


def test_excessive_entry_count_fails_before_scanning_contents() -> None:
    b = _bundle()
    b["entry"] = [copy.deepcopy(b["entry"][1])] * 129
    with pytest.raises(BundlePreflightError, match="bundle_entry_count_out_of_range"):
        inspect_synthetic_bundle(b)


def test_real_public_cli_single_command_returns_redacted_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _write(tmp_path, _bundle())
    assert public_cli_main(["fhir", "bundle-preflight", str(source), "--synthetic-only"]) == 0
    captured = capsys.readouterr()
    receipt = json.loads(captured.out)
    assert receipt == inspect_synthetic_bundle(_bundle())
    assert not captured.err
    assert PRIVATE_SENTINEL not in captured.out
    assert "pat-001" not in captured.out
    assert list(tmp_path.iterdir()) == [source]


def test_bundle_command_must_require_explicit_synthetic_attestation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _write(tmp_path, _bundle())
    assert fhir_cli.main(["bundle-preflight", str(source)]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "synthetic_only_attestation_required" in captured.err
    assert PRIVATE_SENTINEL not in captured.err


def test_refused_bundle_has_no_report_or_payload_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = _bundle()
    payload["entry"][0]["resource"]["subject"] = {
        "reference": "urn:uuid:00000000-0000-4000-8000-000000000099"
    }
    source = _write(tmp_path, payload)
    assert fhir_cli.main(["bundle-preflight", str(source), "--synthetic-only"]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "unresolved_local_patient_reference" in captured.err
    assert PRIVATE_SENTINEL not in captured.err
    assert list(tmp_path.iterdir()) == [source]


def test_duplicate_input_keys_rejected_by_shared_core_parser(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "ambiguous-bundle.json"
    source.write_text('{"resourceType":"Bundle","resourceType":"Patient"}', encoding="utf-8")
    assert fhir_cli.main(["bundle-preflight", str(source), "--synthetic-only"]) == 1
    captured = capsys.readouterr()
    assert "duplicate_json_key" in captured.err
    assert not captured.out
    assert list(tmp_path.iterdir()) == [source]


def test_legacy_single_resource_validation_contract_is_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "fictional.json"
    path.write_text('{"resourceType":"Patient","id":"synthetic"}', encoding="utf-8")
    output = tmp_path / "reports"
    assert public_cli_main(["fhir", "validate", str(path), "--output-dir", str(output)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "not_validated"
    assert len(list(output.rglob("report.json"))) == 1


def test_committed_fictional_bundle_example_runs_through_public_cli(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "synthetic_fhir_bundle_preflight"
        / "fictional_bundle.json"
    )
    assert public_cli_main(["fhir", "bundle-preflight", str(fixture), "--synthetic-only"]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["resource_count"] == 3
    assert receipt["local_references_checked"] == 3
    assert receipt["full_fhir_r4_conformance_established"] is False
    assert receipt["input_persisted"] is False


def test_same_bundle_reference_must_match_target_resource_type() -> None:
    bundle = _bundle()
    # A local UUID exists, but it points to Encounter rather than Patient.
    bundle["entry"][0]["resource"]["subject"] = {
        "reference": "urn:uuid:00000000-0000-4000-8000-000000000003"
    }
    with pytest.raises(BundlePreflightError, match="local_reference_target_type_mismatch"):
        inspect_synthetic_bundle(bundle)


def test_relative_reference_is_not_silently_resolved_against_urn_uuid_fullurl() -> None:
    bundle = _bundle()
    bundle["entry"][0]["resource"]["subject"] = {"reference": "Patient/pat-001"}
    with pytest.raises(BundlePreflightError, match="external_or_invalid_reference_refused"):
        inspect_synthetic_bundle(bundle)
