"""Real, private, local fictional FHIR batch triage and source-safe diagnostics."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit.bundle_batch_diagnostics import (
    SyntheticBatchDiagnosticsError,
    diagnose_synthetic_bundle_batch_local,
)
from medscale.fhirkit.workspace_demo import _fictional_bundle

_PRIVATE = "VERY_PRIVATE_FICTIONAL_NAME_NOT_FOR_LOGS"


def _pair() -> list[dict]:
    first = _fictional_bundle()
    first["entry"][1]["resource"]["name"][0]["text"] = _PRIVATE
    second = copy.deepcopy(first)
    second["entry"][0]["resource"]["valueString"] = "An entirely fictional second value"
    return [first, second]


def _sources(tmp_path: Path, pair: list[dict]) -> list[Path]:
    paths: list[Path] = []
    for index, bundle in enumerate(pair):
        filename = tmp_path / f"{_PRIVATE}_{index}.json"
        filename.write_text(json.dumps(bundle), encoding="utf-8")
        paths.append(filename)
    return paths


def _public_args(paths: list[Path]) -> list[str]:
    return ["fhir", "batch-bundle-diagnose", "--synthetic-only", *(str(p) for p in paths)]


def test_real_cli_actionable_per_source_outcome_from_fictional_json_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pair = _pair()
    pair[1]["entry"][0]["resource"]["subject"]["reference"] = (
        "https://untrusted.example/fhir/Patient/" + _PRIVATE
    )
    paths = _sources(tmp_path, pair)
    assert public_cli(_public_args(paths)) == 2
    output = capsys.readouterr()
    assert output.err == ""
    result = json.loads(output.out)
    assert result["schema"] == "medorigin-core-fictional-batch-local-triage/v1"
    assert result["status"] == "LOCAL_FICTIONAL_BUNDLE_TRIAGE_ONLY"
    assert result["document_count"] == 2
    assert result["preflight_only_count"] == 1
    assert result["rejected_local_count"] == 1
    good, bad = result["documents"]
    assert good["document_ordinal"] == 1
    assert good["local_relationship_status"] == "preflight_only"
    assert good["resource_count"] == 3
    assert good["resource_counts"] == {"Encounter": 1, "Observation": 1, "Patient": 1}
    assert good["local_references_checked"] == 3
    assert len(good["source_content_sha256"]) == 64
    assert bad["document_ordinal"] == 2
    assert bad["local_relationship_status"] == "rejected"
    assert "source_content_sha256" not in bad
    assert "resource_count" not in bad
    issues = bad["operation_outcome"]["issue"]
    assert [entry["severity"] for entry in issues] == ["error", "warning"]
    assert [entry["code"] for entry in issues] == ["structure", "informational"]
    assert (
        "external" in issues[0]["details"]["text"].lower()
        or "uuid" in issues[0]["details"]["text"].lower()
    )
    for flag in (
        "source_filenames_included",
        "patient_identifiers_included",
        "resource_payload_included",
        "filesystem_export_performed",
        "network_access_performed",
        "cross_bundle_patient_identity_join_performed",
        "official_r4_json_schema_check_performed",
        "full_fhir_r4_conformance_established",
        "clinical_use_authorized",
        "publication_authorized",
    ):
        assert result[flag] is False
    for forbidden in (_PRIVATE, str(paths[0]), str(paths[1]), "untrusted.example", "urn:uuid:"):
        assert forbidden not in output.out + output.err
    assert set(tmp_path.iterdir()) == set(paths)


def test_both_marked_files_with_good_local_relationships_are_still_preflight_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    paths = _sources(tmp_path, _pair())
    assert public_cli(_public_args(paths)) == 2
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["preflight_only_count"] == 2
    assert receipt["rejected_local_count"] == 0
    assert all(p["local_relationship_status"] == "preflight_only" for p in receipt["documents"])
    assert all(p["r4_schema_check_run"] is False for p in receipt["documents"])


def test_one_unmarked_source_refuses_entire_batch_without_partial_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle = _pair()
    bundle[1].pop("meta")
    paths = _sources(tmp_path, bundle)
    assert public_cli(_public_args(paths)) == 2
    message = capsys.readouterr()
    assert message.out == ""
    assert message.err.strip().endswith("source_qualification_refused")
    assert _PRIVATE not in message.err


def test_duplicate_source_refused_even_when_both_marked() -> None:
    bundle = _pair()[0]
    with pytest.raises(
        SyntheticBatchDiagnosticsError, match="batch_diagnostics_duplicate_source_refused"
    ):
        diagnose_synthetic_bundle_batch_local([bundle, copy.deepcopy(bundle)], synthetic_only=True)


@pytest.mark.parametrize(
    "payloads,reason",
    [
        ([], "batch_diagnostics_document_bounds_refused"),
        ([{}], "batch_diagnostics_document_bounds_refused"),
        ([{}] * 9, "batch_diagnostics_document_bounds_refused"),
        ([{}, None], "batch_diagnostics_marker_refused"),
    ],
)
def test_bad_shape_is_refused_without_echo(payloads, reason: str) -> None:
    with pytest.raises(SyntheticBatchDiagnosticsError, match=reason):
        diagnose_synthetic_bundle_batch_local(payloads, synthetic_only=True)


def test_missing_explicit_synthetic_permission_is_refused() -> None:
    with pytest.raises(
        SyntheticBatchDiagnosticsError, match="batch_diagnostics_synthetic_only_required"
    ):
        diagnose_synthetic_bundle_batch_local(_pair(), synthetic_only=False)


@pytest.mark.parametrize(
    "bad",
    [
        [],
        ["--synthetic-only"],
        ["--synthetic-only", "only-one"],
        ["--synthetic-only", "one", "--patient", _PRIVATE],
        ["one", "two"],
        ["--synthetic-only", "one", "two", "--unknown"],
        ["--synthetic-only", *[str(i) for i in range(9)]],
    ],
)
def test_cli_requires_exact_fictional_flags_without_echoing_caller_text(
    bad: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert public_cli(["fhir", "batch-bundle-diagnose", *bad]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "explicit_fictional_batch_flags_required" in captured.err
    assert _PRIVATE not in captured.err


def test_unreadable_second_source_refuses_no_partial_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    paths = _sources(tmp_path, _pair())
    paths[1].unlink()
    assert public_cli(_public_args(paths)) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "source_input_refused" in output.err
    assert _PRIVATE not in output.err


def test_adversarial_spoofed_downstream_fhir_diagnostic_text_is_never_relayed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import medscale.fhirkit.bundle_batch_diagnostics as module

    bundle = _pair()
    bundle[1]["entry"][0]["resource"]["subject"]["reference"] = (
        "https://untrusted.example/patient/" + _PRIVATE
    )

    def poisoned_outcome(*_args, **_kwargs):
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {"severity": "error", "code": "structure", "details": {"text": _PRIVATE}},
            ],
        }

    monkeypatch.setattr(module, "rejected_synthetic_bundle_operation_outcome", poisoned_outcome)
    with pytest.raises(
        SyntheticBatchDiagnosticsError, match="batch_diagnostics_outcome_contract_refused"
    ) as exc:
        module.diagnose_synthetic_bundle_batch_local(bundle, synthetic_only=True)
    assert _PRIVATE not in str(exc.value)


def test_cli_help_never_implies_full_r4_validation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert public_cli(["fhir", "batch-bundle-diagnose", "--help"]) == 0
    printed = capsys.readouterr()
    assert "NOT HL7 R4" in printed.out
    assert "FICTIONAL_BUNDLE_8" in printed.out
    assert printed.err == ""
