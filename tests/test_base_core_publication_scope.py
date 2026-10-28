"""Adversarial, synthetic-only tests for fail-closed publisher artifact admission."""

from __future__ import annotations

import gzip
import importlib.util
import io
import json
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


def test_no_independent_approval_or_publisher_code_in_gate() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "github.event_name" not in source
    assert "gh release create" not in source
    assert "twine upload" not in source


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
