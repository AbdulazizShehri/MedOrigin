"""Offline, fail-closed source-pinned QA handoff assembly/adversarial tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import warnings
import zipfile
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "assemble_medorigin_exact_head_qa.py"


@pytest.fixture
def maker() -> Any:
    spec = importlib.util.spec_from_file_location("medorigin_exact_head_qa", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def files(maker: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    result = {
        name: ("synthetic test " + name).encode()
        for name in maker.MEMBERS
        if name not in {maker.MANIFEST, maker.CHECKSUMS, maker.PROVENANCE}
    }
    result[f"artifacts/{maker.WHEEL}"] = b"fictional-wheel-bytes"
    result[f"artifacts/{maker.SDIST}"] = b"fictional-sdist-bytes"
    monkeypatch.setattr(
        maker,
        "PINNED",
        {
            maker.WHEEL: maker.sha(result[f"artifacts/{maker.WHEEL}"]),
            maker.SDIST: maker.sha(result[f"artifacts/{maker.SDIST}"]),
        },
    )
    provenance = {
        "source_git_commit": maker.SOURCE_SHA,
        "publication_authorized": False,
        "frozen_pyproject_sha256": maker.FROZEN_PYPROJECT,
        "frozen_lock_sha256": maker.FROZEN_UV_LOCK,
    }
    result[maker.PROVENANCE] = json.dumps(provenance).encode()
    refresh(maker, result)
    return result


def refresh(maker: Any, files: dict[str, bytes]) -> None:
    files[maker.MANIFEST] = json.dumps(maker.manifest_contract()).encode()
    files[maker.CHECKSUMS] = (
        "\n".join(
            f"{maker.sha(files[name])}  {name}" for name in sorted(files) if name != maker.CHECKSUMS
        )
        + "\n"
    ).encode("ascii")


def write_archive(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "x") as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, files[name])


def test_synthetic_exact_head_member_contract(maker: Any, files: dict[str, bytes]) -> None:
    result = maker.check_members(files)
    assert result["status"] == "MEDORIGIN_EXACT_HEAD_UNPUBLISHED_QA_PASS"
    assert result["member_count"] == 16
    assert result["source_git_commit"] == maker.SOURCE_SHA
    assert result["publication_authorized"] is False
    assert result["independent_review_completed"] is False


def test_archive_verification_and_external_digest(
    maker: Any, files: dict[str, bytes], tmp_path: Path
) -> None:
    out = tmp_path / "candidate.zip"
    write_archive(out, files)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    assert maker.verify(out, sha)["member_count"] == 16
    with pytest.raises(maker.ExactHeadQualificationError):
        maker.verify(out, "0" * 64)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "content",
        "replacement-and-rehash",
        "fake-approval",
        "source-forgery",
        "duplicate-json",
    ],
)
def test_adversarial_member_mutations_rejected(
    maker: Any,
    files: dict[str, bytes],
    mutation: str,
) -> None:
    altered = files.copy()
    if mutation == "missing":
        del altered[maker.PROVENANCE]
    elif mutation == "extra":
        altered["../../unsafe.txt"] = b"unsafe"
    elif mutation == "content":
        altered[maker.README] += b"corrupt"
    elif mutation == "replacement-and-rehash":
        altered[f"artifacts/{maker.WHEEL}"] = b"changed artifact"
        refresh(maker, altered)
    elif mutation == "fake-approval":
        document = maker.manifest_contract()
        document["publication_authorized"] = True
        altered[maker.MANIFEST] = json.dumps(document).encode()
        altered[maker.CHECKSUMS] = (
            "\n".join(
                f"{maker.sha(altered[name])}  {name}"
                for name in sorted(altered)
                if name != maker.CHECKSUMS
            )
            + "\n"
        ).encode()
    elif mutation == "source-forgery":
        receipt = json.loads(altered[maker.PROVENANCE])
        receipt["source_git_commit"] = "0" * 40
        altered[maker.PROVENANCE] = json.dumps(receipt).encode()
        refresh(maker, altered)
    else:
        altered[maker.PROVENANCE] = b'{"source_git_commit":"fake","source_git_commit":"fake"}'
        refresh(maker, altered)
    with pytest.raises(maker.ExactHeadQualificationError):
        maker.check_members(altered)


def test_duplicate_archive_entry_is_rejected(
    maker: Any, files: dict[str, bytes], tmp_path: Path
) -> None:
    out = tmp_path / "duplicate.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(out, "x") as archive:
            archive.writestr(maker.MANIFEST, files[maker.MANIFEST])
            archive.writestr(maker.MANIFEST, files[maker.MANIFEST])
    with pytest.raises(maker.ExactHeadQualificationError):
        maker.verify(out)


def test_symlink_archive_entry_is_rejected(maker: Any, tmp_path: Path) -> None:
    out = tmp_path / "linked.zip"
    with zipfile.ZipFile(out, "x") as archive:
        info = zipfile.ZipInfo(maker.MANIFEST)
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"../external")
    with pytest.raises(maker.ExactHeadQualificationError):
        maker.verify(out)


def test_oversized_external_hash_path_rejected(
    maker: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "large.zip"
    path.write_bytes(b"x" * 8)
    monkeypatch.setattr(maker, "MAX_ZIP", 7)
    with pytest.raises(maker.ExactHeadQualificationError, match="oversized"):
        maker.verify(path, "0" * 64)


def test_source_builder_pins_git_sha_and_core_bytes(
    maker: Any,
    files: dict[str, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    for name in (maker.WHEEL, maker.SDIST):
        (artifacts / name).write_bytes(files[f"artifacts/{name}"])
    provenance = tmp_path / "provenance.json"
    provenance.write_bytes(files[maker.PROVENANCE])

    def simulated_git(*args: str) -> bytes:
        if args == ("status", "--porcelain"):
            return b""
        if args == ("rev-parse", "--verify", maker.SOURCE_SHA):
            return str(maker.SOURCE_SHA).encode("ascii") + b"\n"
        if args[0] == "show" and args[1].startswith(maker.SOURCE_SHA + ":"):
            return files[args[1].split(":", 1)[1]]
        raise AssertionError("unanticipated Git access")

    monkeypatch.setattr(maker, "git", simulated_git)
    built = maker.construct(artifacts, provenance)
    assert maker.check_members(built)["member_count"] == 16
    (artifacts / maker.SDIST).write_bytes(b"forged")
    with pytest.raises(maker.ExactHeadQualificationError, match="bytes differ"):
        maker.construct(artifacts, provenance)


def test_builder_produces_deterministic_and_no_overwrite_zip(
    maker: Any,
    files: dict[str, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maker, "construct", lambda _a, _p: files)
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()
    path_a = one / maker.ZIP_NAME
    path_b = two / maker.ZIP_NAME
    result_a = maker.build(path_a, tmp_path, tmp_path / "none")
    result_b = maker.build(path_b, tmp_path, tmp_path / "none")
    assert result_a["zip_sha256"] == result_b["zip_sha256"]
    assert path_a.read_bytes() == path_b.read_bytes()
    assert result_a["publication_authorized"] is False
    with pytest.raises(maker.ExactHeadQualificationError):
        maker.build(path_a, tmp_path, tmp_path / "none")


def test_no_publication_operations_in_source() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    for operation in ("gh release create", "git push", "git tag", "twine upload", "hf upload"):
        assert operation not in source
