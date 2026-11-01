"""Windows-only synthetic failure injection at CRT fd -> Python file object handoff.

An already-created NTFS temporary report must be disposed via its adopted
descriptor if os.fdopen fails. No PHI, EHR, network, or publication.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, storage, store_report


@pytest.mark.skipif(os.name != "nt", reason="native Windows CRT descriptor handoff only")
def test_failed_fdopen_disposes_adopted_native_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = ValidationReport(status="valid")
    root = tmp_path / "native-root"
    root.mkdir()
    directory = storage.fhirkit_reports_dir(root) / report_hash(report)
    adopted: list[int] = []

    def reject_file_object(fd: int, *args: object, **kwargs: object) -> None:
        adopted.append(fd)
        raise OSError("synthetic Python file object construction failure")

    monkeypatch.setattr(os, "fdopen", reject_file_object)
    with pytest.raises(FhirStorageError):
        store_report(report, root=root)

    assert len(adopted) == 1, "test must reach the post-adoption fdopen boundary"
    assert directory.is_dir()
    assert not list(directory.glob(".report-*.tmp")), "unpublished adopted temp leaked"
    assert not (directory / "report.json").exists(), "failed write published a report"
