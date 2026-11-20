"""R4 Observation.value[x] choice admission in the local synthetic-only Core.

Official R4 Observation.value[x] 0..1:
https://hl7.org/fhir/R4/observation.html
These fixtures are invented. This checks one choice-cardinality invariant
only; it does NOT prove full FHIR R4 profiles, terminology or clinical safety.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit.bundle import BundlePreflightError, inspect_synthetic_bundle
from medscale.fhirkit.bundle_diagnostics import (
    rejected_synthetic_bundle_operation_outcome,
    rejected_synthetic_bundle_outcome_json,
)
from medscale.fhirkit.workspace_file_batch_demo import (
    SyntheticFileImportDemoError,
    run_fictional_file_batch_encrypted_demo,
)

_SECRET = "FICTIONAL_PATIENT_NAME_MUST_NEVER_APPEAR"
_PATIENT = "urn:uuid:00000000-0000-4000-8000-000000000002"
_ENCOUNTER = "urn:uuid:00000000-0000-4000-8000-000000000003"
_FAILURE = "observation_multiple_r4_choice_values_refused"


def _bundle() -> dict[str, Any]:
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
                    "code": {"text": "invented-only"},
                    "subject": {"reference": _PATIENT},
                    "encounter": {"reference": _ENCOUNTER},
                },
            },
            {
                "fullUrl": _PATIENT,
                "resource": {
                    "resourceType": "Patient",
                    "id": "fictional-patient-001",
                    "name": [{"text": _SECRET}],
                },
            },
            {
                "fullUrl": _ENCOUNTER,
                "resource": {
                    "resourceType": "Encounter",
                    "id": "fictional-encounter-001",
                    "status": "finished",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                    },
                    "subject": {"reference": _PATIENT},
                },
            },
        ],
    }


@pytest.mark.parametrize(
    "admitted",
    [
        {},
        {"valueString": "fictional"},
        {"valueQuantity": {"value": 10.0, "unit": "mmol/L"}},
    ],
)
@pytest.mark.parametrize("status", ["registered", "preliminary", "final"])
def test_r4_zero_or_one_choice_value_admitted_locally(
    admitted: dict[str, Any], status: str
) -> None:
    bundle = _bundle()
    bundle["entry"][0]["resource"].update(admitted)
    bundle["entry"][0]["resource"]["status"] = status
    summary = inspect_synthetic_bundle(bundle)
    assert summary["resource_count"] == 3
    assert summary["local_references_checked"] == 3
    assert summary["full_fhir_r4_conformance_established"] is False
    assert summary["terminology_profiles_invariants_verified"] is False
    assert summary["clinical_use_authorized"] is False
    assert _SECRET not in json.dumps(summary)


@pytest.mark.parametrize(
    ("value_string", "value_quantity"),
    [
        ("example", {"value": 2.5, "unit": "mg"}),
        ("", {}),
        (None, None),
        ("\\x00", {"unit": "fake"}),
        (_SECRET, {"text": _SECRET}),
    ],
)
def test_multiple_observation_values_refused_regardless_of_contents(
    value_string: object, value_quantity: object
) -> None:
    bundle = _bundle()
    observation = bundle["entry"][0]["resource"]
    observation["valueString"] = value_string
    observation["valueQuantity"] = value_quantity
    with pytest.raises(BundlePreflightError, match=_FAILURE) as raised:
        inspect_synthetic_bundle(bundle)
    assert str(raised.value) == _FAILURE
    assert _SECRET not in str(raised.value)
    assert "Observation" not in str(raised.value)


def test_r4_status_check_still_precedes_choice_check() -> None:
    bundle = _bundle()
    obs = bundle["entry"][0]["resource"]
    obs["status"] = "R5-FICTIONAL-STATUS"
    obs["valueString"] = "fictional"
    obs["valueQuantity"] = {}
    with pytest.raises(BundlePreflightError, match="observation_status_not_in_r4_required_codes"):
        inspect_synthetic_bundle(bundle)


def test_choice_error_has_only_fixed_redacted_fhir_operation_outcome() -> None:
    bundle = _bundle()
    obs = bundle["entry"][0]["resource"]
    obs["valueString"] = _SECRET
    obs["valueQuantity"] = {"text": _SECRET}
    with pytest.raises(BundlePreflightError, match=_FAILURE) as exc:
        inspect_synthetic_bundle(bundle)
    result: Any = rejected_synthetic_bundle_operation_outcome(bundle, exc.value)
    assert result["resourceType"] == "OperationOutcome"
    assert len(result["issue"]) == 2
    assert result["issue"][0]["severity"] == "error"
    assert result["issue"][1]["severity"] == "warning"
    assert "FHIR R4 value[x]" in result["issue"][0]["details"]["text"]
    encoded = rejected_synthetic_bundle_outcome_json(bundle, exc.value)
    assert json.loads(encoded) == result
    for secret in (_SECRET, "urn:uuid:", "fictional-patient-001", "mg"):
        assert secret not in encoded


def test_real_public_cli_rejects_conflicting_value_before_schema_or_storage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle = _bundle()
    obs = bundle["entry"][0]["resource"]
    obs["valueString"] = _SECRET
    obs["valueQuantity"] = {"value": 3.0, "unit": "fictional-unit"}
    source = tmp_path / f"{_SECRET}-source.json"
    source.write_text(json.dumps(bundle), encoding="utf-8")
    assert public_cli(["fhir", "bundle-preflight", str(source), "--synthetic-only"]) == 2
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err.strip() == "bundle preflight refused: " + _FAILURE
    assert _SECRET not in out.err + out.out
    assert str(source) not in out.err + out.out

    # Unlike a structurally passed source, this invalid choice cannot reach
    # optional official schema loading, even if no official ZIP exists.
    assert (
        public_cli(
            [
                "fhir",
                "bundle-assess",
                "--synthetic-only",
                "--offline-r4-schema",
                str(tmp_path / "missing-official.zip"),
                str(source),
            ]
        )
        == 2
    )
    outcome = capsys.readouterr()
    assert outcome.err == ""
    assert json.loads(outcome.out)["resourceType"] == "OperationOutcome"
    assert _SECRET not in outcome.out + outcome.err
    assert list(tmp_path.iterdir()) == [source]


def test_bad_second_bundle_blocks_real_encrypted_workspace_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as importer

    first = _bundle()
    second = copy.deepcopy(first)
    second["entry"][0]["resource"]["valueQuantity"] = {"value": 2.0}
    second["entry"][0]["resource"]["valueString"] = "ambiguous"

    def forbid_storage(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("encryption store must NOT be allocated")

    monkeypatch.setattr(importer, "TemporaryDirectory", forbid_storage)
    with pytest.raises(
        SyntheticFileImportDemoError, match="fictional_import_source_preflight_refused"
    ) as raised:
        run_fictional_file_batch_encrypted_demo(
            [first, second], synthetic_only=True, ephemeral_demo=True
        )
    assert _SECRET not in str(raised.value)


def test_order_of_bundle_entries_cannot_bypass_choice_cardinality() -> None:
    bundle = _bundle()
    bundle["entry"][0]["resource"]["valueString"] = "invented"
    bundle["entry"][0]["resource"]["valueQuantity"] = {"value": 1.0}
    bundle["entry"].reverse()
    with pytest.raises(BundlePreflightError, match=_FAILURE):
        inspect_synthetic_bundle(bundle)
