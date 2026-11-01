"""Adversarial inode/link-count and mode drift tests for unapproved ADR-0045.

All files are synthetic local scratch. No package release or owner ADR acceptance.
"""

from __future__ import annotations

import importlib.util
import os
import stat
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_medorigin_base_only_proposal.py"
WHEEL = "medscale-0.3.0-py3-none-any.whl"
SDIST = "medscale-0.3.0.tar.gz"


@pytest.fixture
def gate() -> Any:
    spec = importlib.util.spec_from_file_location("medorigin_identity_drift_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / WHEEL).write_bytes(b"SYNTHETIC_WHEEL")
    (dist / SDIST).write_bytes(b"SYNTHETIC_SDIST")
    return dist


def _link_or_skip(source: Path, alias: Path) -> None:
    try:
        os.link(source, alias)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"Unprivileged hardlink unavailable: {type(exc).__name__}")


def test_ordinary_synthetic_dist_remains_accepted(gate: Any, fake_dist: Path) -> None:
    assert gate.read_stable_dist_bytes(fake_dist) == (
        b"SYNTHETIC_WHEEL",
        b"SYNTHETIC_SDIST",
    )


@pytest.mark.parametrize("target_name", [WHEEL, SDIST])
def test_new_external_hardlink_during_pinned_snapshot_is_refused(
    gate: Any, fake_dist: Path, tmp_path: Path, monkeypatch: Any, target_name: str
) -> None:
    target = fake_dist / target_name
    alias = tmp_path / ("outside-wheel" if target_name == WHEEL else "outside-sdist")
    original = gate._read_pinned_regular_bytes
    injected = False

    def create_alias(path: Path, directory_identity: tuple[int, int]) -> bytes:
        nonlocal injected
        raw = original(path, directory_identity)
        if path == target:
            _link_or_skip(target, alias)
            injected = True
        return raw

    monkeypatch.setattr(gate, "_read_pinned_regular_bytes", create_alias)
    with pytest.raises(gate.ProposalVerificationError, match=r"changed|link|identity"):
        gate.read_stable_dist_bytes(fake_dist)
    assert injected
    assert alias.samefile(target)
    assert target.stat().st_nlink >= 2


def test_preexisting_external_hardlink_is_refused(
    gate: Any, fake_dist: Path, tmp_path: Path
) -> None:
    _link_or_skip(fake_dist / WHEEL, tmp_path / "existing-alias")
    with pytest.raises(gate.ProposalVerificationError, match=r"ordinary|changed|link"):
        gate.read_stable_dist_bytes(fake_dist)


@pytest.mark.skipif(os.name != "nt", reason="Windows mode changes lack POSIX ctime guard")
def test_windows_readonly_mode_drift_after_read_is_refused(
    gate: Any, fake_dist: Path, monkeypatch: Any
) -> None:
    target = fake_dist / WHEEL
    original = gate._read_pinned_regular_bytes

    def change_mode(path: Path, directory_identity: tuple[int, int]) -> bytes:
        raw = original(path, directory_identity)
        if path == target:
            os.chmod(target, stat.S_IREAD)
        return raw

    monkeypatch.setattr(gate, "_read_pinned_regular_bytes", change_mode)
    try:
        with pytest.raises(gate.ProposalVerificationError, match=r"changed|mode|identity"):
            gate.read_stable_dist_bytes(fake_dist)
    finally:
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
