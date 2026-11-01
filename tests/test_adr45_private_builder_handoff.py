"""Test-first fail-closed tests for unpublished Windows/Linux ADR-0045 build handoff.

Source-only synthetic bytes; not a package publisher or an ADR approval.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/qa/adr45_private_builder_handoff.py"
WHEEL = "medscale-0.3.0-py3-none-any.whl"
SDIST = "medscale-0.3.0.tar.gz"


@pytest.fixture
def gate() -> Any:
    spec = importlib.util.spec_from_file_location("adr45_private_handoff", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(spec.name, None)


def make_builder(root: Path) -> Path:
    root.mkdir()
    (root / WHEEL).write_bytes(b"SYNTHETIC_WHEEL")
    (root / SDIST).write_bytes(b"SYNTHETIC_SDIST")
    (root / ".gitignore").write_bytes(b"*\n")
    return root


def test_private_exact_two_archives_and_receipts(gate: Any, tmp_path: Path) -> None:
    src = make_builder(tmp_path / "builder")
    dest = tmp_path / "dist"
    receipt = gate.handoff(src, dest)
    assert receipt["status"] == "ADR45_PRIVATE_TWO_ARCHIVES_STAGED"
    assert receipt["publication_authorized"] is False
    assert {p.name for p in dest.iterdir()} == {WHEEL, SDIST}
    assert (dest / WHEEL).read_bytes() == b"SYNTHETIC_WHEEL"
    assert (dest / SDIST).read_bytes() == b"SYNTHETIC_SDIST"
    assert set(receipt["sha256"]) == {WHEEL, SDIST}


@pytest.mark.parametrize("extra", ["unapproved.whl", "unexpected.txt", "test-dir"])
def test_builder_extra_item_never_permitted(gate: Any, tmp_path: Path, extra: str) -> None:
    src = make_builder(tmp_path / "builder")
    path = src / extra
    if extra == "test-dir":
        path.mkdir()
    else:
        path.write_bytes(b"EVIL")
    with pytest.raises(gate.HandoffError, match=r"builder|unexpected|exact"):
        gate.handoff(src, tmp_path / "dist")
    assert not (tmp_path / "dist").exists()


def test_builder_link_refused_without_link_following(gate: Any, tmp_path: Path) -> None:
    src = make_builder(tmp_path / "builder")
    target = tmp_path / "foreign"
    target.write_bytes(b"FOREIGN")
    wheel = src / WHEEL
    wheel.unlink()
    try:
        wheel.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("unprivileged symlink not supported on this Windows host")
    with pytest.raises(gate.HandoffError, match=r"symlink|regular"):
        gate.handoff(src, tmp_path / "dist")
    assert not (tmp_path / "dist").exists()


def test_builder_hardlink_not_promoted(gate: Any, tmp_path: Path) -> None:
    src = make_builder(tmp_path / "builder")
    wheel = src / WHEEL
    other = tmp_path / "another-hardlink"
    try:
        os.link(wheel, other)
    except (OSError, NotImplementedError):
        pytest.skip("hardlink creation not supported on this test filesystem")
    with pytest.raises(gate.HandoffError, match=r"hardlink|regular"):
        gate.handoff(src, tmp_path / "dist")
    assert not (tmp_path / "dist").exists()


def test_builder_directory_replaced_with_symlink(gate: Any, tmp_path: Path) -> None:
    source = make_builder(tmp_path / "source")
    link = tmp_path / "link"
    try:
        link.symlink_to(source, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlink creation unavailable")
    with pytest.raises(gate.HandoffError, match=r"directory|symlink"):
        gate.handoff(link, tmp_path / "dist")


def test_over_budget_no_copy(gate: Any, monkeypatch: Any, tmp_path: Path) -> None:
    src = make_builder(tmp_path / "builder")
    monkeypatch.setattr(gate, "MAX_ARTIFACT_BYTES", 5)
    with pytest.raises(gate.HandoffError, match=r"size|budget"):
        gate.handoff(src, tmp_path / "dist")
    assert not (tmp_path / "dist").exists()


def test_target_must_not_exist_and_never_overwrite(gate: Any, tmp_path: Path) -> None:
    src = make_builder(tmp_path / "builder")
    dest = tmp_path / "dist"
    dest.mkdir()
    important = dest / "important"
    important.write_bytes(b"DO_NOT_TOUCH")
    with pytest.raises(gate.HandoffError, match=r"destination|exists"):
        gate.handoff(src, dest)
    assert important.read_bytes() == b"DO_NOT_TOUCH"


def test_unexpected_builder_gitignore_link_refused(gate: Any, tmp_path: Path) -> None:
    src = make_builder(tmp_path / "builder")
    target = tmp_path / "foreign"
    target.write_bytes(b"NO")
    gi = src / ".gitignore"
    gi.unlink()
    try:
        gi.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(gate.HandoffError, match=r"symlink|regular"):
        gate.handoff(src, tmp_path / "dist")


def test_handoff_never_issues_publication_claim(gate: Any, tmp_path: Path) -> None:
    receipt = gate.handoff(make_builder(tmp_path / "builder"), tmp_path / "dist")
    assert receipt.get("publication_authorized") is False
    assert receipt.get("adr_0045_accepted") is False
    assert receipt.get("status") != "RELEASE_READY"
