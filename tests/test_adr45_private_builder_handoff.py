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


def test_pinned_identity_detects_file_mode_and_hardlink_count_change(
    gate: Any, tmp_path: Path
) -> None:
    from types import SimpleNamespace

    file = tmp_path / "regular"
    file.write_bytes(b"STABLE")
    original = file.stat()
    fields = {
        name: getattr(original, name)
        for name in (
            "st_dev",
            "st_ino",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
            "st_mode",
            "st_nlink",
        )
    }
    changed_mode = SimpleNamespace(**{**fields, "st_mode": fields["st_mode"] ^ 0o200})
    changed_links = SimpleNamespace(**{**fields, "st_nlink": fields["st_nlink"] + 1})
    assert gate._identity(original) != gate._identity(changed_mode)
    assert gate._identity(original) != gate._identity(changed_links)


def test_handoff_detects_hardlink_alias_created_after_wheel_snapshot(
    gate: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    src = make_builder(tmp_path / "builder")
    outside = tmp_path / "new_external_hardlink"
    original = gate._pinned_bytes

    def raced(path: Path, *, limit: int, parent_id: tuple[int, int]) -> bytes:
        data = original(path, limit=limit, parent_id=parent_id)
        if path.name == WHEEL:
            try:
                os.link(path, outside)
            except (OSError, NotImplementedError):
                pytest.skip("Unable to create controlled hardlink race on this filesystem")
        return data

    monkeypatch.setattr(gate, "_pinned_bytes", raced)
    with pytest.raises(gate.HandoffError, match=r"changed|hardlink|identity"):
        gate.handoff(src, tmp_path / "dist")
    assert not (tmp_path / "dist").exists()
    if outside.exists():
        outside.unlink()


def test_handoff_never_writes_to_untrusted_destination_path_before_publish(
    gate: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    """The caller-visible destination must never receive in-progress bytes."""
    source = make_builder(tmp_path / "builder")
    destination = tmp_path / "dist"
    original_open = os.open
    opened: list[Path] = []

    def monitor_open(path: str | os.PathLike[str], flags: int, *args: Any, **kwargs: Any) -> int:
        entry = Path(path)
        opened.append(entry)
        if entry.parent == destination:
            raise AssertionError("early write into caller destination")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(gate.os, "open", monitor_open)
    receipt = gate.handoff(source, destination)
    assert receipt["status"] == "ADR45_PRIVATE_TWO_ARCHIVES_STAGED"
    assert destination.is_dir()
    assert (destination / WHEEL).read_bytes() == b"SYNTHETIC_WHEEL"
    assert (destination / SDIST).read_bytes() == b"SYNTHETIC_SDIST"
    assert all(p.parent != destination for p in opened)


def test_concurrent_destination_injected_at_commit_is_never_replaced(
    gate: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    """Atomic no-replace finalization preserves a racing caller-owned dir."""
    source = make_builder(tmp_path / "builder")
    dest = tmp_path / "dist"
    original_commit = gate._commit_private_staging

    def inject_caller_dir(staging: Path, intended: Path) -> None:
        assert intended == dest
        dest.mkdir()
        (dest / "foreign").write_bytes(b"DO_NOT_DELETE")
        original_commit(staging, intended)

    monkeypatch.setattr(gate, "_commit_private_staging", inject_caller_dir)
    with pytest.raises(gate.HandoffError, match=r"destination|exists|replace"):
        gate.handoff(source, dest)
    assert (dest / "foreign").read_bytes() == b"DO_NOT_DELETE"
    assert list(dest.iterdir()) == [dest / "foreign"]


def test_error_after_concurrent_target_creation_never_deletes_foreign_directory(
    gate: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    """A failed temporary write may clean only its own staged directory."""
    source = make_builder(tmp_path / "builder")
    dest = tmp_path / "dist"
    original_open = os.open
    injected = False

    def fail_first_wheel(
        path: str | os.PathLike[str], flags: int, *args: Any, **kwargs: Any
    ) -> int:
        nonlocal injected
        if Path(path).name == WHEEL and not injected:
            injected = True
            dest.mkdir()
            (dest / "foreign").write_bytes(b"STILL_HERE")
            raise OSError("synthetic private copy failure")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(gate.os, "open", fail_first_wheel)
    with pytest.raises(gate.HandoffError, match=r"changed|unreadable|copy|destination"):
        gate.handoff(source, dest)
    assert injected
    assert (dest / "foreign").read_bytes() == b"STILL_HERE"
    assert list(dest.iterdir()) == [dest / "foreign"]


def test_no_stray_private_directory_after_success_or_failure(
    gate: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    """Temporary stage names may not be orphaned inside the parent."""
    source = make_builder(tmp_path / "builder")
    destination = tmp_path / "dist"
    gate.handoff(source, destination)
    assert {p.name for p in tmp_path.iterdir()} == {"builder", "dist"}
    assert not any("adr45" in p.name and p.name != "dist" for p in tmp_path.iterdir())
