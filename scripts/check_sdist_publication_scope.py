"""Fail-closed, read-only MedOrigin Core sdist publication-content preflight."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

TOP_LEVEL = frozenset(
    {
        "src",
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "pyproject.toml",
        "PKG-INFO",
        ".gitignore",
        "MEDORIGIN_SOURCE_PROVENANCE.json",
        "apps",
    }
)
ESSENTIAL = frozenset(
    {
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "pyproject.toml",
        "src/medscale/__init__.py",
        "src/medscale/__about__.py",
        "apps/workspace/LICENSE",
        "MEDORIGIN_SOURCE_PROVENANCE.json",
    }
)
MAX_MEMBERS = 2_000
MAX_TOTAL_SIZE = 50_000_000
MAX_ONE_FILE = 30_000_000


def _verify_projection(archive: tarfile.TarFile, entries: set[str]) -> list[str]:
    """Rehash every archived source file against the projection's source receipt."""
    issues: list[str] = []
    prefix = "medscale-0.3.0/"
    try:
        receipt_file = archive.extractfile(prefix + "MEDORIGIN_SOURCE_PROVENANCE.json")
        assert receipt_file is not None
        doc = json.loads(receipt_file.read())
        source = doc.get("source_files")
        if doc.get("schema") != "MEDORIGIN-CORE-PROJECTION-1" or not isinstance(source, dict):
            return ["invalid source provenance schema"]
        required = {
            name
            for name in entries
            if name.startswith("src/medscale/")
            or name in {"README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "apps/workspace/LICENSE"}
        }
        if set(source) != required or doc.get("source_file_count") != len(required):
            issues.append("source provenance membership mismatch")
        if doc.get("publication_authorized") is not False:
            issues.append("source provenance must not authorize publication")
        for name in sorted(required):
            expected = source.get(name)
            member = archive.extractfile(prefix + name)
            if member is None or not isinstance(expected, str) or len(expected) != 64:
                issues.append("missing source checksum")
            elif hashlib.sha256(member.read()).hexdigest() != expected:
                issues.append("source provenance hash mismatch")
                break
        projected = archive.extractfile(prefix + "pyproject.toml")
        if projected is None or hashlib.sha256(projected.read()).hexdigest() != doc.get(
            "projected_pyproject_sha256"
        ):
            issues.append("projected metadata checksum mismatch")
        core_license = archive.extractfile(prefix + "LICENSE")
        workspace_license = archive.extractfile(prefix + "apps/workspace/LICENSE")
        if core_license is None or workspace_license is None:
            issues.append("Core or Workspace license missing")
        elif core_license.read() != workspace_license.read():
            issues.append("Core and Workspace license bytes differ")
    except (AttributeError, AssertionError, UnicodeError, ValueError, TypeError, KeyError):
        issues.append("unreadable or malformed source provenance")
    return issues


def _verify_source_checkout(archive: tarfile.TarFile, repository: Path) -> list[str]:
    """Independently compare the receipt to exact committed Git source bytes."""
    issues: list[str] = []
    try:
        record = archive.extractfile("medscale-0.3.0/MEDORIGIN_SOURCE_PROVENANCE.json")
        if record is None:
            return ["source provenance record missing"]
        provenance = json.load(record)
        commit = provenance.get("source_git_commit")
        source = provenance.get("source_files")
        if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            return ["invalid provenance source commit"]
        if not isinstance(source, dict):
            return ["invalid source file map"]
        head = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if commit != head:
            return ["sdist source commit is not the checked-out HEAD"]
        git_archive = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "archive",
                "--format=zip",
                commit,
                "--",
                *sorted(source),
            ],
            check=True,
            capture_output=True,
        ).stdout
        with zipfile.ZipFile(io.BytesIO(git_archive)) as zipped:
            archived_names = {entry.filename for entry in zipped.infolist() if not entry.is_dir()}
            if archived_names != set(source):
                issues.append("Git source archive membership differs from provenance")
            for name, expected in source.items():
                if (
                    name not in archived_names
                    or hashlib.sha256(zipped.read(name)).hexdigest() != expected
                ):
                    issues.append("source file differs from committed Git bytes")
                    break
        for path, field in (
            ("pyproject.toml", "frozen_pyproject_sha256"),
            ("uv.lock", "frozen_lock_sha256"),
            (
                "specs/mesc-experiment-0/mrl-0809-static-prerequisites-v1.json",
                "frozen_mrl_manifest_sha256",
            ),
        ):
            committed = subprocess.run(
                ["git", "-C", str(repository), "show", f"{commit}:{path}"],
                check=True,
                capture_output=True,
            ).stdout
            if hashlib.sha256(committed).hexdigest() != provenance.get(field):
                issues.append("frozen Git input differs from provenance: " + path)
        if (
            provenance.get("canonical_distribution_repository")
            != "https://github.com/AbdulazizShehri/MedOrigin"
        ):
            issues.append("canonical distribution repository differs from provenance")
    except (
        subprocess.CalledProcessError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        zipfile.BadZipFile,
    ):
        issues.append("Git source provenance could not be verified")
    return issues


def inspect(path: Path, *, source_repo: Path | None = None) -> dict[str, object]:
    issues: list[str] = []
    entries: set[str] = set()
    byte_total = 0
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            for member in archive:
                if len(entries) >= MAX_MEMBERS:
                    issues.append("sdist exceeds member limit")
                    break
                parts = member.name.split("/")
                if (
                    len(parts) < 2
                    or parts[0] != "medscale-0.3.0"
                    or any(piece in ("", ".", "..") for piece in parts[1:])
                    or "\\" in member.name
                ):
                    issues.append("unsafe or unexpected archive path")
                    continue
                relative = "/".join(parts[1:])
                if relative in entries:
                    issues.append("duplicate archive member")
                entries.add(relative)
                if parts[1] not in TOP_LEVEL:
                    issues.append(f"unapproved root: {parts[1]}")
                elif parts[1] == "src" and (len(parts) < 3 or parts[2] != "medscale"):
                    issues.append("src contains non-Core payload")
                elif parts[1] == "apps" and relative != "apps/workspace/LICENSE":
                    issues.append("apps contains non-license payload")
                if not (member.isfile() or member.isdir()):
                    issues.append("link or special file not permitted")
                if member.size > MAX_ONE_FILE:
                    issues.append("sdist member exceeds size budget")
                byte_total += member.size
                if byte_total > MAX_TOTAL_SIZE:
                    issues.append("sdist exceeds total byte budget")
                    break
            if not issues:
                issues.extend(_verify_projection(archive, entries))
            if not issues and source_repo is not None:
                issues.extend(_verify_source_checkout(archive, source_repo))
    except (tarfile.TarError, OSError, EOFError, ValueError, KeyError):
        issues.append("sdist is corrupt or unreadable")
    missing = sorted(ESSENTIAL - entries)
    if missing:
        issues.append("essential package files missing: " + ", ".join(missing))
    return {
        "status": "SDIST_SCOPE_QUALIFIED_ONLY" if not issues else "BLOCKED",
        "publication_authorized": False,
        "members": len(entries),
        "total_uncompressed_bytes": byte_total,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument(
        "--verify-source-checkout",
        type=Path,
        help="Require the source receipt to match every byte of this Git checkout at HEAD",
    )
    args = parser.parse_args(argv)
    if not args.sdist.is_file():
        parser.error("source distribution not found")
    result = inspect(args.sdist, source_repo=args.verify_source_checkout)
    sys.stdout.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return 0 if result["status"] == "SDIST_SCOPE_QUALIFIED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
