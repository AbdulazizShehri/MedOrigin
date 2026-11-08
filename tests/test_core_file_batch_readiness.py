"""Real fictional FHIR batch readiness, read-only dates before encryption.

All fixtures are invented. No real PHI, EHR, network, saved Workspace or
claim of HL7 R4 profile/terminology/FHIRPath/clinical validation.
"""

from __future__ import annotations

import copy
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit.workspace_demo import _fictional_bundle
from medscale.fhirkit.workspace_file_batch_demo import (
    SyntheticFileImportDemoError,
    run_fictional_file_batch_encrypted_demo,
)
from medscale.fhirkit.workspace_file_readiness import (
    SyntheticFileBatchReadinessError,
    assess_fictional_file_batch_readiness,
    fictional_file_batch_readiness_json,
)
from medscale.fhirkit.workspace_multi_timeline_demo import (
    _second_fictional_timeline_bundle,
)

_SECRET = "NEVER_ECHO_FICTIONAL_PATIENT_NAME"


def _two() -> list[dict[str, Any]]:
    first: dict[str, Any] = _fictional_bundle()
    second: dict[str, Any] = _second_fictional_timeline_bundle()
    first["entry"][1]["resource"]["name"][0]["text"] = _SECRET
    second["entry"][1]["resource"]["name"][0]["text"] = _SECRET + "_SECOND"
    return [first, second]


def _files(tmp_path: Path, sources: list[dict[str, Any]]) -> list[Path]:
    files: list[Path] = []
    for i, source in enumerate(sources, 1):
        path = tmp_path / f"{_SECRET}-{i}.json"
        path.write_text(json.dumps(source), encoding="utf-8")
        files.append(path)
    return files


def _assert_flags_false(receipt: dict[str, Any]) -> None:
    for key in (
        "source_filenames_included",
        "patient_identity_included",
        "precise_timestamps_included",
        "cross_source_patient_join_performed",
        "payload_included",
        "workspace_allocated",
        "output_persisted",
        "network_access_performed",
        "fhir_r4_conformance_validated",
        "clinical_use_authorized",
        "publication_authorized",
    ):
        assert receipt[key] is False


def test_real_readonly_readiness_reports_undated_and_utc_days_before_storage() -> None:
    receipt: dict[str, Any] = assess_fictional_file_batch_readiness(_two(), synthetic_only=True)
    assert receipt["schema"] == "medorigin-core-fictional-file-batch-readiness/v1"
    assert receipt["status"] == "SYNTHETIC_READ_ONLY_IMPORT_READINESS_NOT_VALIDATED"
    assert receipt["source_count"] == 2
    assert receipt["total_resource_count"] == 6
    assert receipt["total_timeline_events"] == 4
    assert receipt["total_dated_events"] == 2
    assert receipt["total_undated_events"] == 2
    assert receipt["official_r4_structural_status"] == "not_requested"
    assert [r["source_ordinal"] for r in receipt["sources"]] == [1, 2]
    assert [r["resource_count"] for r in receipt["sources"]] == [3, 3]
    assert [r["timeline_event_count"] for r in receipt["sources"]] == [2, 2]
    assert [r["dated_event_count"] for r in receipt["sources"]] == [0, 2]
    assert [r["undated_event_count"] for r in receipt["sources"]] == [2, 0]
    assert [r["first_day_utc"] for r in receipt["sources"]] == [None, "2026-11-04"]
    assert [r["last_day_utc"] for r in receipt["sources"]] == [None, "2026-11-05"]
    assert len({r["source_content_sha256"] for r in receipt["sources"]}) == 2
    assert all(len(r["source_content_sha256"]) == 64 for r in receipt["sources"])
    _assert_flags_false(receipt)
    encoded = fictional_file_batch_readiness_json(_two(), synthetic_only=True)
    assert json.loads(encoded) == receipt
    assert encoded.endswith("\n")
    for forbidden in (_SECRET, "urn:uuid:", "fictional-patient-001", "mmol/L"):
        assert forbidden not in encoded


def test_real_public_cli_readiness_is_readonly_and_reports_no_filepath(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = _files(tmp_path, _two())
    original = {p: p.read_bytes() for p in files}
    args = ["fhir", "file-batch-readiness", "--synthetic-only", *(str(p) for p in files)]
    assert public_cli(args) == 2
    got = capsys.readouterr()
    assert got.err == ""
    receipt = json.loads(got.out)
    assert receipt["source_count"] == 2
    assert receipt["total_timeline_events"] == 4
    _assert_flags_false(receipt)
    assert set(tmp_path.iterdir()) == set(files)
    assert all(p.read_bytes() == original[p] for p in files)
    for hidden in (_SECRET, *(str(p) for p in files), "urn:uuid:"):
        assert hidden not in got.out + got.err


@pytest.mark.parametrize(
    ("change", "kind"),
    [
        (
            lambda b: b["entry"][0]["resource"].update(effectiveDateTime="2026-02-30T00:10:00Z"),
            "invalid_observation",
        ),
        (
            lambda b: b["entry"][0]["resource"].update(effectiveDateTime="2026-11-03"),
            "partial_observation",
        ),
        (
            lambda b: b["entry"][2]["resource"].update(
                period={
                    "start": "2026-11-05T05:00:00Z",
                    "end": "2026-11-04T05:00:00Z",
                }
            ),
            "reversed_encounter",
        ),
        (
            lambda b: b["entry"][2]["resource"].update(period={"end": "2026-11-04T05:00:00Z"}),
            "missing_period_start",
        ),
        (
            lambda b: b["entry"][2]["resource"].update(period={"start": "2026-11-03T00:10:00"}),
            "timezone_missing",
        ),
    ],
)
def test_invalid_second_source_dates_fail_before_any_encrypted_allocation(
    change: Callable[[dict[str, Any]], object], kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as importer

    sources = _two()
    change(sources[1])

    def prevent_workspace(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("encrypted SQLite must not be allocated")

    monkeypatch.setattr(importer, "TemporaryDirectory", prevent_workspace)
    with pytest.raises(
        SyntheticFileImportDemoError, match="fictional_import_timeline_preflight_refused"
    ) as error:
        run_fictional_file_batch_encrypted_demo(sources, synthetic_only=True, ephemeral_demo=True)
    assert _SECRET not in str(error.value)
    with pytest.raises(
        SyntheticFileBatchReadinessError, match="fictional_readiness_source_preflight_refused"
    ):
        assess_fictional_file_batch_readiness(sources, synthetic_only=True)


def test_duplicate_source_is_never_reported_or_joined() -> None:
    source = _two()[0]
    with pytest.raises(SyntheticFileBatchReadinessError, match="source_preflight_refused"):
        assess_fictional_file_batch_readiness([source, copy.deepcopy(source)], synthetic_only=True)


def test_readiness_never_creates_ephemeral_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as importer

    def never_allocate(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("read-only planning must not allocate Workspace")

    monkeypatch.setattr(importer, "TemporaryDirectory", never_allocate)
    report = assess_fictional_file_batch_readiness(_two(), synthetic_only=True)
    assert report["workspace_allocated"] is False


def test_cli_missing_consent_or_bad_source_returns_no_partial_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = _files(tmp_path, _two())
    wrong = [
        ["fhir", "file-batch-readiness", *(str(p) for p in sources)],
        ["fhir", "file-batch-readiness", "--synthetic-only", str(sources[0])],
        [
            "fhir",
            "file-batch-readiness",
            "--synthetic-only",
            "--offline-r4-schema",
            "--unexpected",
            *(str(p) for p in sources),
        ],
        [
            "fhir",
            "file-batch-readiness",
            "--synthetic-only",
            "--insecure",
            *(str(p) for p in sources),
        ],
    ]
    for argv in wrong:
        assert public_cli(argv) == 2
        capture = capsys.readouterr()
        assert capture.out == ""
        assert _SECRET not in capture.err
        for path in sources:
            assert str(path) not in capture.err


def test_bad_official_r4_archive_never_downgrades_to_partial_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = _files(tmp_path, _two())
    fake_zip = tmp_path / "not-the-official.zip"
    fake_zip.write_bytes(b"NOT_OFFICIAL_R4_SCHEMA")
    assert (
        public_cli(
            [
                "fhir",
                "file-batch-readiness",
                "--synthetic-only",
                "--offline-r4-schema",
                str(fake_zip),
                *(str(p) for p in sources),
            ]
        )
        == 2
    )
    capture = capsys.readouterr()
    assert capture.out == ""
    assert capture.err.strip() == "file readiness refused: source_or_timeline_preflight_refused"
    assert str(fake_zip) not in capture.err


def test_genuine_official_r4_schema_is_structural_only_if_provided() -> None:
    archive = os.getenv("MEDORIGIN_OFFICIAL_R4_SCHEMA_ZIP")
    if not archive:
        pytest.skip("genuine official R4 pinned archive not supplied")
    result = assess_fictional_file_batch_readiness(
        _two(), synthetic_only=True, offline_r4_schema=Path(archive)
    )
    assert result["source_count"] == 2
    assert result["official_r4_structural_status"] == ("official_r4_structure_only_not_validated")
    assert result["fhir_r4_conformance_validated"] is False


def test_fictional_single_patient_only_and_no_implicit_cross_source_merge() -> None:
    sources = _two()
    sources[1]["entry"] = [
        row for row in sources[1]["entry"] if row["resource"]["resourceType"] == "Patient"
    ]
    ready: dict[str, Any] = assess_fictional_file_batch_readiness(sources, synthetic_only=True)
    assert ready["sources"][1]["timeline_event_count"] == 0
    assert ready["sources"][1]["first_day_utc"] is None
    assert ready["cross_source_patient_join_performed"] is False
    assert ready["total_undated_events"] == 2
