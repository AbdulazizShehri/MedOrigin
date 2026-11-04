"""Synthetic-only FHIR local report storage corruption and traversal regression."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale.cli import fhir as fhir_cli
from medscale.fhirkit.errors import FhirStorageError
from medscale.fhirkit.report import report_hash, report_to_json
from medscale.fhirkit.storage import fhirkit_reports_dir, load_report, store_report
from medscale.fhirkit.validate import validate_fhir


@pytest.fixture
def report():
    return validate_fhir(
        {"resourceType": "StructureDefinition", "id": "fictional-synthetic-only"},
        created_at="2026-11-04T00:00:00Z",
    )


def _expected_path(root: Path, report) -> Path:
    return fhirkit_reports_dir(root) / report_hash(report) / "report.json"


def test_new_content_addressed_file_is_regular_and_can_be_loaded(tmp_path: Path, report) -> None:
    target = store_report(report, root=tmp_path)
    assert target == _expected_path(tmp_path, report)
    assert target.is_file()
    assert target.stat().st_nlink == 1
    assert load_report(report_hash(report), root=tmp_path) == report_to_json(report)


def test_identical_report_is_idempotent_and_not_rewritten(tmp_path: Path, report) -> None:
    target = store_report(report, root=tmp_path)
    before = target.stat().st_mtime_ns
    assert store_report(report, root=tmp_path) == target
    assert target.stat().st_mtime_ns == before
    assert target.read_text(encoding="utf-8") == report_to_json(report)


def test_preexisting_corrupt_report_is_not_repaired_or_overwritten(tmp_path: Path, report) -> None:
    target = _expected_path(tmp_path, report)
    target.parent.mkdir(parents=True)
    original = b"FICTIONAL UNCHANGED CORRUPT REPORT SENTINEL"
    target.write_bytes(original)
    with pytest.raises(FhirStorageError, match="mismatch"):
        store_report(report, root=tmp_path)
    assert target.read_bytes() == original


def test_hardlinked_report_cannot_modify_separate_file(tmp_path: Path, report) -> None:
    victim = tmp_path / "fictional-other-file.txt"
    original = b"FICTIONAL EXTERNAL USER FILE MUST NOT CHANGE"
    victim.write_bytes(original)
    target = _expected_path(tmp_path, report)
    target.parent.mkdir(parents=True)
    os.link(victim, target)
    assert target.stat().st_nlink == 2
    with pytest.raises(FhirStorageError, match="linked"):
        store_report(report, root=tmp_path)
    assert victim.read_bytes() == original
    assert target.read_bytes() == original


def test_valid_contents_through_a_hardlink_are_still_rejected(tmp_path: Path, report) -> None:
    victim = tmp_path / "fictional-duplicate-report.json"
    victim.write_text(report_to_json(report), encoding="utf-8", newline="\n")
    target = _expected_path(tmp_path, report)
    target.parent.mkdir(parents=True)
    os.link(victim, target)
    with pytest.raises(FhirStorageError, match="linked"):
        store_report(report, root=tmp_path)
    with pytest.raises(FhirStorageError, match="linked"):
        load_report(report_hash(report), root=tmp_path)


@pytest.mark.parametrize(
    "artifact_id",
    [
        "",
        ".",
        "..",
        "../../unreviewed-file",
        "..\\..\\unreviewed-file",
        "/" + "a" * 64,
        "A" * 64,
        "g" * 64,
        "0" * 63,
        "0" * 65,
        "0" * 64 + "/../../file",
        "0" * 64 + "\\..\\..\\file",
    ],
)
def test_report_id_must_be_exact_lowercase_64_hex(tmp_path: Path, artifact_id: str) -> None:
    with pytest.raises(FhirStorageError, match="invalid FHIR report artifact id"):
        load_report(artifact_id, root=tmp_path)


def test_report_id_traversal_cannot_read_outside_reports_root(
    tmp_path: Path,
) -> None:
    victim = tmp_path / "unreviewed-file"
    victim.mkdir()
    path = victim / "report.json"
    path.write_text("FICTIONAL OUTSIDE-ROOT SECRET", encoding="utf-8")
    # The parent implementation would read this by traversing from
    # {root}/fhirkit/reports/../../unreviewed-file/report.json.
    (tmp_path / "fhirkit" / "reports").mkdir(parents=True)
    with pytest.raises(FhirStorageError, match="invalid"):
        load_report("../../unreviewed-file", root=tmp_path)
    assert path.read_text(encoding="utf-8") == "FICTIONAL OUTSIDE-ROOT SECRET"


def test_read_refuses_missing_artifact_without_path_leak(
    tmp_path: Path,
) -> None:
    with pytest.raises(FhirStorageError) as caught:
        load_report("a" * 64, root=tmp_path)
    assert str(tmp_path) not in str(caught.value)


def test_linked_fhir_report_parent_directory_is_refused(tmp_path: Path, report) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "fictional-target"
    outside.mkdir()
    root.mkdir()
    linked = root / "fhirkit"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("host lacks symlink creation privileges")
    with pytest.raises(FhirStorageError, match="linked"):
        store_report(report, root=root)
    assert list(outside.rglob("*")) == []


def test_final_report_symlink_refused_without_changing_victim(tmp_path: Path, report) -> None:
    victim = tmp_path / "victim.txt"
    original = b"FICTIONAL VICTIM NEVER MODIFIED"
    victim.write_bytes(original)
    target = _expected_path(tmp_path, report)
    target.parent.mkdir(parents=True)
    try:
        target.symlink_to(victim)
    except (OSError, NotImplementedError):
        pytest.skip("host lacks symlink creation privileges")
    with pytest.raises(FhirStorageError):
        store_report(report, root=tmp_path)
    with pytest.raises(FhirStorageError):
        load_report(report_hash(report), root=tmp_path)
    assert victim.read_bytes() == original


def test_existing_nonreport_directory_will_not_be_replaced(tmp_path: Path, report) -> None:
    target = _expected_path(tmp_path, report)
    target.mkdir(parents=True)
    with pytest.raises(FhirStorageError):
        store_report(report, root=tmp_path)
    assert target.is_dir()


def test_loading_modified_but_well_formed_report_rejects_corrupt_digest(
    tmp_path: Path, report
) -> None:
    target = store_report(report, root=tmp_path)
    # Modify a guaranteed present field while retaining syntactically valid
    # canonical JSON; the address hash must no longer match its contents.
    tampered = target.read_text(encoding="utf-8").replace(
        '"status":"not_validated"', '"status":"valid"'
    )
    assert tampered != target.read_text(encoding="utf-8")
    target.write_text(tampered, encoding="utf-8", newline="\n")
    with pytest.raises(FhirStorageError, match="checksum"):
        load_report(report_hash(report), root=tmp_path)
    assert target.read_text(encoding="utf-8") == tampered


def test_cli_reports_storage_refusal_without_positive_receipt_or_paths(
    tmp_path: Path, report, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "fictional-input.json"
    source.write_text(
        '{"resourceType":"StructureDefinition","id":"fictional-synthetic-only"}',
        encoding="utf-8",
    )
    root = tmp_path / "private-output"
    target = _expected_path(root, report)
    target.parent.mkdir(parents=True)
    # The CLI uses its own fresh created-at unless provided explicitly.
    # Pin the same value as the expected deterministic report hash.
    target.write_bytes(b"FICTIONAL CORRUPTED REPORT IN CONTENT-ADDRESSED SLOT")
    exit_code = fhir_cli.main(
        [
            str(source),
            "--output-dir",
            str(root),
            "--created-at",
            "2026-11-04T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "FHIR_REPORT_STORAGE_BLOCKED" in captured.err
    assert str(root) not in captured.err
    assert "Traceback" not in captured.err
    assert target.read_bytes() == b"FICTIONAL CORRUPTED REPORT IN CONTENT-ADDRESSED SLOT"
