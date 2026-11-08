"""Public negative-outcome UX for refused fictional FHIR Bundle references.

Uses finite fixed diagnostics and returns *only* a rejected FHIR-shaped
OperationOutcome with CLI exit 2. Never an accepted dual assessment receipt.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from medscale.cli import main as public_main
from medscale.fhirkit.bundle import BundlePreflightError
from medscale.fhirkit.bundle_diagnostics import (
    _FIXED_LOCAL_FAILURES,
    NegativeBundleOutcomeError,
    rejected_synthetic_bundle_operation_outcome,
    rejected_synthetic_bundle_outcome_json,
)
from medscale.fhirkit.r4_schema import validate_offline_r4_json_structure
from medscale.fhirkit.workspace_demo import _fictional_bundle

SECRET = "NEVER_SHOW_THIS_FICTIONAL_PATIENT_OR_HOSPITAL_DATA"
MARKER = "urn:medorigin:fixture-classification"


@pytest.mark.parametrize("error_code", sorted(_FIXED_LOCAL_FAILURES))
def test_every_fixed_relationship_failure_yields_only_redacted_fhir_issues(
    error_code: str,
) -> None:
    source: dict[str, Any] = _fictional_bundle()
    source["entry"][1]["resource"]["name"][0]["text"] = SECRET
    reason = BundlePreflightError(error_code)
    outcome: dict[str, Any] = rejected_synthetic_bundle_operation_outcome(source, reason)
    serialized = rejected_synthetic_bundle_outcome_json(source, reason)
    assert json.loads(serialized) == outcome
    assert outcome["resourceType"] == "OperationOutcome"
    assert set(outcome) == {"resourceType", "issue"}
    assert len(outcome["issue"]) == 2
    assert [i["severity"] for i in outcome["issue"]] == ["error", "warning"]
    assert [i["code"] for i in outcome["issue"]] == ["structure", "informational"]
    assert "NOT run or established" in outcome["issue"][-1]["details"]["text"]
    assert error_code not in serialized  # Safe human-readable fixed descriptions
    for text in (SECRET, "fictional-patient-001", "urn:uuid:", "http://"):
        assert text not in serialized


@pytest.mark.parametrize(
    "reason",
    [
        BundlePreflightError("arbitrary:" + SECRET),
        BundlePreflightError(""),
        BundlePreflightError("unresolved_local_patient_reference\n" + SECRET),
        ValueError("unresolved_local_patient_reference"),
    ],
)
def test_unknown_or_forged_refusal_cannot_be_serialized(reason: Exception) -> None:
    with pytest.raises(NegativeBundleOutcomeError, match="unqualified_bundle_failure_refused"):
        # The forged ValueError refusal is deliberately outside the declared type.
        rejected_synthetic_bundle_operation_outcome(
            _fictional_bundle(), cast(BundlePreflightError, reason)
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda source: source.pop("meta"),
        lambda source: source["meta"].update(tag=[]),
        lambda source: source["meta"].update(tag=[{"system": "secret", "code": "synthetic"}]),
        lambda source: source["meta"].update(tag=[{"system": MARKER, "code": SECRET}]),
    ],
)
def test_no_exact_synthetic_marker_means_no_fhir_shaped_result(
    mutate: Callable[[dict[str, Any]], object],
) -> None:
    source = _fictional_bundle()
    mutate(source)
    with pytest.raises(
        NegativeBundleOutcomeError, match="explicit_synthetic_fixture_marker_required"
    ):
        rejected_synthetic_bundle_operation_outcome(
            source, BundlePreflightError("unresolved_local_patient_reference")
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda source: source["entry"][0]["resource"]["subject"].update(
            reference="urn:uuid:00000000-0000-4000-8000-000000000099"
        ),
        lambda source: source["entry"][0]["resource"]["subject"].update(
            reference="https://external.example/fhir/Patient/" + SECRET
        ),
        lambda source: source["entry"][0]["resource"].update({"unreviewed": SECRET}),
        lambda source: source["entry"][1]["resource"].update(resourceType="Patient" + SECRET),
        lambda source: source["entry"][1].update(fullUrl=source["entry"][0]["fullUrl"]),
        lambda source: source["entry"][0]["resource"]["encounter"].update(
            reference=source["entry"][1]["fullUrl"]
        ),
    ],
)
def test_installed_style_public_dispatcher_gives_rejected_outcome_not_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    mutate: Callable[[dict[str, Any]], object],
) -> None:
    source: dict[str, Any] = _fictional_bundle()
    source["entry"][1]["resource"]["name"][0]["text"] = SECRET
    mutate(source)
    path = tmp_path / "invented-fhir-input.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    missing_schema = tmp_path / "nonexistent-schema.zip"
    assert (
        public_main(
            [
                "fhir",
                "bundle-assess",
                "--synthetic-only",
                "--offline-r4-schema",
                str(missing_schema),
                str(path),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.err == ""
    negative = json.loads(captured.out)
    assert negative["resourceType"] == "OperationOutcome"
    assert set(negative) == {"resourceType", "issue"}
    assert negative["issue"][0]["severity"] == "error"
    assert negative["issue"][1]["severity"] == "warning"
    for piece in (SECRET, str(path), str(missing_schema), "external.example", "urn:uuid:"):
        assert piece not in captured.out
    assert sorted(tmp_path.iterdir()) == [path]


def test_missing_synthetic_tag_keeps_existing_no_outcome_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _fictional_bundle()
    source.pop("meta")
    path = tmp_path / "unmarked-input.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    assert (
        public_main(
            [
                "fhir",
                "bundle-assess",
                "--synthetic-only",
                "--offline-r4-schema",
                str(tmp_path / "no-zip.zip"),
                str(path),
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert "relationship_preflight_refused" in output.err
    assert SECRET not in output.err


def test_correct_synthetic_bundle_still_requires_official_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "good-synthetic.json"
    path.write_text(json.dumps(_fictional_bundle()), encoding="utf-8")
    assert (
        public_main(
            [
                "fhir",
                "bundle-assess",
                "--synthetic-only",
                "--offline-r4-schema",
                str(tmp_path / "not-official.zip"),
                str(path),
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert "qualified_offline_schema_missing" in output.err
    assert not list(tmp_path.rglob("report.json"))


def test_real_official_r4_accepts_the_finite_rejected_operation_outcomes() -> None:
    archive_path = os.environ.get("MEDORIGIN_OFFICIAL_R4_SCHEMA_ZIP")
    if not archive_path:
        pytest.skip("exact official pinned R4 archive not supplied for opt-in QA")
    archive = Path(archive_path)
    for code in (
        "unresolved_local_patient_reference",
        "external_or_invalid_reference_refused",
        "duplicate_bundle_resource_identity",
        "unreviewed_bundle_resource_field_refused",
    ):
        outcome = rejected_synthetic_bundle_operation_outcome(
            _fictional_bundle(), BundlePreflightError(code)
        )
        report = validate_offline_r4_json_structure(outcome, archive)
        assert report.status == "not_validated"
        assert report.errors == ()
