"""Deterministic POSIX directory-swap attacks against FHIR report loading.

All artifacts are synthetic and task-owned. A test hook swaps a directory
after the existing pathname preflight, with no concurrent background process.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, storage, store_report
from medscale.fhirkit.storage import load_report


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor-relative directory walk only")
@pytest.mark.parametrize("swap_component", ["digest", "root"])
def test_load_rejects_directory_symlink_swapped_after_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_component: str
) -> None:
    report = ValidationReport(status="valid")
    root = tmp_path / "canonical-root"
    canonical = store_report(report, root=root)
    digest = report_hash(report)

    if swap_component == "digest":
        swap_path = canonical.parent
        decoy = tmp_path / "decoy-digest"
        decoy.mkdir()
        (decoy / "report.json").write_bytes(canonical.read_bytes())
    else:
        swap_path = root
        decoy = tmp_path / "decoy-root"
        decoy_report = store_report(report, root=decoy)
        assert decoy_report.read_bytes() == canonical.read_bytes()

    saved = tmp_path / "parked-original"
    original_preflight = storage._reject_report_directory_symlinks
    swapped = False

    def swap_after_preflight(root_arg: Path, digest_arg: str) -> None:
        nonlocal swapped
        original_preflight(root_arg, digest_arg)
        assert not swapped
        swap_path.rename(saved)
        swap_path.symlink_to(decoy, target_is_directory=True)
        swapped = True

    monkeypatch.setattr(storage, "_reject_report_directory_symlinks", swap_after_preflight)
    with pytest.raises(FhirStorageError):
        load_report(digest, root=root)
    assert swapped
    assert swap_path.is_symlink()
    assert saved.is_dir()


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor-relative directory walk only")
def test_nofollow_load_preserves_normal_canonical_report(tmp_path: Path) -> None:
    report = ValidationReport(status="valid")
    root = tmp_path / "normal" / "nested"
    path = store_report(report, root=root)
    assert load_report(report_hash(report), root=root) == path.read_text(encoding="utf-8")
