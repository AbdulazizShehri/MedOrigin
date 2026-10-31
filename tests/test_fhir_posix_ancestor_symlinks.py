"""Reject POSIX symlinks in ancestors of a FHIR report root.

All data are fictional, local, and task-owned. This test exercises a parent
symlink rather than a symlink at the report root itself.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, store_report
from medscale.fhirkit.storage import load_report


@pytest.mark.skipif(os.name == "nt", reason="POSIX parent-symlink semantics only")
def test_posix_ancestor_symlink_rejected_before_report_io(tmp_path: Path) -> None:
    actual_parent = tmp_path / "actual-parent"
    root = actual_parent / "reports-root"
    root.mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(actual_parent, target_is_directory=True)
    redirected_root = alias / "reports-root"
    assert redirected_root.is_dir()
    assert not redirected_root.is_symlink()

    report = ValidationReport(status="valid")
    with pytest.raises(FhirStorageError, match="symlinked report directory"):
        store_report(report, root=redirected_root)
    with pytest.raises(FhirStorageError, match="symlinked report directory"):
        load_report(report_hash(report), root=redirected_root)
    assert not list(root.rglob("report.json"))


@pytest.mark.skipif(os.name == "nt", reason="POSIX parent-symlink semantics only")
def test_posix_ancestor_symlink_cannot_read_existing_report(tmp_path: Path) -> None:
    actual_parent = tmp_path / "actual-parent"
    root = actual_parent / "nested" / "reports-root"
    root.mkdir(parents=True)
    report = ValidationReport(status="valid")
    store_report(report, root=root)

    alias = tmp_path / "alias"
    alias.symlink_to(actual_parent, target_is_directory=True)
    redirected_root = alias / "nested" / "reports-root"
    assert not redirected_root.is_symlink()
    with pytest.raises(FhirStorageError, match="symlinked report directory"):
        load_report(report_hash(report), root=redirected_root)


@pytest.mark.skipif(os.name == "nt", reason="POSIX parent-symlink semantics only")
def test_posix_normal_nested_root_still_round_trips(tmp_path: Path) -> None:
    root = tmp_path / "normal" / "nested" / "reports-root"
    report = ValidationReport(status="valid")
    store_report(report, root=root)
    assert load_report(report_hash(report), root=root)
