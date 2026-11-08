"""Real caller-selected fictional FHIR JSON -> encrypted filter after full cold-reopen.

Source events and fake dates are invented. No real patient data, EHR or network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NoReturn

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit.workspace_demo import _fictional_bundle
from medscale.fhirkit.workspace_file_batch_demo import (
    SyntheticFileImportDemoError,
    run_fictional_file_batch_encrypted_demo,
)
from medscale.fhirkit.workspace_multi_timeline_demo import (
    _second_fictional_timeline_bundle,
)

_PRIVATE = "INVENTED_PRIVATE_PERSON_DO_NOT_ECHO"


def _fictional_two() -> list[dict[str, Any]]:
    first: dict[str, Any] = _fictional_bundle()
    first["entry"][0]["resource"]["effectiveDateTime"] = "2026-11-02T22:10:00-05:00"
    first["entry"][2]["resource"]["period"] = {
        "start": "2026-11-03T02:20:00Z",
        "end": "2026-11-03T03:00:00Z",
    }
    first["entry"][1]["resource"]["name"][0]["text"] = _PRIVATE
    second: dict[str, Any] = _second_fictional_timeline_bundle()
    second["entry"][1]["resource"]["name"][0]["text"] = _PRIVATE + "_SECOND"
    return [first, second]


def _local(tmp: Path) -> list[Path]:
    output = []
    for index, source in enumerate(_fictional_two(), 1):
        item = tmp / f"{_PRIVATE}-source-{index}.json"
        item.write_text(json.dumps(source), encoding="utf-8")
        output.append(item)
    return output


def _cli(source_files: list[Path], flags: list[str]) -> list[str]:
    return [
        "fhir",
        "file-batch-encrypted-demo",
        "--synthetic-only",
        "--ephemeral-demo",
        *flags,
        *(str(file) for file in source_files),
    ]


@pytest.mark.parametrize(
    ("flags", "visible", "types", "days", "per_import"),
    [
        (
            [
                "--from-day",
                "2026-11-04",
                "--through-day",
                "2026-11-04",
                "--event-type",
                "Encounter",
            ],
            1,
            ["Encounter"],
            ["2026-11-04"],
            [0, 1],
        ),
        (
            [
                "--from-day",
                "2026-11-04",
                "--through-day",
                "2026-11-04",
                "--event-type",
                "Observation",
            ],
            0,
            [],
            [],
            [0, 0],
        ),
        (
            ["--event-type", "Observation"],
            2,
            ["Observation", "Observation"],
            ["2026-11-03", "2026-11-05"],
            [1, 1],
        ),
        (
            ["--through-day", "2026-11-03"],
            2,
            ["Encounter", "Observation"],
            ["2026-11-03", "2026-11-03"],
            [2, 0],
        ),
        (
            ["--from-day", "2026-11-05"],
            1,
            ["Observation"],
            ["2026-11-05"],
            [0, 1],
        ),
    ],
)
def test_actual_file_filtered_encrypted_cold_reopen_source_scoped(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    flags: list[str],
    visible: int,
    types: list[str],
    days: list[str],
    per_import: list[int],
) -> None:
    files = _local(tmp_path)
    original_bytes = [file.read_bytes() for file in files]
    assert public_cli(_cli(files, flags)) == 2
    output = capsys.readouterr()
    assert output.err == ""
    report = json.loads(output.out)
    assert report["schema"] == "medorigin-core-fictional-file-encrypted-batch-reopen/v1"
    assert report["status"] == "FICTIONAL_FILE_BATCH_ENCRYPTED_REOPEN_VERIFIED"
    assert report["import_count"] == 2
    assert report["verified_timeline_event_count"] == 4
    assert report["verified_audit_events"] == 2
    assert report["physically_closed_and_reopened"] is True
    assert report["ephemeral_store_removed"] is True
    filtered = report["filtered_review"]
    assert filtered["schema"] == "medorigin-core-caller-file-filtered-verified-review/v1"
    assert filtered["status"] == "FICTIONAL_SOURCE_VERIFIED_FILTERED_REVIEW"
    assert filtered["source_total_event_count"] == 4
    assert filtered["visible_total_event_count"] == visible
    assert filtered["hidden_total_event_count"] == 4 - visible
    assert [x["visible_event_count"] for x in filtered["imports"]] == per_import
    assert [x["source_event_count"] for x in filtered["imports"]] == [2, 2]
    events = [e for group in filtered["imports"] for e in group["events"]]
    assert [e["resource_type"] for e in events] == types
    assert [e["day_utc"] for e in events] == days
    assert all(e["ordinal"] in (1, 2) for e in events)
    assert all(e["date_available"] is True for e in events)
    for key in (
        "cross_import_patient_identity_join_performed",
        "patient_identity_included",
        "resource_payload_included",
        "clinical_use_authorized",
        "fhir_r4_conformance_validated",
    ):
        assert filtered[key] is False
    for group, full in zip(filtered["imports"], report["imports"], strict=True):
        assert group["source_content_sha256"] == full["source_content_sha256"]
        assert group["import_audit_event_digest"] == full["import_audit_event_digest"]
        assert group["hidden_event_count"] + group["visible_event_count"] == 2
    assert [file.read_bytes() for file in files] == original_bytes
    assert set(tmp_path.iterdir()) == set(files)
    for private in (_PRIVATE, str(files[0]), str(files[1]), "urn:uuid:", "fictional-patient"):
        assert private not in output.out + output.err


def test_no_options_preserves_original_receipt_exact_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = _local(tmp_path)
    assert public_cli(_cli(files, [])) == 2
    output = json.loads(capsys.readouterr().out)
    assert "filtered_review" not in output
    assert output["verified_timeline_event_count"] == 4
    assert output["ephemeral_store_removed"] is True


@pytest.mark.parametrize(
    ("flags", "expected_error"),
    [
        (["--from-day", "2026-02-30"], "verified_encrypted_fictional_batch_refused"),
        (["--through-day", "2026-13-01"], "verified_encrypted_fictional_batch_refused"),
        (
            ["--from-day", "2026-11-06", "--through-day", "2026-11-04"],
            "verified_encrypted_fictional_batch_refused",
        ),
        (["--event-type", "Patient"], "verified_encrypted_fictional_batch_refused"),
        (
            ["--event-type", "Observation", "--event-type", "Encounter"],
            "exact_fictional_ephemeral_file_flags_required",
        ),
        (
            ["--from-day", "2026-11-04", "--from-day", "2026-11-05"],
            "exact_fictional_ephemeral_file_flags_required",
        ),
        (["--event-type"], "exact_fictional_ephemeral_file_flags_required"),
        (["--unknown", _PRIVATE], "exact_fictional_ephemeral_file_flags_required"),
    ],
)
def test_invalid_filter_is_redacted_and_nonzero_no_partial_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    flags: list[str],
    expected_error: str,
) -> None:
    files = _local(tmp_path)
    assert public_cli(_cli(files, flags)) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert expected_error in result.err
    assert _PRIVATE not in result.err


@pytest.mark.parametrize(
    "bad",
    [
        {"from_day_utc": "2026-02-29"},
        {"through_day_utc": "2026-11-31"},
        {"from_day_utc": "2026-11-05", "through_day_utc": "2026-11-04"},
        {"resource_type": "Patient"},
        {"from_day_utc": 6},
    ],
)
def test_bad_api_filter_is_rejected_before_workspace_allocation(
    monkeypatch: pytest.MonkeyPatch,
    bad: dict[str, Any],
) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as module

    def refuse_allocation(*_args: object, **_kw: object) -> NoReturn:
        raise AssertionError("must not allocate if filter is invalid")

    monkeypatch.setattr(module, "TemporaryDirectory", refuse_allocation)
    with pytest.raises(SyntheticFileImportDemoError, match="fictional_import_filter_refused"):
        run_fictional_file_batch_encrypted_demo(
            _fictional_two(), synthetic_only=True, ephemeral_demo=True, **bad
        )


def test_filtered_result_with_forged_patient_field_refused_no_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from medscale.fhirkit import workspace_multi_timeline as module

    original = module.list_filtered_verified_synthetic_import_timelines

    def poisoned(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result: dict[str, Any] = original(*args, **kwargs)
        result["imports"][0]["private_patient_identity"] = _PRIVATE
        return result

    monkeypatch.setattr(module, "list_filtered_verified_synthetic_import_timelines", poisoned)
    with pytest.raises(SyntheticFileImportDemoError, match="workspace_verification_refused") as err:
        run_fictional_file_batch_encrypted_demo(
            _fictional_two(),
            synthetic_only=True,
            ephemeral_demo=True,
            resource_type="Observation",
        )
    assert _PRIVATE not in str(err.value)


def test_forged_extra_visible_event_refused_even_when_dates_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from medscale.fhirkit import workspace_multi_timeline as module

    original = module.list_filtered_verified_synthetic_import_timelines

    def poisoned(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result: dict[str, Any] = original(*args, **kwargs)
        result["imports"][0]["events"][0]["patient_name"] = _PRIVATE
        return result

    monkeypatch.setattr(module, "list_filtered_verified_synthetic_import_timelines", poisoned)
    with pytest.raises(SyntheticFileImportDemoError, match="workspace_verification_refused"):
        run_fictional_file_batch_encrypted_demo(
            _fictional_two(),
            synthetic_only=True,
            ephemeral_demo=True,
            resource_type="Observation",
        )


def test_hidden_corrupt_source_invalidates_entire_filtered_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from medscale.fhirkit import workspace_multi_timeline as module

    original = module.list_verified_synthetic_import_timelines
    hits = [0]

    def corrupt_second_independent_verification(*args: Any, **kwargs: Any) -> dict[str, object]:
        hits[0] += 1
        if hits[0] == 2:
            raise RuntimeError(_PRIVATE)
        return original(*args, **kwargs)

    monkeypatch.setattr(
        module, "list_verified_synthetic_import_timelines", corrupt_second_independent_verification
    )
    with pytest.raises(SyntheticFileImportDemoError, match="workspace_verification_refused") as err:
        run_fictional_file_batch_encrypted_demo(
            _fictional_two(),
            synthetic_only=True,
            ephemeral_demo=True,
            from_day_utc="2026-11-04",
            through_day_utc="2026-11-04",
            resource_type="Observation",
        )
    assert _PRIVATE not in str(err.value)
