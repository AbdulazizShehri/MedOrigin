"""Stage a transparent, source-verified MedOrigin Core packaging projection.

The frozen research repository root is untouched. The independent staging tree
has a canonical distribution pyproject and exact, committed source bytes from
Git HEAD. This is NOT a publisher, source edit, or release authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
PREDECESSOR_ROOT_SHA: Final = "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
LOCK_SHA: Final = "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"
MRL_MANIFEST_SHA: Final = "7773967611e42c3d74338a1ec7c9004f661843df809865f6c6d455923fea89d1"
BASE: Final = "https://github.com/AbdulazizShehri/MedOrigin"
SOURCE_PATHS: Final = (
    "src/medscale",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "apps/workspace/LICENSE",
)
PACKAGED_PATHS: Final = (*SOURCE_PATHS, "MEDORIGIN_SOURCE_PROVENANCE.json")
RELEASE_METADATA: Final = {
    "Homepage": BASE,
    "Repository": BASE,
    "Documentation": BASE + "/tree/main/docs",
    "Issues": BASE + "/issues",
}


class ProjectionError(ValueError):
    """Source identity or package projection violates the declared contract."""


def _git(*args: str) -> bytes:
    cp = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True)
    return cp.stdout


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_bytes(commit: str, path: str) -> bytes:
    return _git("show", f"{commit}:{path}")


def stage(target: Path) -> dict[str, object]:
    """Stage exact committed source into a new directory; no root mutation."""
    target = target.resolve()
    if target.exists():
        raise ProjectionError(f"destination already exists: {target}")
    if target == ROOT or (ROOT in target.parents and ".git" in target.parts):
        raise ProjectionError("cannot stage inside the Git metadata directory")
    commit = _git("rev-parse", "HEAD").decode("ascii").strip()
    if re.fullmatch("[0-9a-f]{40}", commit) is None:
        raise ProjectionError("noncanonical commit SHA")
    root = _source_bytes(commit, "pyproject.toml")
    lock = _source_bytes(commit, "uv.lock")
    manifest = _source_bytes(
        commit, "specs/mesc-experiment-0/mrl-0809-static-prerequisites-v1.json"
    )
    if _sha(root) != PREDECESSOR_ROOT_SHA or _sha(lock) != LOCK_SHA:
        raise ProjectionError("frozen root or dependency lock no longer matches")
    if _sha(manifest) != MRL_MANIFEST_SHA:
        raise ProjectionError("frozen research manifest no longer matches")
    original = root.decode("utf-8")
    newline = "\r\n" if "\r\n" in original else "\n"
    parsed = original.splitlines(keepends=True)
    current_section = ""
    replaced: set[str] = set()
    for i, line in enumerate(parsed):
        if line.lstrip().startswith("[") and line.strip().endswith("]"):
            current_section = line.strip()
        if current_section != "[project.urls]":
            continue
        for key, url in RELEASE_METADATA.items():
            old = f'{key} = "https://github.com/TheHalfMoon/MESC'
            if line.startswith(old):
                expected = url.removeprefix(BASE)
                if line.rstrip("\r\n") != f'{old}{expected}"':
                    raise ProjectionError(f"unexpected predecessor URL: {key}")
                parsed[i] = f'{key} = "{url}"' + ("\r\n" if line.endswith("\r\n") else "\n")
                replaced.add(key)
    if replaced != set(RELEASE_METADATA):
        raise ProjectionError("all four source Project-URLs must have known predecessors")
    marker = "[tool.hatch.build.targets.wheel]" + newline + 'packages = ["src/medscale"]' + newline
    successor = "".join(parsed)
    if successor.count(marker) != 1 or "[tool.hatch.build.targets.sdist]" in successor:
        raise ProjectionError("unsupported build contract")
    selector = ", ".join(f'"{p}"' for p in PACKAGED_PATHS)
    successor = successor.replace(
        marker,
        marker
        + newline
        + "[tool.hatch.build.targets.sdist]"
        + newline
        + "only-include = ["
        + selector
        + "]"
        + newline,
    )
    archive = _git("archive", "--format=zip", commit, "--", *SOURCE_PATHS)
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            path = info.filename
            if "\\" in path or Path(path).is_absolute() or ".." in Path(path).parts:
                raise ProjectionError("unsafe archived path")
            if not any(path == p or path.startswith(p + "/") for p in SOURCE_PATHS):
                raise ProjectionError("unapproved archived file")
            if path in files or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ProjectionError("duplicate or symlinked archived file")
            files[path] = z.read(info)
    for essential in (
        "src/medscale/__init__.py",
        "src/medscale/__about__.py",
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "apps/workspace/LICENSE",
    ):
        if essential not in files:
            raise ProjectionError(f"missing source requirement: {essential}")
    if files["LICENSE"] != files["apps/workspace/LICENSE"]:
        raise ProjectionError("Core and Workspace license bytes disagree")
    manifest_doc: dict[str, object] = {
        "schema": "MEDORIGIN-CORE-PROJECTION-1",
        "status": "UNPUBLISHED_NOT_APPROVED",
        "source_git_commit": commit,
        "frozen_pyproject_sha256": _sha(root),
        "frozen_lock_sha256": _sha(lock),
        "frozen_mrl_manifest_sha256": _sha(manifest),
        "projected_pyproject_sha256": _sha(successor.encode("utf-8")),
        "canonical_distribution_repository": BASE,
        "source_files": {p: _sha(v) for p, v in sorted(files.items())},
        "source_file_count": len(files),
        "publication_authorized": False,
    }
    record = (json.dumps(manifest_doc, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with tempfile.TemporaryDirectory(prefix="medorigin-projection-") as scratch:
        work = Path(scratch) / "package"
        work.mkdir()
        for p, value in files.items():
            dst = work / p
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(value)
        (work / "pyproject.toml").write_bytes(successor.encode("utf-8"))
        (work / "MEDORIGIN_SOURCE_PROVENANCE.json").write_bytes(record)
        if target.exists():
            raise ProjectionError("destination created during staging")
        target.parent.mkdir(parents=True, exist_ok=True)
        work.rename(target)
    return {
        "source_commit": commit,
        "source_file_count": len(files),
        "projected_pyproject_sha256": _sha(successor.encode("utf-8")),
        "staged_path": str(target),
        "publication_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        result = stage(args.out)
    except (OSError, subprocess.CalledProcessError, ProjectionError) as ex:
        sys.stderr.write(f"PROJECTION_BLOCKED: {ex}\n")
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
