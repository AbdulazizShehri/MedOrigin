"""Windows junction regression: FHIR report roots must not traverse reparse points.

Synthetic-only, no UNC endpoints or real patient data. This test requires a
real Windows directory junction, not a symlink mock.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, store_report
from medscale.fhirkit.storage import load_report


@pytest.mark.skipif(os.name != "nt", reason="Windows NTFS junction semantics only")
@pytest.mark.parametrize("nested", [False, True])
def test_windows_junction_ancestor_rejected_before_report_io(tmp_path: Path, nested: bool) -> None:
    real = tmp_path / "real"
    real.mkdir()
    if nested:
        (real / "child").mkdir()
    junction = tmp_path / "junction"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert created.returncode == 0, created.stderr

    # A junction is a reparse point, not a Python Path.is_symlink() symlink.
    assert junction.is_dir()
    assert not junction.is_symlink()
    root = junction / "child" if nested else junction
    report = ValidationReport(status="valid")
    with pytest.raises(FhirStorageError, match="reparse"):
        store_report(report, root=root)
    with pytest.raises(FhirStorageError, match="reparse"):
        load_report(report_hash(report), root=root)
    assert not list(real.rglob("report.json"))
