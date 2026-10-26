"""Unpublished ADR-0045 cross-platform archive diagnostics (synthetic fixtures)."""

from __future__ import annotations

import gzip
import importlib.util
import io
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/compare_medorigin_base_only_archives.py"


@pytest.fixture
def audit() -> Any:
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location("medorigin_archive_compare", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT.parent))


def _make_pair(folder: Path, creator: int, timestamp: int, altered: bool = False) -> None:
    folder.mkdir()
    with zipfile.ZipFile(folder / "medscale-0.3.0-py3-none-any.whl", "w") as out:
        info = zipfile.ZipInfo("medscale/safe.py", (2020, 1, 1, 0, 0, 0))
        info.create_system = creator
        info.compress_type = zipfile.ZIP_DEFLATED
        out.writestr(info, b"safe = True\n" if not altered else b"unsafe = True\n")
    # Write a qualified simple gzip envelope: tarfile.open(path, "w:gz")
    # adds a filename (FNAME) gzip header flag, which the stricter source-bound
    # verifier correctly rejects. Keep the verifier strict and fix this fixture.
    tar = io.BytesIO()
    with tarfile.open(fileobj=tar, mode="w") as out:
        data = b"safe = True\n"
        info = tarfile.TarInfo("medscale-0.3.0/medscale/safe.py")
        info.size = len(data)
        info.mtime = timestamp
        out.addfile(info, io.BytesIO(data))
    (folder / "medscale-0.3.0.tar.gz").write_bytes(gzip.compress(tar.getvalue(), mtime=0))


def test_source_bound_equal_members_different_envelopes(
    audit: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    _make_pair(left, 0, 10)
    _make_pair(right, 3, 20)
    calls: list[Path] = []

    def fake_verification(_repo: Path, dist: Path) -> dict[str, str]:
        calls.append(dist)
        return {"source_git_commit": "test-source"}

    monkeypatch.setattr(audit, "verify", fake_verification)
    result = audit.compare(ROOT, left, right)
    assert calls == [left.resolve(), right.resolve()]
    assert result["publication_authorized"] is False
    assert result["adr_0045_accepted"] is False
    assert result["status"] == "SOURCE_BOUND_MEMBERS_EQUAL_ARCHIVE_ENVELOPES_DIFFER"
    assert result["wheel"]["archive_header_difference"]["changed_count"] == 1
    assert result["sdist"]["archive_header_difference"]["changed_count"] == 1
    assert result["wheel"]["member_fingerprint"] == audit._fingerprint(
        {"medscale/safe.py": b"safe = True\n"}
    )


def test_byte_identical_copy(audit: Any, monkeypatch: Any, tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    _make_pair(left, 3, 0)
    right.mkdir()
    for name in (audit.WHEEL, audit.SDIST):
        shutil.copyfile(left / name, right / name)
    monkeypatch.setattr(audit, "verify", lambda *_: {"source_git_commit": "test-source"})
    result = audit.compare(ROOT, left, right)
    assert result["status"] == "SOURCE_BOUND_ARCHIVES_BYTE_IDENTICAL"
    assert result["wheel"]["archive_bytes_identical"]
    assert result["sdist"]["archive_bytes_identical"]


def test_strict_mode_refuses_equal_members_with_different_archives(
    audit: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    _make_pair(left, 0, 10)
    _make_pair(right, 3, 20)
    monkeypatch.setattr(audit, "verify", lambda *_: {"source_git_commit": "test-source"})
    with pytest.raises(audit.ProposalVerificationError, match="require-identical"):
        audit.compare(ROOT, left, right, require_identical=True)


def test_strict_mode_passes_identical_archives(
    audit: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    _make_pair(left, 3, 0)
    right.mkdir()
    for name in (audit.WHEEL, audit.SDIST):
        shutil.copyfile(left / name, right / name)
    monkeypatch.setattr(audit, "verify", lambda *_: {"source_git_commit": "test-source"})
    result = audit.compare(ROOT, left, right, require_identical=True)
    assert result["status"] == "SOURCE_BOUND_ARCHIVES_BYTE_IDENTICAL"


def test_gate_must_run_first(audit: Any, tmp_path: Path) -> None:
    with pytest.raises(audit.ProposalVerificationError):
        audit.compare(ROOT, tmp_path / "not-a-dist", tmp_path / "also-not-a-dist")


def test_reject_member_differences_even_if_mocked_gate_says_pass(
    audit: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    _make_pair(left, 3, 0)
    _make_pair(right, 3, 0, altered=True)
    monkeypatch.setattr(audit, "verify", lambda *_: {"source_git_commit": "test-source"})
    with pytest.raises(audit.ProposalVerificationError, match="member bytes differ"):
        audit.compare(ROOT, left, right)


def test_refuses_same_directory(audit: Any, tmp_path: Path) -> None:
    with pytest.raises(audit.ProposalVerificationError, match="distinct directories"):
        audit.compare(ROOT, tmp_path, tmp_path)


def test_same_tar_bytes_different_gzip_compression(
    audit: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    _make_pair(left, 3, 0)
    right.mkdir()
    shutil.copyfile(left / audit.WHEEL, right / audit.WHEEL)
    tar = gzip.decompress((left / audit.SDIST).read_bytes())
    # Use a larger, compressible valid TAR payload while keeping every member unchanged.
    (left / audit.SDIST).write_bytes(gzip.compress(tar, compresslevel=1, mtime=0))
    (right / audit.SDIST).write_bytes(gzip.compress(tar, compresslevel=9, mtime=0))
    monkeypatch.setattr(audit, "verify", lambda *_: {"source_git_commit": "test-source"})
    result = audit.compare(ROOT, left, right)
    assert result["sdist"]["decompressed_tar_identical"]
    assert not result["sdist"]["archive_bytes_identical"]
    assert result["wheel"]["compressed_member_streams_identical"]


def test_equal_zip_members_different_compression_streams(
    audit: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    _make_pair(left, 3, 0)
    _make_pair(right, 3, 0)
    payload = b"algorithm=deterministic\n" * 10000
    for folder, level in ((left, 1), (right, 9)):
        with zipfile.ZipFile(
            folder / audit.WHEEL,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=level,
        ) as archive:
            archive.writestr("medscale/safe.py", payload)
    monkeypatch.setattr(audit, "verify", lambda *_: {"source_git_commit": "test-source"})
    result = audit.compare(ROOT, left, right)
    assert result["wheel"]["member_count"] == 1
    assert result["wheel"]["compressed_member_streams_identical"] is False
    assert not result["wheel"]["archive_bytes_identical"]
    assert result["sdist"]["decompressed_tar_identical"]
