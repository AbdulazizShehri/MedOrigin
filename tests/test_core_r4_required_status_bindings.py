"""Source-backed exact FHIR R4 v4.0.1 required Encounter/Observation status codes.

All resources and identifiers are invented. This is a narrow local admission
gate, not full terminology/profile/FHIRPath validation, clinical evidence or
a PHI detector. Official codes:
https://hl7.org/fhir/R4/codesystem-encounter-status.html
https://hl7.org/fhir/R4/valueset-observation-status.html
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit.bundle import BundlePreflightError, inspect_synthetic_bundle
from medscale.fhirkit.bundle_diagnostics import rejected_synthetic_bundle_operation_outcome
from medscale.fhirkit.workspace_file_batch_demo import (
    SyntheticFileImportDemoError,
    run_fictional_file_batch_encrypted_demo,
)

_R4_ENCOUNTER_STATUSES = (
    "planned",
    "arrived",
    "triaged",
    "in-progress",
    "onleave",
    "finished",
    "cancelled",
    "entered-in-error",
    "unknown",
)
_R4_OBSERVATION_STATUSES = (
    "registered",
    "preliminary",
    "final",
    "amended",
    "corrected",
    "cancelled",
    "entered-in-error",
    "unknown",
)
_PRIVATE = "INVENTED_PATIENT_NAME_NEVER_TO_ECHO"
_P = "urn:uuid:00000000-0000-4000-8000-000000000002"
_E = "urn:uuid:00000000-0000-4000-8000-000000000003"


def _fixture() -> dict:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {
            "tag": [
                {
                    "system": "urn:medorigin:fixture-classification",
                    "code": "synthetic",
                }
            ]
        },
        "entry": [
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000001",
                "resource": {
                    "resourceType": "Observation",
                    "id": "fictional-observation-001",
                    "status": "final",
                    "code": {"text": "invented observation only"},
                    "subject": {"reference": _P},
                    "encounter": {"reference": _E},
                },
            },
            {
                "fullUrl": _P,
                "resource": {
                    "resourceType": "Patient",
                    "id": "fictional-patient-001",
                    "name": [{"text": _PRIVATE}],
                },
            },
            {
                "fullUrl": _E,
                "resource": {
                    "resourceType": "Encounter",
                    "id": "fictional-encounter-001",
                    "status": "finished",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                    },
                    "subject": {"reference": _P},
                },
            },
        ],
    }


def _change(kind: str, new_status: object) -> dict:
    source = _fixture()
    index = {"Encounter": 2, "Observation": 0}[kind]
    source["entry"][index]["resource"]["status"] = new_status
    return source


@pytest.mark.parametrize("status", _R4_ENCOUNTER_STATUSES)
def test_all_nine_exact_r4_encounter_codes_are_admitted_locally(status: str) -> None:
    report = inspect_synthetic_bundle(_change("Encounter", status))
    assert report["local_references_checked"] == 3
    assert report["full_fhir_r4_conformance_established"] is False
    assert report["terminology_profiles_invariants_verified"] is False
    assert report["clinical_use_authorized"] is False
    assert _PRIVATE not in json.dumps(report)


@pytest.mark.parametrize("status", _R4_OBSERVATION_STATUSES)
def test_all_eight_exact_r4_observation_codes_are_admitted_locally(status: str) -> None:
    report = inspect_synthetic_bundle(_change("Observation", status))
    assert report["local_references_checked"] == 3
    assert report["full_fhir_r4_conformance_established"] is False
    assert report["clinical_use_authorized"] is False


@pytest.mark.parametrize(
    ("kind", "status"),
    [
        ("Encounter", "completed"),  # R5 code, NOT R4 v4.0.1
        ("Encounter", "on-hold"),  # R5 code, NOT R4 v4.0.1
        ("Encounter", "discharged"),  # R5 code, NOT R4 v4.0.1
        ("Encounter", "finished "),
        ("Encounter", "FINISHED"),
        ("Encounter", "nonexistent-status"),
        ("Encounter", "finished\\n"),
        ("Observation", "completed"),
        ("Observation", "FINAL"),
        ("Observation", "final "),
        ("Observation", "unknown-status"),
        ("Observation", "registered\\x00"),
        ("Observation", "ｆｉｎａｌ"),  # noqa: RUF001
        ("Observation", "réel"),
    ],
)
def test_non_r4_exact_status_refused_without_patient_details(kind: str, status: str) -> None:
    expected = (
        "encounter_status_not_in_r4_required_codes"
        if kind == "Encounter"
        else "observation_status_not_in_r4_required_codes"
    )
    with pytest.raises(BundlePreflightError, match=expected) as error:
        inspect_synthetic_bundle(_change(kind, status))
    assert str(error.value) == expected
    assert _PRIVATE not in str(error.value)


@pytest.mark.parametrize("kind", ["Encounter", "Observation"])
@pytest.mark.parametrize("status", [None, 1, True, [], {}, ["final"]])
def test_missing_or_nontext_status_preserves_existing_subset_error(
    kind: str, status: object
) -> None:
    expected = {
        "Encounter": "incomplete_encounter_subset",
        "Observation": "incomplete_observation_subset",
    }[kind]
    with pytest.raises(BundlePreflightError, match=expected):
        inspect_synthetic_bundle(_change(kind, status))


@pytest.mark.parametrize("kind", ["Encounter", "Observation"])
def test_unknown_status_has_fixed_redacted_operation_outcome(kind: str) -> None:
    invalid = _change(kind, "unsafe-patient-status-" + _PRIVATE)
    expected = {
        "Encounter": "encounter_status_not_in_r4_required_codes",
        "Observation": "observation_status_not_in_r4_required_codes",
    }[kind]
    outcome = rejected_synthetic_bundle_operation_outcome(invalid, BundlePreflightError(expected))
    assert outcome["resourceType"] == "OperationOutcome"
    assert [issue["severity"] for issue in outcome["issue"]] == ["error", "warning"]
    assert "FHIR R4 v4.0.1" in outcome["issue"][0]["details"]["text"]
    assert _PRIVATE not in json.dumps(outcome)
    assert "urn:uuid:" not in json.dumps(outcome)


@pytest.mark.parametrize("kind", ["Encounter", "Observation"])
def test_actual_public_file_cli_refuses_bad_r4_status_without_json_or_path(
    kind: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / f"{_PRIVATE}-{kind}.json"
    file.write_text(json.dumps(_change(kind, "invalid-status")), encoding="utf-8")
    assert public_cli(["fhir", "bundle-preflight", str(file), "--synthetic-only"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "status_not_in_r4_required_codes" in captured.err
    assert _PRIVATE not in captured.out + captured.err
    assert str(file) not in captured.err
    assert list(tmp_path.iterdir()) == [file]


def test_bad_second_file_refuses_entire_encrypted_batch_before_any_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as importer

    def forbid_storage(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("encrypted Workspace must NEVER be allocated")

    monkeypatch.setattr(importer, "TemporaryDirectory", forbid_storage)
    good = _fixture()
    invalid = _change("Observation", "unsafe-status")
    with pytest.raises(
        SyntheticFileImportDemoError, match="fictional_import_source_preflight_refused"
    ) as error:
        run_fictional_file_batch_encrypted_demo(
            [good, invalid], synthetic_only=True, ephemeral_demo=True
        )
    assert _PRIVATE not in str(error.value)


def test_source_entry_order_must_not_bypass_required_status_binding() -> None:
    source = _change("Encounter", "completed")
    source["entry"].reverse()
    with pytest.raises(BundlePreflightError, match="encounter_status_not_in_r4_required_codes"):
        inspect_synthetic_bundle(source)
