"""Adversarial tests for read-only source archive publication allowlisting."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_sdist_publication_scope.py"
ESSENTIAL = (
    "src/medscale/__init__.py",
    "src/medscale/__about__.py",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
)


def _archive(
    path: Path,
    *,
    extras: tuple[str, ...] = (),
    missing: tuple[str, ...] = (),
    symbolic: bool = False,
) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        for name in (*ESSENTIAL, *extras):
            if name in missing:
                continue
            info = tarfile.TarInfo("medscale-0.3.0/" + name)
            if symbolic and name == "README.md":
                info.type = tarfile.SYMTYPE
                info.linkname = "../../secret"
                archive.addfile(info)
            else:
                blob = b"test-only fixture"
                info.size = len(blob)
                archive.addfile(info, io.BytesIO(blob))
    return path


def _run(sdist: Path) -> tuple[int, dict[str, Any]]:
    p = subprocess.run(
        [sys.executable, str(SCRIPT), "--sdist", str(sdist)],
        capture_output=True,
        text=True,
        check=False,
    )
    return p.returncode, cast(dict[str, Any], json.loads(p.stdout))


def test_minimal_whitelist_is_not_publication_authorization(tmp_path: Path) -> None:
    status, report = _run(_archive(tmp_path / "good.tar.gz"))
    assert status == 0
    assert report["status"] == "SDIST_SCOPE_QUALIFIED_ONLY"
    assert report["publication_authorized"] is False
    assert report["members"] == len(ESSENTIAL)


def test_unapproved_source_payload_blocks_archive(tmp_path: Path) -> None:
    extras = (
        "data/patient.json",
        "specs/experiment/artifact.json",
        "notebooks/development.ipynb",
        "apps/workspace/secret.json",
        ".github/workflows/release.yml",
        "../outside.txt",
        "src/other_module/__init__.py",
    )
    for i, extra in enumerate(extras):
        code, result = _run(_archive(tmp_path / f"bad-{i}.tar.gz", extras=(extra,)))
        assert code == 2, extra
        assert result["status"] == "BLOCKED", extra
        assert result["issues"], extra


def test_symbolic_link_is_rejected(tmp_path: Path) -> None:
    code, result = _run(_archive(tmp_path / "link.tar.gz", symbolic=True))
    assert code == 2
    assert any("special" in str(s) for s in result["issues"])


def test_missing_license_is_rejected(tmp_path: Path) -> None:
    code, result = _run(_archive(tmp_path / "missing.tar.gz", missing=("LICENSE",)))
    assert code == 2
    assert any("essential" in str(s) for s in result["issues"])


def test_corrupt_archive_is_rejected(tmp_path: Path) -> None:
    broken = tmp_path / "corrupt.tar.gz"
    broken.write_bytes(b"not a tar file")
    code, result = _run(broken)
    assert code == 2
    assert result["status"] == "BLOCKED"
