"""Adversarial tests of MedOrigin Core source-distribution integrity."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest

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


def _add_bound_pkg_info(stage: Path) -> None:
    """Materialize self-consistent test-only metadata for staged source fixtures."""
    project = tomllib.loads((stage / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    fields = [
        "Metadata-Version: 2.5",
        f"Name: {project['name']}",
        "Version: 0.3.0",
        f"Summary: {project['description']}",
    ]
    fields.extend(f"Project-URL: {name}, {url}" for name, url in project["urls"].items())
    fields.extend(
        [
            f"Author: {', '.join(author['name'] for author in project['authors'])}",
            f"License-Expression: {project['license']}",
            "License-File: LICENSE",
            f"Keywords: {','.join(sorted(project['keywords']))}",
        ]
    )
    fields.extend(f"Classifier: {value}" for value in project["classifiers"])
    fields.append(f"Requires-Python: {project['requires-python']}")
    extras = project.get("optional-dependencies", {})
    for name, values in extras.items():
        fields.append(f"Provides-Extra: {name}")
        for requirement in values:
            dependency, has_marker, marker = requirement.partition(";")
            condition = f"({marker.strip()}) and " if has_marker else ""
            fields.append(f"Requires-Dist: {dependency.strip()}; {condition}extra == '{name}'")
    fields.append("Description-Content-Type: text/markdown")
    (stage / "PKG-INFO").write_bytes(
        ("\n".join(fields) + "\n\n").encode("utf-8") + (stage / "README.md").read_bytes()
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


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("setuid", "file mode"),
        ("executable", "file mode"),
        ("pax-xattr", "PAX extension"),
        ("uid", "owner metadata"),
        ("gid", "owner metadata"),
        ("uname", "owner metadata"),
        ("gname", "owner metadata"),
    ],
)
def test_sdist_rejects_unauthenticated_tar_header_controls(
    tmp_path: Path, mutation: str, expected: str
) -> None:
    """Identical source bytes and provenance never authorize TAR modes/xattrs."""
    original = _archive(tmp_path / "known.tar.gz")
    code, baseline = _run(original)
    assert code == 0, baseline
    forged = tmp_path / (mutation + ".tar.gz")
    with (
        tarfile.open(original, "r:gz") as source,
        tarfile.open(forged, "w:gz", format=tarfile.PAX_FORMAT) as target,
    ):
        for member in source:
            payload = source.extractfile(member)
            if member.name == "medscale-0.3.0/README.md":
                if mutation == "setuid":
                    member.mode = 0o4755
                elif mutation == "executable":
                    member.mode = 0o755
                elif mutation == "uid":
                    member.uid = 1000
                elif mutation == "gid":
                    member.gid = 1000
                elif mutation == "uname":
                    member.uname = "untrusted-owner"
                elif mutation == "gname":
                    member.gname = "untrusted-group"
                else:
                    member.pax_headers = {"SCHILY.xattr.user.proof": "test-only untrusted metadata"}
            target.addfile(member, io.BytesIO(payload.read()) if payload else None)
    status, report = _run(forged)
    assert status == 2, report
    assert report["status"] == "BLOCKED"
    assert any(expected in issue for issue in report["issues"]), report


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


def test_rehashed_source_receipt_cannot_hide_missing_git_module(tmp_path: Path) -> None:
    """A partial sdist cannot shrink its own trust boundary to omit a module."""
    staged = tmp_path / "staged"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/stage_medorigin_core_projection.py"),
            "--out",
            str(staged),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    _add_bound_pkg_info(staged)
    removed = "src/medscale/cli/dataset.py"
    receipt_path = staged / "MEDORIGIN_SOURCE_PROVENANCE.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert removed in receipt["source_files"]

    def package(filename: str) -> Path:
        output = tmp_path / filename
        with tarfile.open(output, "w:gz", format=tarfile.GNU_FORMAT) as tar:
            for source in sorted(path for path in staged.rglob("*") if path.is_file()):
                arcname = "medscale-0.3.0/" + source.relative_to(staged).as_posix()
                info = tar.gettarinfo(str(source), arcname=arcname)
                info.mode = 0o644
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                with source.open("rb") as stream:
                    tar.addfile(info, stream)
        return output

    def bound_inspect(archive: Path) -> tuple[int, dict[str, Any]]:
        proc = subprocess.run(
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
        assert proc.stdout, proc.stderr
        return proc.returncode, cast(dict[str, Any], json.loads(proc.stdout))

    ok, report = bound_inspect(package("original.tar.gz"))
    assert ok == 0, report
    # Forge a self-consistent partial inventory: source bytes in Git remain
    # intact, but the distributable and its declared hash map lose a module.
    (staged / removed).unlink()
    receipt["source_files"].pop(removed)
    receipt["source_file_count"] = len(receipt["source_files"])
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    forged = package("forged-partial.tar.gz")
    # A scope-only check has no independent Git anchor and may pass;
    # the authoritative committed-source check MUST reject the omitted file.
    scope_status, scope = _run(forged)
    assert scope_status == 0, scope
    status, bound = bound_inspect(forged)
    assert status == 2, bound
    assert "Git source archive membership differs from provenance" in bound["issues"]


def test_generated_pkg_info_installer_controls_are_git_bound(tmp_path: Path) -> None:
    """A tampered sdist must not change dependencies, metadata, or README."""
    stage = tmp_path / "source"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/stage_medorigin_core_projection.py"),
            "--out",
            str(stage),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    _add_bound_pkg_info(stage)
    pkg = stage / "PKG-INFO"
    original = pkg.read_bytes()

    def check_bound(name: str) -> tuple[int, dict[str, Any]]:
        output = tmp_path / (name + ".tar.gz")
        with tarfile.open(output, "w:gz", format=tarfile.GNU_FORMAT) as archive:
            for file in sorted(path for path in stage.rglob("*") if path.is_file()):
                info = archive.gettarinfo(
                    str(file), arcname="medscale-0.3.0/" + file.relative_to(stage).as_posix()
                )
                info.mode = 0o644
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                with file.open("rb") as source:
                    archive.addfile(info, source)
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--sdist",
            str(output),
            "--verify-source-checkout",
            str(ROOT),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        assert proc.stdout, proc.stderr
        return proc.returncode, cast(dict[str, Any], json.loads(proc.stdout))

    code, report = check_bound("genuine-source")
    assert code == 0, report
    header, divider, body = original.partition(b"\n\n")
    assert divider
    for name, tampered, expected in (
        (
            "unexpected-install-dependency",
            header + b"\nRequires-Dist: synthetic-undisclosed-dependency>=9" + divider + body,
            "Requires-Dist",
        ),
        (
            "unexpected-control-header",
            header + b"\nX-Extra-Installer-Control: yes" + divider + body,
            "unapproved metadata fields",
        ),
        (
            "wrong-project-version",
            original.replace(b"Version: 0.3.0\n", b"Version: 9.9.9\n", 1),
            "Version",
        ),
        ("different-readme-body", original + b"\nforged footer\n", "README body"),
    ):
        pkg.write_bytes(tampered)
        code, report = check_bound(name)
        assert code == 2, (name, report)
        assert any(expected in issue for issue in report["issues"]), (name, report)
    pkg.unlink()
    code, report = check_bound("missing-pkg-info")
    assert code == 2, report
    assert any("PKG-INFO" in issue for issue in report["issues"]), report


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
    _add_bound_pkg_info(stage_dir)

    def pack(name: str) -> Path:
        destination = tmp_path / name
        with tarfile.open(destination, "w:gz", format=tarfile.GNU_FORMAT) as archive:
            for path in sorted(p for p in stage_dir.rglob("*") if p.is_file()):
                relative = path.relative_to(stage_dir).as_posix()
                info = archive.gettarinfo(str(path), arcname="medscale-0.3.0/" + relative)
                info.mode = 0o644
                info.uid = info.gid = 0
                info.uname = info.gname = ""
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
