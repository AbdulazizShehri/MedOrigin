"""Native Windows FHIR report load must refuse late NTFS junction aliases.

Real mklink /J is available without elevated symlink privileges on Windows.
All bytes/paths are ephemeral synthetic reports, never patient data.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, storage
from medscale.fhirkit.report import report_to_json
from medscale.fhirkit.storage import load_report


@pytest.mark.skipif(os.name != "nt", reason="NTFS junction and NtCreateFile are Windows-only")
@pytest.mark.parametrize("swap", ["root", "ancestor"])
def test_load_refuses_junction_swapped_after_lexical_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap: str
) -> None:
    """A later pathname open must not dereference an untrusted junction."""
    report = ValidationReport(status="valid")
    digest = report_hash(report)
    anchor = tmp_path / "source-parent"
    root = anchor / "reports"
    root.mkdir(parents=True)
    target = storage.fhirkit_reports_dir(root) / digest / "report.json"
    target.parent.mkdir(parents=True)
    target.write_text(report_to_json(report), encoding="utf-8")

    decoy = tmp_path / "decoy"
    decoy_root = decoy if swap == "root" else decoy / "reports"
    fake_target = storage.fhirkit_reports_dir(decoy_root) / digest / "report.json"
    fake_target.parent.mkdir(parents=True)
    fake_target.write_text(report_to_json(report), encoding="utf-8")

    junction = root if swap == "root" else anchor
    destination = decoy
    moved = tmp_path / "parked-original"
    original_preflight = storage._reject_report_directory_symlinks
    visited: list[bool] = []

    def replace_after_preflight(root_arg: Path, digest_arg: str) -> None:
        original_preflight(root_arg, digest_arg)
        if visited:
            return
        junction.rename(moved)
        result = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(junction), str(destination)],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        flags = junction.lstat().st_file_attributes
        assert flags & stat.FILE_ATTRIBUTE_REPARSE_POINT
        visited.append(True)

    monkeypatch.setattr(storage, "_reject_report_directory_symlinks", replace_after_preflight)
    with pytest.raises(FhirStorageError, match=r"unreadable|reparse|junction|untrusted"):
        load_report(digest, root=root)
    assert visited, "real junction replacement hook not exercised"
    assert junction.is_dir() and moved.is_dir()
