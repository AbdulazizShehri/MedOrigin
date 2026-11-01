"""POSIX FHIR temporary-file descriptor ownership on stream-construction failure.

Fictional in-memory report only. The failed stream constructor must not
leave an open descriptor or an orphan .report-*.tmp.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale._layout import fhirkit_reports_dir
from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, store_report


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor-relative publisher only")
def test_posix_temp_fdopen_failure_closes_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "synthetic-root"
    root.mkdir()
    report = ValidationReport(status="valid")
    real_fdopen = os.fdopen
    rejected: list[int] = []

    def reject_output(fd: int, mode: str = "r", *args: object, **kwargs: object):
        if mode == "w":
            rejected.append(fd)
            raise OSError("synthetic POSIX output stream construction failure")
        return real_fdopen(fd, mode, *args, **kwargs)

    def is_live(fd: int) -> bool:
        try:
            os.fstat(fd)
        except OSError:
            return False
        return True

    monkeypatch.setattr(os, "fdopen", reject_output)
    try:
        with pytest.raises(FhirStorageError):
            store_report(report, root=root)
        assert len(rejected) == 1, "test did not reach POSIX fdopen boundary"
        assert not is_live(rejected[0]), "failed POSIX fdopen leaked an open descriptor"
        directory = fhirkit_reports_dir(root) / report_hash(report)
        assert not list(directory.glob(".report-*.tmp")), "orphan POSIX temporary artifact"
        assert not (directory / "report.json").exists(), "failed write must not publish"
    finally:
        # Keep RED regression safe: close intentionally leaked FD on failure.
        for fd in rejected:
            if is_live(fd):
                os.close(fd)
