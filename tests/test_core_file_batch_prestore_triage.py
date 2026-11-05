"""User-visible, invented-only FHIR pre-storage source diagnosis tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit.workspace_demo import _fictional_bundle
from medscale.fhirkit.workspace_file_readiness import (
    SyntheticFileBatchReadinessError,
    assess_fictional_file_batch_readiness,
)
from medscale.fhirkit.workspace_file_triage import (
    SyntheticFileBatchTriageError,
    fictional_file_batch_triage_json,
    triage_fictional_file_batch,
)
from medscale.fhirkit.workspace_multi_timeline_demo import (
    _second_fictional_timeline_bundle,
)

_SECRET = "SENSITIVE_FICTIONAL_PATIENT_TEXT_MUST_NEVER_ESCAPE"


def _two() -> list[dict]:
    first = _fictional_bundle()
    second = _second_fictional_timeline_bundle()
    for item in (first, second):
        item["entry"][1]["resource"]["name"][0]["text"] = _SECRET
    return [first, second]


def _files(tmp_path: Path, payloads: list[dict]) -> list[Path]:
    output: list[Path] = []
    for i, item in enumerate(payloads, 1):
        file = tmp_path / f"{_SECRET}-file-{i}.json"
        file.write_text(json.dumps(item), encoding="utf-8")
        output.append(file)
    return output


def test_all_ready_reconciles_same_source_day_counts_as_original_readiness() -> None:
    sources = _two()
    triage = triage_fictional_file_batch(sources, synthetic_only=True)
    readiness = assess_fictional_file_batch_readiness(sources, synthetic_only=True)
    assert triage["schema"] == "medorigin-core-fictional-prestorage-file-triage/v1"
    assert triage["status"] == "SYNTHETIC_FILE_TRIAGE_ONLY_NOT_VALIDATED"
    assert triage["source_count"] == 2
    assert triage["source_ready_count"] == 2
    assert triage["source_blocked_count"] == 0
    assert triage["all_sources_locally_ready"] is True
    for actual, expected in zip(triage["sources"], readiness["sources"], strict=True):
        assert actual["status"] == "ready_for_synthetic_readiness_only"
        assert actual["reason_code"] is None
        assert actual["reason_text"] is None
        assert actual["source_content_sha256"] == expected["source_content_sha256"]
        assert actual["resource_count"] == expected["resource_count"]
        assert actual["timeline_event_count"] == expected["timeline_event_count"]
        assert actual["dated_event_count"] == expected["dated_event_count"]
        assert actual["undated_event_count"] == expected["undated_event_count"]
        assert actual["first_day_utc"] == expected["first_day_utc"]
        assert actual["last_day_utc"] == expected["last_day_utc"]
    assert [i["first_day_utc"] for i in triage["sources"]] == [None, "2026-11-04"]
    assert [i["last_day_utc"] for i in triage["sources"]] == [None, "2026-11-05"]
    for field in (
        "source_filenames_included", "patient_identity_included",
        "precise_timestamps_included", "payload_included", "workspace_allocated",
        "output_persisted", "network_access_performed",
        "cross_source_patient_join_performed", "official_r4_schema_checked",
        "fhir_r4_conformance_validated", "clinical_use_authorized",
        "publication_authorized",
    ):
        assert triage[field] is False
    encoded = fictional_file_batch_triage_json(sources, synthetic_only=True)
    assert json.loads(encoded) == triage
    assert encoded.endswith("\n")
    assert _SECRET not in encoded
    assert "urn:uuid:" not in encoded


@pytest.mark.parametrize(
    ("mutate", "stage", "reason"),
    [
        (
            lambda b: b["entry"][0]["resource"].update(
                effectiveDateTime="2026-02-30T00:10:00Z"
            ),
            "timeline", "timeline_observation_invalid",
        ),
        (
            lambda b: b["entry"][0]["resource"].update(
                effectiveDateTime="2026-11-03"
            ),
            "timeline", "timeline_observation_timezone_timestamp_required",
        ),
        (
            lambda b: b["entry"][2]["resource"].update(period={
                "start": "2026-11-05T06:00:00Z",
                "end": "2026-11-04T05:00:00Z",
            }),
            "timeline", "timeline_encounter_period_reversed",
        ),
        (
            lambda b: b["entry"][2]["resource"].update(period={
                "end": "2026-11-04T05:00:00Z",
            }),
            "timeline", "timeline_encounter_period_start_required",
        ),
        (
            lambda b: b["entry"][0]["resource"].update(status="FINAL"),
            "local_relationship", "observation_status_not_in_r4_required_codes",
        ),
        (
            lambda b: b["entry"][0]["resource"].update(
                valueString=_SECRET, valueQuantity={"value": 5},
            ),
            "local_relationship", "observation_multiple_r4_choice_values_refused",
        ),
        (
            lambda b: b["entry"][0]["resource"].update(
                unreviewed_patient_record=_SECRET
            ),
            "local_relationship", "unreviewed_bundle_resource_field_refused",
        ),
    ],
)
def test_per_source_actionable_fixed_error_after_shared_import_gate_refuses(
    mutate, stage: str, reason: str
) -> None:
    sources = _two()
    mutate(sources[1])
    actual = triage_fictional_file_batch(sources, synthetic_only=True)
    assert actual["source_ready_count"] == 1
    assert actual["source_blocked_count"] == 1
    assert actual["all_sources_locally_ready"] is False
    assert actual["sources"][0]["status"] == "ready_for_synthetic_readiness_only"
    rejected = actual["sources"][1]
    assert rejected["source_ordinal"] == 2
    assert rejected["status"] == "blocked"
    assert rejected["stage"] == stage
    assert rejected["reason_code"] == reason
    assert rejected["reason_text"]
    assert rejected["source_content_sha256"] is None
    assert rejected["resource_count"] is None
    assert rejected["first_day_utc"] is None
    encoded = fictional_file_batch_triage_json(sources, synthetic_only=True)
    assert _SECRET not in encoded
    assert "urn:uuid:" not in encoded
    with pytest.raises(
        SyntheticFileBatchReadinessError, match="fictional_readiness_source_preflight_refused"
    ):
        assess_fictional_file_batch_readiness(sources, synthetic_only=True)


def test_original_duplicate_source_has_ordinal_diagnostic_not_false_admission() -> None:
    sources = _two()
    sources[1] = copy.deepcopy(sources[0])
    triage = triage_fictional_file_batch(sources, synthetic_only=True)
    assert triage["source_ready_count"] == 1
    assert triage["source_blocked_count"] == 1
    assert triage["sources"][1]["source_content_sha256"] is None
    assert triage["sources"][1]["stage"] == "source_identity"
    assert triage["sources"][1]["reason_code"] == (
        "fictional_import_duplicate_source_refused"
    )
    assert triage["all_sources_locally_ready"] is False


def test_one_patient_per_file_and_empty_event_source() -> None:
    sources = _two()
    second = sources[1]
    second["entry"] = [
        row for row in second["entry"]
        if row["resource"]["resourceType"] == "Patient"
    ]
    triage = triage_fictional_file_batch(sources, synthetic_only=True)
    assert triage["source_blocked_count"] == 0
    assert triage["sources"][1]["timeline_event_count"] == 0
    assert triage["sources"][1]["first_day_utc"] is None
    assert triage["sources"][1]["undated_event_count"] == 0


def test_real_cli_triage_returns_useful_second_file_reason_without_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = _two()
    sources[1]["entry"][2]["resource"]["period"] = {
        "start": "2026-11-05T10:00:00Z",
        "end": "2026-11-04T10:00:00Z",
    }
    files = _files(tmp_path, sources)
    before = {p: p.read_bytes() for p in files}
    assert public_cli([
        "fhir", "file-batch-triage", "--synthetic-only", *(str(p) for p in files)
    ]) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    value = json.loads(captured.out)
    assert value["sources"][1]["reason_code"] == "timeline_encounter_period_reversed"
    assert value["sources"][1]["source_ordinal"] == 2
    assert set(tmp_path.iterdir()) == set(files)
    assert all(path.read_bytes() == before[path] for path in files)
    for secret in (_SECRET, "urn:uuid:", *(str(p) for p in files)):
        assert secret not in captured.out + captured.err


def test_triage_never_attempts_workspace_allocation(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as importer

    def forbidden_workspace(*_args, **_kwargs):
        raise AssertionError("triage must never create encrypted Workspace")

    monkeypatch.setattr(importer, "TemporaryDirectory", forbidden_workspace)
    value = triage_fictional_file_batch(_two(), synthetic_only=True)
    assert value["all_sources_locally_ready"] is True


def test_missing_synthetic_marker_refuses_all_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = _two()
    sources[1].pop("meta")
    with pytest.raises(SyntheticFileBatchTriageError, match="marker_required"):
        triage_fictional_file_batch(sources, synthetic_only=True)
    files = _files(tmp_path, sources)
    assert public_cli([
        "fhir", "file-batch-triage", "--synthetic-only", *(str(p) for p in files)
    ]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert result.err.strip() == "file triage refused: unqualified_batch_or_marker"
    for file in files:
        assert str(file) not in result.err


def test_malformed_json_and_bad_flags_have_no_partial_diagnostics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = _files(tmp_path, _two())
    files[1].write_text("{BAD_JSON_" + _SECRET, encoding="utf-8")
    assert public_cli([
        "fhir", "file-batch-triage", "--synthetic-only", *(str(p) for p in files)
    ]) == 1
    bad = capsys.readouterr()
    assert bad.out == ""
    assert bad.err.strip() == "file triage refused: fictional_source_input_refused"
    assert _SECRET not in bad.err
    assert public_cli([
        "fhir", "file-batch-triage", *(str(p) for p in files)
    ]) == 2
    missing_flag = capsys.readouterr()
    assert missing_flag.out == ""
    assert "explicit_fictional_readonly_batch_required" in missing_flag.err


def test_more_than_four_sources_refuses_no_partial_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = _files(tmp_path, _two())
    assert public_cli([
        "fhir", "file-batch-triage", "--synthetic-only",
        *(str(p) for p in [*files, files[0], files[1], files[0]]),
    ]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "explicit_fictional_readonly_batch_required" in output.err


def test_readonly_help_states_nonclinical(capsys: pytest.CaptureFixture[str]) -> None:
    assert public_cli(["fhir", "file-batch-triage", "--help"]) == 0
    value = capsys.readouterr().out
    assert "--synthetic-only" in value
    assert "NO database, PHI, full FHIR validation" in value
