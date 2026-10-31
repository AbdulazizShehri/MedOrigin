"""Atomic FHIR report publication: never expose partial canonical artifacts.

Only fictional deterministic reports and task-local temporary paths are used.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, storage, store_report
from medscale.fhirkit.report import report_to_json


def _target(root: Path, report: ValidationReport) -> Path:
    return storage.fhirkit_reports_dir(root) / report_hash(report) / "report.json"


def _assert_no_temporary_reports(target: Path) -> None:
    assert list(target.parent.glob(".report-*.tmp")) == []


def test_failed_atomic_link_does_not_publish_or_leave_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = ValidationReport(status="valid")
    target = _target(tmp_path, report)
    attempts = 0

    def deny_link(
        _source: os.PathLike[str] | str, _destination: os.PathLike[str] | str, **_kwargs: object
    ) -> None:
        nonlocal attempts
        attempts += 1
        raise OSError(errno.EACCES, "synthetic link refusal")

    if os.name == "nt":
        def deny_native_link(_native: object, _source_handle: int, _directory_handle: int) -> None:
            deny_link("native-temp", "report.json")
        monkeypatch.setattr(storage, "_windows_link_pinned", deny_native_link)
    else:
        monkeypatch.setattr(os, "link", deny_link)
    with pytest.raises(FhirStorageError, match=r"create .*FHIR report artifact"):
        store_report(report, root=tmp_path)
    assert attempts == 1
    assert not target.exists()
    _assert_no_temporary_reports(target)


def test_failed_fsync_does_not_publish_or_leave_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = ValidationReport(status="valid")
    target = _target(tmp_path, report)
    attempts = 0

    def deny_fsync(_descriptor: int) -> None:
        nonlocal attempts
        attempts += 1
        raise OSError(errno.EIO, "synthetic flush failure")

    monkeypatch.setattr(os, "fsync", deny_fsync)
    with pytest.raises(FhirStorageError, match="create FHIR report artifact"):
        store_report(report, root=tmp_path)
    assert attempts == 1
    assert not target.exists()
    _assert_no_temporary_reports(target)


def test_atomic_link_collision_preserves_matching_existing_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = ValidationReport(status="valid")
    target = _target(tmp_path, report)
    expected = report_to_json(report)
    attempts = 0

    def concurrent_identical_writer(
        _source: os.PathLike[str] | str, destination: os.PathLike[str] | str, **kwargs: object
    ) -> None:
        nonlocal attempts
        attempts += 1
        if "dst_dir_fd" in kwargs:
            descriptor = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=kwargs["dst_dir_fd"],
            )
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                output.write(expected)
        else:
            with Path(destination).open("w", encoding="utf-8", newline="\n") as output:
                output.write(expected)
        raise FileExistsError(errno.EEXIST, "synthetic concurrent writer")

    if os.name == "nt":
        def concurrent_windows(
            _native: object, _source_handle: int, _directory_handle: int
        ) -> None:
            concurrent_identical_writer("native-temp", target)
        monkeypatch.setattr(storage, "_windows_link_pinned", concurrent_windows)
    else:
        monkeypatch.setattr(os, "link", concurrent_identical_writer)
    assert store_report(report, root=tmp_path) == target
    assert attempts == 1
    assert target.read_text(encoding="utf-8") == expected
    _assert_no_temporary_reports(target)


def test_successful_atomic_publish_remains_idempotent_and_leaves_no_temps(
    tmp_path: Path,
) -> None:
    report = ValidationReport(status="valid")
    target = _target(tmp_path, report)
    assert store_report(report, root=tmp_path) == target
    assert store_report(report, root=tmp_path) == target
    assert target.read_text(encoding="utf-8") == report_to_json(report)
    _assert_no_temporary_reports(target)
