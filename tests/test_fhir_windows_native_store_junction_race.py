"""Synthetic Windows report-store write redirection must fail closed.

Uses actual unprivileged NTFS junctions, with byte-identical valid synthetic
reports and no PHI, network, clinical execution or privileged Windows settings.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, storage, store_report


@pytest.mark.skipif(os.name != "nt", reason="real NTFS directory junction requires Windows")
@pytest.mark.parametrize("stage", ["root_preflight", "digest_preflight"])
def test_windows_store_refuses_late_junction_without_decoy_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """No mkdir, temp write, publish or cleanup through swapped public paths."""
    report = ValidationReport(status="valid")
    root = tmp_path / "original-root"
    root.mkdir()
    target_dir = storage.fhirkit_reports_dir(root) / report_hash(report)
    if stage == "digest_preflight":
        target_dir.mkdir(parents=True)
    swapped = root if stage == "root_preflight" else target_dir
    parked = tmp_path / "original-parked"
    decoy = tmp_path / "decoy-empty"
    decoy.mkdir()

    prior = storage._reject_report_directory_symlinks
    seen: list[int] = []

    def swap_after_preflight(root_arg: Path, digest_arg: str) -> None:
        prior(root_arg, digest_arg)
        seen.append(len(seen) + 1)
        if len(seen) == (1 if stage == "root_preflight" else 2):
            swapped.rename(parked)
            link = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", str(swapped), str(decoy)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            assert link.returncode == 0, link.stderr or link.stdout
            assert swapped.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT

    monkeypatch.setattr(storage, "_reject_report_directory_symlinks", swap_after_preflight)
    with pytest.raises(FhirStorageError):
        store_report(report, root=root)
    assert len(seen) >= (1 if stage == "root_preflight" else 2)
    assert parked.is_dir()
    assert list(decoy.iterdir()) == [], "report store wrote or mkdir'ed inside swapped decoy"


@pytest.mark.skipif(os.name != "nt", reason="native Windows HANDLE publication only")
def test_windows_store_does_not_follow_hardlink_target_directory_after_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even after the pinned target is opened, a junction must not redirect writes."""
    report = ValidationReport(status="valid")
    root = tmp_path / "original-root"
    root.mkdir()
    target_dir = storage.fhirkit_reports_dir(root) / report_hash(report)
    target_dir.mkdir(parents=True)
    parked = tmp_path / "parked"
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    prior = storage._reject_report_directory_symlinks
    activated: list[bool] = []

    def swap_at_second_check(root_arg: Path, digest_arg: str) -> None:
        prior(root_arg, digest_arg)
        if not activated:
            activated.append(True)
            return
        if len(activated) == 1:
            target_dir.rename(parked)
            result = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", str(target_dir), str(decoy)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            assert result.returncode == 0
            activated.append(True)

    monkeypatch.setattr(storage, "_reject_report_directory_symlinks", swap_at_second_check)
    with pytest.raises(FhirStorageError):
        store_report(report, root=root)
    assert len(activated) == 2
    assert list(decoy.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="native Windows HANDLE-relative link only")
def test_windows_store_link_stays_pinned_after_directory_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rename/reparse after tempfile fsync, immediately before native hard link."""
    report = ValidationReport(status="valid")
    root = tmp_path / "root"
    root.mkdir()
    directory = storage.fhirkit_reports_dir(root) / report_hash(report)
    directory.mkdir(parents=True)
    parked = tmp_path / "parked-original"
    decoy = tmp_path / "decoy-empty"
    decoy.mkdir()
    link_real = storage._windows_link_pinned
    witnessed: list[str] = []

    def attempt_rename_at_link(native: object, source: int, parent: int) -> None:
        try:
            directory.rename(parked)
        except PermissionError:
            # Real hosted Windows2025 denied a directory rename while its
            # child temporary file HANDLE was still open. This is a valid
            # native denial, not evidence that the hook was not reached.
            witnessed.append("windows-denied-rename")
            link_real(native, source, parent)
            return
        result = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(directory), str(decoy)],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        assert directory.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
        witnessed.append("swapped")
        link_real(native, source, parent)

    monkeypatch.setattr(storage, "_windows_link_pinned", attempt_rename_at_link)
    try:
        stored = store_report(report, root=root)
    except FhirStorageError:
        assert witnessed == ["swapped"], "only a successful path swap can justify refusal"
    else:
        assert witnessed == ["windows-denied-rename"]
        assert stored == directory / "report.json"
        assert stored.is_file()
    assert witnessed, "native hard-link hook must execute"
    assert list(decoy.iterdir()) == [], "native publication must never enter decoy"
    if witnessed == ["swapped"]:
        assert parked.is_dir()
        assert not list(parked.glob(".report-*.tmp"))
    else:
        assert directory.is_dir()
        assert not list(directory.glob(".report-*.tmp"))
