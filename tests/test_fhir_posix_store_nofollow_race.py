"""Synthetic POSIX report-store races must not redirect filesystem writes.

The deterministic hook swaps an ancestor after lexical preflight; no attacker
process, network access, clinical data, or privileged filesystem is involved.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, storage, store_report


@pytest.mark.skipif(os.name == "nt", reason="POSIX dir_fd hardening only")
@pytest.mark.parametrize("swap_at", ["first_root_preflight", "second_digest_preflight"])
def test_store_never_writes_through_swapped_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_at: str
) -> None:
    report = ValidationReport(status="valid")
    root = tmp_path / "root"
    root.mkdir()
    digest_dir = storage.fhirkit_reports_dir(root) / report_hash(report)
    if swap_at == "second_digest_preflight":
        digest_dir.mkdir(parents=True)
    swap_path = root if swap_at == "first_root_preflight" else digest_dir
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    parked = tmp_path / "parked-original"

    original_preflight = storage._reject_report_directory_symlinks
    calls = 0

    def swap_after_preflight(root_arg: Path, digest_arg: str) -> None:
        nonlocal calls
        original_preflight(root_arg, digest_arg)
        calls += 1
        if calls == (1 if swap_at == "first_root_preflight" else 2):
            swap_path.rename(parked)
            swap_path.symlink_to(decoy, target_is_directory=True)

    monkeypatch.setattr(storage, "_reject_report_directory_symlinks", swap_after_preflight)
    with pytest.raises(FhirStorageError):
        store_report(report, root=root)
    assert swap_path.is_symlink()
    assert parked.is_dir()
    assert list(decoy.iterdir()) == [], "store must not create even temporary files in decoy"
