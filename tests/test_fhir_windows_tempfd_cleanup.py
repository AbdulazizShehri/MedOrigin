"""Synthetic Windows native report-store temp HANDLE conversion failure regression.

No PHI, EHR, network, model or publishing operations.  The test forces a
failure after the temporary NTFS file is created, before Python owns its HANDLE.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, storage, store_report


@pytest.mark.skipif(os.name != "nt", reason="native Windows HANDLE conversion only")
def test_windows_failed_temp_fd_adoption_disposes_unpublished_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed CRT HANDLE adoption must not leave a synthetic .report temp file."""
    import msvcrt

    report = ValidationReport(status="valid")
    root = tmp_path / "native-root"
    root.mkdir()
    directory = storage.fhirkit_reports_dir(root) / report_hash(report)
    calls: list[int] = []

    def reject_adoption(handle: int, flags: int) -> int:
        calls.append(handle)
        raise OSError("synthetic CRT descriptor-adoption failure")

    monkeypatch.setattr(msvcrt, "open_osfhandle", reject_adoption)
    with pytest.raises(FhirStorageError):
        store_report(report, root=root)

    assert len(calls) == 1, "failure injection must reach the newly created native temp HANDLE"
    assert directory.is_dir()
    assert not list(directory.glob(".report-*.tmp")), "unpublished native temporary file leaked"
    assert not (directory / "report.json").exists(), "failed store must not publish a report"
