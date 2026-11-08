"""Core local FHIR invariant: Observation.encounter cannot belong to another Patient.

All resources here are completely fabricated; zero external FHIR/EHR or PHI.
This is a narrow, not-full-R4 relationship check on admitted local UUIDs.
"""

from __future__ import annotations

# mypy: disable-error-code="import-not-found"
# The Workspace package under apps/workspace is deliberately outside strict mypy's
# file set while Issue #464 item 1 is open; it is imported at runtime. Declaring
# the missing import here keeps that deferral explicit.
import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn, cast

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit.bundle import BundlePreflightError, inspect_synthetic_bundle
from medscale.fhirkit.bundle_diagnostics import rejected_synthetic_bundle_operation_outcome
from medscale.fhirkit.workspace_demo import _fictional_bundle
from medscale.fhirkit.workspace_ingest import (
    SyntheticWorkspaceImportError,
    ingest_synthetic_bundle_atomic,
)

_SENSITIVE = "INVENTED_PATIENT_IDENTITY_NEVER_OUTPUT"


def _two_patients() -> dict[str, Any]:
    """A valid, patient-separated 6-resource local synthetic FHIR Bundle."""
    result = cast(dict[str, Any], _fictional_bundle())
    patient2 = copy.deepcopy(result["entry"][1])
    patient2["fullUrl"] = "urn:uuid:00000000-0000-4000-8000-000000000004"
    patient2["resource"]["id"] = "fictional-patient-002"
    patient2["resource"]["name"][0]["text"] = _SENSITIVE

    encounter2 = copy.deepcopy(result["entry"][2])
    encounter2["fullUrl"] = "urn:uuid:00000000-0000-4000-8000-000000000005"
    encounter2["resource"]["id"] = "fictional-encounter-002"
    encounter2["resource"]["subject"]["reference"] = patient2["fullUrl"]

    observation2 = copy.deepcopy(result["entry"][0])
    observation2["fullUrl"] = "urn:uuid:00000000-0000-4000-8000-000000000006"
    observation2["resource"]["id"] = "fictional-observation-002"
    observation2["resource"]["subject"]["reference"] = patient2["fullUrl"]
    observation2["resource"]["encounter"]["reference"] = encounter2["fullUrl"]

    result["entry"].extend([patient2, encounter2, observation2])
    return result


def _mismatched() -> dict[str, Any]:
    bundle = _two_patients()
    # The Observation belongs to patient #1 but refers to patient #2's
    # Encounter. Both resources exist; type-only reference checking passes.
    bundle["entry"][-1]["resource"]["subject"]["reference"] = bundle["entry"][1]["fullUrl"]
    return bundle


def test_two_patients_each_have_matching_encounter_and_observation() -> None:
    result = inspect_synthetic_bundle(_two_patients())
    assert result["resource_count"] == 6
    assert result["resource_counts"] == {"Encounter": 2, "Observation": 2, "Patient": 2}
    assert result["local_references_checked"] == 6
    assert result["status"] == "local_relationship_preflight_only"
    assert result["full_fhir_r4_conformance_established"] is False
    assert result["clinical_use_authorized"] is False
    assert _SENSITIVE not in json.dumps(result)
    assert "fictional-patient-002" not in json.dumps(result)


def test_local_forward_reference_order_does_not_change_patient_invariant() -> None:
    good = _two_patients()
    forward = copy.deepcopy(good)
    forward["entry"].reverse()
    assert inspect_synthetic_bundle(forward)["local_references_checked"] == 6
    bad = _mismatched()
    bad["entry"].reverse()
    with pytest.raises(BundlePreflightError, match=r"^observation_encounter_patient_mismatch$"):
        inspect_synthetic_bundle(bad)


@pytest.mark.parametrize(
    "transform",
    [
        lambda x: x,
        lambda x: {**x, "entry": list(reversed(x["entry"]))},
        lambda x: {
            **x,
            "entry": [
                x["entry"][2],
                x["entry"][5],
                x["entry"][0],
                x["entry"][1],
                x["entry"][4],
                x["entry"][3],
            ],
        },
    ],
)
def test_multi_patient_mismatch_is_fixed_redacted_error(
    transform: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    bad = transform(_mismatched())
    with pytest.raises(
        BundlePreflightError, match=r"^observation_encounter_patient_mismatch$"
    ) as error:
        inspect_synthetic_bundle(bad)
    assert _SENSITIVE not in str(error.value)


def test_changing_encounter_subject_also_refuses_a_previously_good_observation() -> None:
    good = _two_patients()
    # Observation #1 refers to Encounter #1, which now belongs to patient #2.
    good["entry"][2]["resource"]["subject"]["reference"] = good["entry"][3]["fullUrl"]
    with pytest.raises(BundlePreflightError, match="observation_encounter_patient_mismatch"):
        inspect_synthetic_bundle(good)


def test_no_encounter_reference_remains_a_supported_narrow_subset() -> None:
    good = _two_patients()
    good["entry"][5]["resource"].pop("encounter")
    good["entry"][5]["resource"]["subject"]["reference"] = good["entry"][1]["fullUrl"]
    receipt = inspect_synthetic_bundle(good)
    assert receipt["local_references_checked"] == 5


def test_rejected_operation_outcome_has_fixed_text_without_patient_identity() -> None:
    source = _mismatched()
    failure = BundlePreflightError("observation_encounter_patient_mismatch")
    outcome: Any = rejected_synthetic_bundle_operation_outcome(source, failure)
    assert outcome["resourceType"] == "OperationOutcome"
    assert [x["severity"] for x in outcome["issue"]] == ["error", "warning"]
    assert "different local Patients" in outcome["issue"][0]["details"]["text"]
    assert _SENSITIVE not in json.dumps(outcome)
    assert "urn:uuid:" not in json.dumps(outcome)


def test_real_single_bundle_public_cli_refuses_mismatched_patient_with_no_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / f"{_SENSITIVE}-wrong-person.json"
    source.write_text(json.dumps(_mismatched()), encoding="utf-8")
    assert public_cli(["fhir", "bundle-preflight", str(source), "--synthetic-only"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "observation_encounter_patient_mismatch" in output.err
    assert _SENSITIVE not in output.err
    assert str(source) not in output.err
    assert list(tmp_path.iterdir()) == [source]


def test_real_multi_file_cli_returns_actionable_redacted_second_source_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good, bad = _two_patients(), _mismatched()
    first = tmp_path / f"{_SENSITIVE}-good.json"
    second = tmp_path / f"{_SENSITIVE}-bad.json"
    first.write_text(json.dumps(good), encoding="utf-8")
    second.write_text(json.dumps(bad), encoding="utf-8")
    assert (
        public_cli(["fhir", "batch-bundle-diagnose", "--synthetic-only", str(first), str(second)])
        == 2
    )
    response = capsys.readouterr()
    assert response.err == ""
    payload = json.loads(response.out)
    assert payload["document_count"] == 2
    assert payload["preflight_only_count"] == 1
    assert payload["rejected_local_count"] == 1
    accepted, rejected = payload["documents"]
    assert accepted["local_relationship_status"] == "preflight_only"
    assert accepted["resource_counts"]["Patient"] == 2
    assert rejected["local_relationship_status"] == "rejected"
    assert "source_content_sha256" not in rejected
    assert "resource_count" not in rejected
    assert (
        "different local Patients" in (rejected["operation_outcome"]["issue"][0]["details"]["text"])
    )
    for secret in (_SENSITIVE, str(first), str(second), "urn:uuid:", "fictional-patient"):
        assert secret not in response.out + response.err
    assert set(tmp_path.iterdir()) == {first, second}


def test_dual_official_r4_assessment_never_runs_schema_on_wrong_patient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from medscale.fhirkit import bundle_assessment as assessment

    def must_not_validate(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("official schema must NOT run before local patient matching")

    monkeypatch.setattr(assessment, "validate_offline_r4_json_structure", must_not_validate)
    with pytest.raises(BundlePreflightError, match="observation_encounter_patient_mismatch"):
        assessment.assess_synthetic_bundle_offline(
            _mismatched(),
            Path("unused-official-r4.zip"),
            synthetic_only=True,
        )


def test_atomic_encrypted_import_never_calls_commit_on_cross_patient_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from medscale_workspace import fhir_batch

    def commit_should_not_run(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("never call encrypted commit on a mismatched local patient")

    monkeypatch.setattr(fhir_batch, "commit_synthetic_fhir_batch_atomic", commit_should_not_run)
    with pytest.raises(SyntheticWorkspaceImportError, match="synthetic_bundle_preflight_refused"):
        ingest_synthetic_bundle_atomic(
            _mismatched(),
            object(),
            test_key_provider=object(),
            actor_id="invented-operator",
            occurred_at="2026-11-05T05:00:00+03:00",
            synthetic_only=True,
        )


def test_duplicate_or_unmarked_source_cannot_masquerade_as_qualified() -> None:
    copy_source = copy.deepcopy(_mismatched())
    copy_source["meta"] = {"tag": []}
    with pytest.raises(BundlePreflightError, match="explicit_synthetic_fixture_marker_required"):
        inspect_synthetic_bundle(copy_source)
