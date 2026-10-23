"""Adversarial tests of MedOrigin Core source-distribution integrity."""

from __future__ import annotations

import hashlib
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
    "apps/workspace/LICENSE",
    "MEDORIGIN_SOURCE_PROVENANCE.json",
)


def _archive(
    dest: Path,
    *,
    extra: str | None = None,
    missing: str | None = None,
    symbolic: bool = False,
    altered: str | None = None,
) -> Path:
    files = {
        name: b"test-only fixture"
        for name in ESSENTIAL
        if name != "MEDORIGIN_SOURCE_PROVENANCE.json"
    }
    source = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in files.items()
        if name.startswith("src/medscale/")
        or name in {"README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "apps/workspace/LICENSE"}
    }
    receipt = {
        "schema": "MEDORIGIN-CORE-PROJECTION-1",
        "source_files": source,
        "source_file_count": len(source),
        "projected_pyproject_sha256": hashlib.sha256(files["pyproject.toml"]).hexdigest(),
        "publication_authorized": False,
    }
    files["MEDORIGIN_SOURCE_PROVENANCE.json"] = json.dumps(receipt).encode("utf-8")
    if altered is not None:
        files[altered] = b"unrecorded tampering"
    if extra is not None:
        files[extra] = b"not permitted"
    with tarfile.open(dest, "w:gz") as tar:
        for name, data in files.items():
            if name == missing:
                continue
            info = tarfile.TarInfo("medscale-0.3.0/" + name)
            if symbolic and name == "README.md":
                info.type = tarfile.SYMTYPE
                info.linkname = "../../secret"
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return dest


def _run(source: Path) -> tuple[int, dict[str, Any]]:
    run = subprocess.run(
        [sys.executable, str(SCRIPT), "--sdist", str(source)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.stdout, run.stderr
    return run.returncode, cast(dict[str, Any], json.loads(run.stdout))


def test_allowlisted_archive_does_not_approve_publication(tmp_path: Path) -> None:
    status, output = _run(_archive(tmp_path / "ok.tar.gz"))
    assert status == 0
    assert output["status"] == "SDIST_SCOPE_QUALIFIED_ONLY"
    assert output["publication_authorized"] is False
    assert output["members"] == len(ESSENTIAL)


def test_unapproved_roots_and_license_neighbours_refused(tmp_path: Path) -> None:
    unwanted = (
        "data/patient.json",
        "specs/research.json",
        "notebooks/run.ipynb",
        "apps/workspace/private.bin",
        "apps/workspace/LICENSE.bak",
        "apps/other/LICENSE",
        ".github/workflows/publish.yml",
        "../outside.txt",
        "src/another/__init__.py",
    )
    for i, name in enumerate(unwanted):
        status, result = _run(_archive(tmp_path / f"extra-{i}.tar.gz", extra=name))
        assert status == 2, name
        assert result["issues"], name


def test_source_tampering_blocks_archive(tmp_path: Path) -> None:
    for path in ("README.md", "src/medscale/__about__.py", "pyproject.toml"):
        status, output = _run(_archive(tmp_path / (path.split("/")[-1] + ".tar.gz"), altered=path))
        assert status == 2
        assert "mismatch" in " ".join(output["issues"])


def test_missing_notices_or_record_blocks_archive(tmp_path: Path) -> None:
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "MEDORIGIN_SOURCE_PROVENANCE.json"):
        status, result = _run(_archive(tmp_path / (name + ".tar.gz"), missing=name))
        assert status == 2
        assert result["issues"]


def test_symlink_is_rejected(tmp_path: Path) -> None:
    status, result = _run(_archive(tmp_path / "link.tar.gz", symbolic=True))
    assert status == 2
    assert any("special" in str(v) for v in result["issues"])


def test_scope_only_receipt_cannot_impersonate_committed_git_source(tmp_path: Path) -> None:
    """An internally consistent scope receipt is not proof of Git-origin bytes."""
    archive = _archive(tmp_path / "unbound.tar.gz")
    status, report = _run(archive)
    assert status == 0 and report["publication_authorized"] is False
    checked = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--sdist",
            str(archive),
            "--verify-source-checkout",
            str(ROOT),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 2
    assert "source commit" in checked.stdout


def test_corrupt_archive_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.tar.gz"
    path.write_bytes(b"not a valid tar")
    status, result = _run(path)
    assert status == 2
    assert result["status"] == "BLOCKED"


def test_rehashed_project_metadata_cannot_override_committed_root(tmp_path: Path) -> None:
    """An attacker must not authorize arbitrary metadata by editing its receipt."""
    stage_dir = tmp_path / "staged"
    staged = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/stage_medorigin_core_projection.py"),
            "--out",
            str(stage_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert staged.returncode == 0, staged.stderr

    def pack(name: str) -> Path:
        destination = tmp_path / name
        with tarfile.open(destination, "w:gz") as archive:
            for path in sorted(p for p in stage_dir.rglob("*") if p.is_file()):
                relative = path.relative_to(stage_dir).as_posix()
                info = archive.gettarinfo(str(path), arcname="medscale-0.3.0/" + relative)
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
        return destination

    def verify(path: Path) -> tuple[int, dict[str, Any]]:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--sdist",
                str(path),
                "--verify-source-checkout",
                str(ROOT),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.stdout, result.stderr
        return result.returncode, cast(dict[str, Any], json.loads(result.stdout))

    # The fixture itself must qualify against exact Git-committed root bytes.
    status, original = verify(pack("untampered.tar.gz"))
    assert status == 0, original

    pyproject = stage_dir / "pyproject.toml"
    pyproject.write_bytes(pyproject.read_bytes() + b"\n# unapproved build metadata change\n")
    record_path = stage_dir / "MEDORIGIN_SOURCE_PROVENANCE.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["projected_pyproject_sha256"] = hashlib.sha256(pyproject.read_bytes()).hexdigest()
    record_path.write_text(
        json.dumps(record, sort_keys=True, indent=2) + chr(10),
        encoding="utf-8",
    )

    forged_archive = pack("rehashed-metadata.tar.gz")
    # Its own digest and provenance receipt now agree, so the scope-only
    # audit passes; verification against committed Git must STILL reject.
    status, scope = _run(forged_archive)
    assert status == 0, scope
    status, bound = verify(forged_archive)
    assert status == 2, bound
    assert "projected metadata differs from canonical Git transform" in bound["issues"]
