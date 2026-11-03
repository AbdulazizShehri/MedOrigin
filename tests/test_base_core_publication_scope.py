"""Adversarial, synthetic-only tests for fail-closed publisher artifact admission."""

from __future__ import annotations

import gzip
import importlib.util
import io
import json
import stat
import struct
import subprocess
import sys
import tarfile
import zipfile
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_base_core_publication_scope.py"


@pytest.fixture
def checker() -> Any:
    spec = importlib.util.spec_from_file_location("medorigin_publish_scope", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def metadata(
    *,
    name: str = "medscale",
    version: str = "0.3.0",
    extra: str | None = None,
    dependency: str | None = None,
    dynamic: str | None = None,
    duplicate_name: bool = False,
) -> bytes:
    doc = EmailMessage()
    doc["Metadata-Version"] = "2.3"
    doc["Name"] = name
    doc["Version"] = version
    if extra is not None:
        doc["Provides-Extra"] = extra
    if dependency is not None:
        doc["Requires-Dist"] = dependency
    if dynamic is not None:
        doc["Dynamic"] = dynamic
    if duplicate_name:
        doc["Name"] = name
    return doc.as_bytes()


def make_dist(
    folder: Path,
    *,
    wheel: bytes | None = None,
    sdist: bytes | None = None,
    duplicate_wheel: bool = False,
    symlink_sdist: bool = False,
) -> Path:
    folder.mkdir(exist_ok=True)
    if wheel is None:
        wheel = metadata()
    if sdist is None:
        sdist = metadata()
    with zipfile.ZipFile(folder / "medscale-0.3.0-py3-none-any.whl", "w") as z:
        z.writestr("medscale-0.3.0.dist-info/METADATA", wheel)
        if duplicate_wheel:
            z.writestr("medscale-9.9.dist-info/METADATA", wheel)
    with tarfile.open(folder / "medscale-0.3.0.tar.gz", "w:gz") as z:
        info = tarfile.TarInfo("medscale-0.3.0/PKG-INFO")
        if symlink_sdist:
            info.type = tarfile.SYMTYPE
            info.linkname = "../../other"
            z.addfile(info)
        else:
            info.size = len(sdist)
            z.addfile(info, io.BytesIO(sdist))
    return folder


def test_base_only_realistic_pair_is_eligible_but_not_authorized(
    checker: Any, tmp_path: Path
) -> None:
    result = checker.inspect(make_dist(tmp_path / "candidate"))
    assert result["status"] == "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
    assert result["versions"] == {"wheel": "0.3.0", "sdist": "0.3.0"}
    assert result["publication_authorized"] is False
    assert result["independent_security_review_complete"] is False


@pytest.mark.parametrize(
    ("wheel", "sdist", "match"),
    [
        (metadata(extra="rq1-runtime-feasibility"), metadata(), "wheel: optional extras"),
        (metadata(), metadata(extra="training-hf-sft"), "sdist: optional extras"),
        (metadata(dependency="pillow==12.3.0"), metadata(), "wheel: runtime dependencies"),
        (metadata(), metadata(dependency="accelerate==1.14.0"), "sdist: runtime dependencies"),
        (metadata(dynamic="Provides-Extra"), metadata(), "dynamic dependency"),
        (metadata(), metadata(dynamic="Requires-Dist"), "dynamic dependency"),
        (
            metadata(version="0.3.0"),
            metadata(version="0.4.0"),
            "source directory version disagrees",
        ),
        (metadata(name="other-project"), metadata(), "unexpected distribution"),
        (metadata(duplicate_name=True), metadata(), "ambiguous Name"),
    ],
)
def test_unqualified_metadata_blocked(
    checker: Any,
    tmp_path: Path,
    wheel: bytes,
    sdist: bytes,
    match: str,
) -> None:
    result = checker.inspect(make_dist(tmp_path / "candidate", wheel=wheel, sdist=sdist))
    assert result["status"] == "BLOCKED"
    assert any(match in str(issue) for issue in result["issues"])
    assert result["publication_authorized"] is False


@pytest.mark.parametrize(
    ("duplicate_wheel", "symlink_sdist", "match"),
    [
        (True, False, "exactly one METADATA"),
        (False, True, "exactly one regular PKG-INFO"),
    ],
)
def test_malicious_archive_metadata_blocked(
    checker: Any,
    tmp_path: Path,
    duplicate_wheel: bool,
    symlink_sdist: bool,
    match: str,
) -> None:
    result = checker.inspect(
        make_dist(
            tmp_path / "candidate", duplicate_wheel=duplicate_wheel, symlink_sdist=symlink_sdist
        )
    )
    assert result["status"] == "BLOCKED"
    assert any(match in str(issue) for issue in result["issues"])


@pytest.mark.parametrize(
    "extra_name",
    [
        "unqualified-9.9.9-py3-none-any.whl",
        "unqualified-9.9.9.tar.gz",
        "SHA256SUMS",
        ".gitignore",
        "unreviewed-sidecar",
    ],
)
def test_unqualified_dist_entries_are_not_silently_uploaded(
    checker: Any, tmp_path: Path, extra_name: str
) -> None:
    folder = make_dist(tmp_path / "extra-dist-file")
    assert checker.inspect(folder)["status"] == "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
    extra = folder / extra_name
    if extra_name == "unreviewed-sidecar":
        extra.mkdir()
    else:
        extra.write_bytes(b"unreviewed synthetic placeholder")
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert "dist: unexpected artifact or sidecar" in result["issues"]
    assert result["publication_authorized"] is False


def test_missing_archive_fails_closed(checker: Any, tmp_path: Path) -> None:
    result = checker.inspect(tmp_path)
    assert result["status"] == "BLOCKED"
    assert len(result["issues"]) == 2


def test_malformed_duplicate_wheel_metadata_blocked(checker: Any, tmp_path: Path) -> None:
    result = checker.inspect(
        make_dist(tmp_path / "candidate", wheel=b"Metadata-Version: 2.3\nName: medscale\n")
    )
    assert result["status"] == "BLOCKED"
    assert any("ambiguous Version" in str(x) for x in result["issues"])


@pytest.mark.parametrize("safe", [True, False])
def test_cli_actual_exit_and_no_release_side_effects(
    tmp_path: Path,
    safe: bool,
) -> None:
    folder = make_dist(
        tmp_path / "candidate",
        wheel=metadata() if safe else metadata(extra="rq1-runtime-feasibility"),
    )
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--dist", str(folder)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == (0 if safe else 2)
    receipt = json.loads(completed.stdout)
    assert receipt["publication_authorized"] is False
    assert receipt["independent_security_review_complete"] is False


def test_gate_wired_before_both_publishers() -> None:
    source = (SCRIPT.parents[1] / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert source.count("python scripts/check_base_core_publication_scope.py --dist dist") == 1
    assert source.index("Block release when optional") < source.index("name: Create Release")
    github_job = source.split("  github-release:", 1)[1].split("  testpypi-publish:", 1)[0]
    pypi_job = source.split("  testpypi-publish:", 1)[1].split("  pr-artifact-build:", 1)[0]
    assert "actions/checkout@" in github_job
    assert "persist-credentials: false" in github_job
    assert "needs: github-release" in pypi_job
    assert "Block TestPyPI" not in pypi_job
    assert "actions/checkout@" not in pypi_job
    assert "permissions:\n      id-token: write" in pypi_job
    assert "contents: write" not in pypi_job


def test_gated_uv_builds_disable_extra_gitignore_sidecar() -> None:
    workflow_dir = SCRIPT.parents[1] / ".github/workflows"
    for filename, expected_builds in (
        ("release.yml", 2),
        ("medorigin-free-linux-proposal-rehearsal.yml", 2),
    ):
        lines = (workflow_dir / filename).read_text(encoding="utf-8").splitlines()
        commands = [line.strip() for line in lines if "uv build " in line]
        assert len(commands) == expected_builds, filename
        assert all("--no-create-gitignore" in line for line in commands), filename


def test_no_independent_approval_or_publisher_code_in_gate() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "github.event_name" not in source
    assert "gh release create" not in source
    assert "twine upload" not in source


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("symlink", "wheel: unsupported member type"),
        ("traversal", "wheel: unsafe member path"),
        ("backslash", "wheel: unsafe member path"),
        ("absolute", "wheel: unsafe member path"),
        ("drive", "wheel: unsafe member path"),
        ("empty-component", "wheel: unsafe member path"),
        ("duplicate", "wheel: duplicate member path"),
        ("case-alias", "wheel: duplicate member path"),
    ],
)
def test_wheel_rejects_unsafe_members_even_with_clean_metadata(
    checker: Any, tmp_path: Path, kind: str, expected: str
) -> None:
    folder = make_dist(tmp_path / kind)
    assert checker.inspect(folder)["status"] == "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
    wheel = folder / "medscale-0.3.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "a") as archive:
        if kind == "symlink":
            member = zipfile.ZipInfo("medscale/unread-link.py")
            member.create_system = 3
            member.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(member, b"../../outside")
        elif kind == "traversal":
            archive.writestr("medscale/../outside.py", b"synthetic")
        elif kind == "backslash":
            # ZipInfo canonicalizes separators on Windows during construction.
            # Force the *stored* ZIP filename bytes to contain a backslash.
            member = zipfile.ZipInfo("medscale/outside.py")
            member.filename = "medscale\\outside.py"
            archive.writestr(member, b"synthetic")
        elif kind == "absolute":
            archive.writestr("/medscale/outside.py", b"synthetic")
        elif kind == "drive":
            archive.writestr("C:/medscale/outside.py", b"synthetic")
        elif kind == "empty-component":
            archive.writestr("medscale//outside.py", b"synthetic")
        elif kind == "duplicate":
            archive.writestr("medscale/duplicate.py", b"synthetic-1")
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr("medscale/duplicate.py", b"synthetic-2")
        else:
            archive.writestr("medscale/Same.py", b"synthetic-1")
            archive.writestr("medscale/same.py", b"synthetic-2")
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read("medscale-0.3.0.dist-info/METADATA") == metadata()
    if kind == "backslash":
        assert b"medscale\\outside.py" in wheel.read_bytes()
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    if kind == "backslash":
        # Windows ZipInfo normalizes the central filename on read; its
        # already-qualified local-name identity guard then catches the
        # raw slash mismatch. POSIX can reject the unsafe name directly.
        assert any(
            message in result["issues"]
            for message in ("wheel: unsafe member path", "wheel: local ZIP filename mismatch")
        )
    else:
        assert expected in result["issues"]
    assert result["publication_authorized"] is False


def test_wheel_forged_inflated_size_fails_closed(checker: Any, tmp_path: Path) -> None:
    folder = make_dist(tmp_path / "bomb")
    wheel = folder / "medscale-0.3.0-py3-none-any.whl"
    raw = bytearray(wheel.read_bytes())
    central_header = raw.find(b"PK\x01\x02")
    assert central_header >= 0
    # Central directory declared original size: no huge allocation needed.
    struct.pack_into("<I", raw, central_header + 24, checker._MAX_SINGLE_MEMBER_BYTES + 1)
    wheel.write_bytes(raw)
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any("wheel: inflated member exceeds budget" in issue for issue in result["issues"])
    assert result["publication_authorized"] is False


@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        ("appended", "wheel: noncanonical ZIP trailer"),
        ("prefixed", "wheel: unaccounted ZIP envelope bytes"),
        ("comment", "wheel: noncanonical ZIP trailer"),
        ("concatenated", "wheel: unaccounted ZIP envelope bytes"),
        ("gap-before-directory", "wheel: hidden ZIP member gap"),
    ],
)
def test_wheel_rejects_unaccounted_physical_payloads(
    checker: Any, tmp_path: Path, variant: str, expected: str
) -> None:
    folder = make_dist(tmp_path / variant)
    wheel = folder / "medscale-0.3.0-py3-none-any.whl"
    original = wheel.read_bytes()
    if variant == "appended":
        wheel.write_bytes(original + b"UNQUALIFIED-TRAILER")
    elif variant == "prefixed":
        wheel.write_bytes(b"UNQUALIFIED-PREFIX" + original)
    elif variant == "gap-before-directory":
        # GitHub artifact and Python ZipFile still see valid METADATA.
        # The previous EOCD-only guard accepted hidden bytes before the
        # central directory when that directory's offset was adjusted.
        eocd = original.rfind(b"PK\x05\x06")
        assert eocd >= 0
        directory_offset = struct.unpack_from("<I", original, eocd + 16)[0]
        gap = b"UNQUALIFIED-INTERNAL-PAYLOAD"
        mutated = bytearray(original[:directory_offset] + gap + original[directory_offset:])
        struct.pack_into("<I", mutated, eocd + len(gap) + 16, directory_offset + len(gap))
        wheel.write_bytes(mutated)
    elif variant == "comment":
        with zipfile.ZipFile(wheel, "a") as archive:
            archive.comment = b"UNQUALIFIED-COMMENT"
    else:
        second = io.BytesIO()
        with zipfile.ZipFile(second, "w") as archive:
            archive.writestr("medscale-0.3.0.dist-info/METADATA", metadata())
        wheel.write_bytes(original + second.getvalue())
    # The standard ZIP parser still reads apparently valid Wheel metadata.
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read("medscale-0.3.0.dist-info/METADATA") == metadata()
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any(expected in issue for issue in result["issues"])
    assert result["publication_authorized"] is False


def test_comment_free_compressed_wheel_still_passes_scope_gate(
    checker: Any, tmp_path: Path
) -> None:
    folder = make_dist(tmp_path / "compressed")
    wheel = folder / "medscale-0.3.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("medscale-0.3.0.dist-info/METADATA", metadata())
    result = checker.inspect(folder)
    assert result["status"] == "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
    assert result["publication_authorized"] is False


@pytest.mark.parametrize(
    ("tamper", "expected"),
    [
        ("local-filename", "wheel: local ZIP filename mismatch"),
        ("local-crc", "wheel: local ZIP header mismatch"),
        ("local-flags", "wheel: local ZIP header mismatch"),
    ],
)
def test_wheel_local_header_matches_central_directory_for_every_member(
    checker: Any, tmp_path: Path, tamper: str, expected: str
) -> None:
    folder = make_dist(tmp_path / tamper)
    wheel = folder / "medscale-0.3.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("medscale/qualified.py", b"fictional-only")
    assert checker.inspect(folder)["status"] == "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
    with zipfile.ZipFile(wheel) as archive:
        target = archive.getinfo("medscale/qualified.py")
        assert archive.read("medscale-0.3.0.dist-info/METADATA") == metadata()
    raw = bytearray(wheel.read_bytes())
    if tamper == "local-filename":
        name_offset = target.header_offset + checker._ZIP_LOCAL_HEADER.size
        original = b"medscale/qualified.py"
        replacement = b"medscale/untrusted.py"
        assert len(original) == len(replacement)
        assert raw[name_offset : name_offset + len(original)] == original
        raw[name_offset : name_offset + len(original)] = replacement
    elif tamper == "local-crc":
        # ZIP local CRC32 begins 14 bytes after the local signature.
        struct.pack_into("<I", raw, target.header_offset + 14, target.CRC ^ 1)
    else:
        # Only the local flags change. The central header remains unchanged.
        struct.pack_into("<H", raw, target.header_offset + 6, target.flag_bits ^ 0x800)
    wheel.write_bytes(raw)
    # The metadata entry was not modified; the old scope gate accepted the
    # malformed extra member without reading its local header identity.
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read("medscale-0.3.0.dist-info/METADATA") == metadata()
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any(expected in issue for issue in result["issues"])
    assert result["publication_authorized"] is False


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        ("symlink", "sdist: unsupported member type"),
        ("hardlink", "sdist: unsupported member type"),
        ("device", "sdist: unsupported member type"),
        ("fifo", "sdist: unsupported member type"),
        ("traversal", "sdist: unsafe member path"),
        ("absolute", "sdist: unsafe member path"),
        ("backslash", "sdist: unsafe member path"),
        ("double-slash", "sdist: unsafe member path"),
        ("reserved-device-name", "sdist: unsafe member path"),
        ("control-character", "sdist: unsafe member path"),
        ("trailing-dot", "sdist: unsafe member path"),
        ("duplicate", "sdist: duplicate member path"),
        ("case-alias", "sdist: duplicate member path"),
    ],
)
def test_sdist_rejects_unsafe_non_metadata_members(
    checker: Any, tmp_path: Path, kind: str, message: str
) -> None:
    folder = make_dist(tmp_path / kind)
    assert checker.inspect(folder)["status"] == "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
    archive_path = folder / "medscale-0.3.0.tar.gz"
    names = {
        "traversal": "medscale-0.3.0/../escape.py",
        "absolute": "/medscale-0.3.0/escape.py",
        "backslash": "medscale-0.3.0\\escape.py",
        "double-slash": "medscale-0.3.0//escape.py",
        "reserved-device-name": "medscale-0.3.0/CON.txt",
        "control-character": "medscale-0.3.0/line\nbreak.py",
        "trailing-dot": "medscale-0.3.0/file.",
    }
    with tarfile.open(archive_path, "w:gz") as archive:
        info = tarfile.TarInfo("medscale-0.3.0/PKG-INFO")
        doc = metadata()
        info.size = len(doc)
        archive.addfile(info, io.BytesIO(doc))
        if kind in {"symlink", "hardlink", "device", "fifo"}:
            special = tarfile.TarInfo("medscale-0.3.0/special")
            special.type = {
                "symlink": tarfile.SYMTYPE,
                "hardlink": tarfile.LNKTYPE,
                "device": tarfile.CHRTYPE,
                "fifo": tarfile.FIFOTYPE,
            }[kind]
            if kind in {"symlink", "hardlink"}:
                special.linkname = "../../unapproved"
            archive.addfile(special)
        elif kind in {"duplicate", "case-alias"}:
            first = tarfile.TarInfo("medscale-0.3.0/Alpha.py")
            first.size = 1
            archive.addfile(first, io.BytesIO(b"a"))
            second = tarfile.TarInfo(
                "medscale-0.3.0/Alpha.py"
                if kind == "duplicate"
                else "medscale-0.3.0/alpha.py"
            )
            second.size = 1
            archive.addfile(second, io.BytesIO(b"b"))
        else:
            file = tarfile.TarInfo(names[kind])
            file.size = 1
            archive.addfile(file, io.BytesIO(b"x"))
    with tarfile.open(archive_path, "r:gz") as archive:
        assert archive.extractfile("medscale-0.3.0/PKG-INFO").read() == metadata()
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert message in result["issues"]
    assert result["publication_authorized"] is False


def test_sdist_accepts_normal_directory_and_member(checker: Any, tmp_path: Path) -> None:
    folder = make_dist(tmp_path / "normal-member")
    archive_path = folder / "medscale-0.3.0.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        doc = metadata()
        info = tarfile.TarInfo("medscale-0.3.0/PKG-INFO")
        info.size = len(doc)
        archive.addfile(info, io.BytesIO(doc))
        folder_info = tarfile.TarInfo("medscale-0.3.0/medscale/")
        folder_info.type = tarfile.DIRTYPE
        archive.addfile(folder_info)
        file = tarfile.TarInfo("medscale-0.3.0/medscale/__init__.py")
        file.size = 1
        archive.addfile(file, io.BytesIO(b"x"))
    receipt = checker.inspect(folder)
    assert receipt["status"] == "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
    assert receipt["publication_authorized"] is False


def test_sdist_forged_inflated_size_fails_before_extraction(checker: Any, tmp_path: Path) -> None:
    folder = make_dist(tmp_path / "bomb")
    oversized = tarfile.TarInfo("medscale-0.3.0/huge-data.bin")
    oversized.size = checker._MAX_SINGLE_MEMBER_BYTES + 1
    # A checksum-valid header advertises a large payload that is NOT present;
    # the metadata gate must reject it before attempting to decompress data.
    (folder / "medscale-0.3.0.tar.gz").write_bytes(
        gzip.compress(oversized.tobuf() + b"\0" * 1024, mtime=0)
    )
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any("sdist: inflated member exceeds budget" in issue for issue in result["issues"])
    assert result["publication_authorized"] is False


def test_wheel_member_count_budget_fails_closed(checker: Any, tmp_path: Path) -> None:
    folder = make_dist(tmp_path / "many-wheel")
    wheel = folder / "medscale-0.3.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for n in range(checker._MAX_MEMBERS):
            archive.writestr(f"medscale/junk_{n:05}.txt", b"")
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any("wheel: archive member limit exceeded" in issue for issue in result["issues"])


def test_sdist_member_count_budget_fails_closed(checker: Any, tmp_path: Path) -> None:
    folder = make_dist(tmp_path / "many-sdist")
    sdist = folder / "medscale-0.3.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo("medscale-0.3.0/PKG-INFO")
        source = metadata()
        info.size = len(source)
        archive.addfile(info, io.BytesIO(source))
        for n in range(checker._MAX_MEMBERS):
            directory = tarfile.TarInfo(f"medscale-0.3.0/extra-{n:05}/")
            directory.type = tarfile.DIRTYPE
            archive.addfile(directory)
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any("sdist: archive member limit exceeded" in issue for issue in result["issues"])


def test_sdist_duplicate_metadata_fails_closed(checker: Any, tmp_path: Path) -> None:
    folder = make_dist(tmp_path / "duplicate")
    sdist = folder / "medscale-0.3.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        for _ in range(2):
            raw = metadata()
            item = tarfile.TarInfo("medscale-0.3.0/PKG-INFO")
            item.size = len(raw)
            archive.addfile(item, io.BytesIO(raw))
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any("sdist: exactly one regular PKG-INFO" in issue for issue in result["issues"])


def test_sdist_bounded_inflation_includes_tar_envelope(
    checker: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    folder = make_dist(tmp_path / "inflation-envelope")
    # Small budget forces an otherwise-valid TAR envelope over the limit,
    # proving the stream reader counts headers/padding and not only file sizes.
    monkeypatch.setattr(checker, "_MAX_TAR_INFLATED_BYTES", 1024)
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any("sdist: inflated TAR envelope exceeds budget" in issue for issue in result["issues"])
    assert result["publication_authorized"] is False


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_artifact_filename_version_mismatch_blocked(
    checker: Any, tmp_path: Path, kind: str
) -> None:
    folder = make_dist(tmp_path / "filename-mismatch")
    if kind == "wheel":
        original = folder / "medscale-0.3.0-py3-none-any.whl"
        original.rename(folder / "medscale-0.4.0-py3-none-any.whl")
    else:
        original = folder / "medscale-0.3.0.tar.gz"
        original.rename(folder / "medscale-0.4.0.tar.gz")
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any(
        f"{kind}: filename does not match metadata version" in issue for issue in result["issues"]
    )
    assert result["publication_authorized"] is False


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_embedded_metadata_directory_version_mismatch_blocked(
    checker: Any, tmp_path: Path, kind: str
) -> None:
    folder = make_dist(tmp_path / "embedded-mismatch")
    if kind == "wheel":
        path = folder / "medscale-0.3.0-py3-none-any.whl"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("medscale-0.4.0.dist-info/METADATA", metadata())
        expected = "wheel: dist-info version disagrees with metadata"
    else:
        path = folder / "medscale-0.3.0.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            raw = metadata()
            entry = tarfile.TarInfo("medscale-0.4.0/PKG-INFO")
            entry.size = len(raw)
            archive.addfile(entry, io.BytesIO(raw))
        expected = "sdist: source directory version disagrees with metadata"
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert expected in result["issues"]
    assert result["publication_authorized"] is False


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("appended-bytes", "sdist: appended gzip data"),
        ("concatenated-member", "sdist: appended gzip data"),
        ("truncated-footer", "sdist: incomplete gzip stream"),
        ("hidden-tar-payload", "sdist: hidden TAR trailer"),
        ("damaged-crc", "sdist: invalid archive"),
    ],
)
def test_sdist_publisher_gate_rejects_hidden_physical_payloads(
    checker: Any, tmp_path: Path, kind: str, expected: str
) -> None:
    folder = make_dist(tmp_path / kind)
    path = folder / "medscale-0.3.0.tar.gz"
    original = path.read_bytes()
    if kind == "appended-bytes":
        altered = original + b"secret-data"
    elif kind == "concatenated-member":
        altered = original + gzip.compress(b"hidden-member", mtime=0)
    elif kind == "truncated-footer":
        altered = original[:-4]
    elif kind == "damaged-crc":
        damaged = bytearray(original)
        damaged[-8] ^= 0x01
        altered = bytes(damaged)
    else:
        inflated = bytearray(gzip.decompress(original))
        assert len(inflated) > 4096
        inflated[4096] = 0x5A
        altered = gzip.compress(inflated, mtime=0)
    path.write_bytes(altered)
    result = checker.inspect(folder)
    assert result["status"] == "BLOCKED"
    assert any(expected in issue for issue in result["issues"])
    assert result["publication_authorized"] is False
