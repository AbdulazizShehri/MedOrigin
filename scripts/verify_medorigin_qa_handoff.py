"""Read-only integrity checker for the *unpublished* MedOrigin QA handoff.

This checks structural safety, completeness and pinned Core bytes. It does not
authenticate the unsigned publisher, approve release, install packages, or
inspect clinical data. The ZIP is never extracted by this checker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path

ROOT = "examples/synthetic_fhir_developer_beta/"
EXAMPLES = (
    "README.md",
    "desktop.py",
    "evidence_export.py",
    "malformed.json",
    "preview.py",
    "reproduce.py",
    "synthetic_cases.py",
    "synthetic_structure_definition.json",
)
WHEEL = "medscale-0.3.0-py3-none-any.whl"
SDIST = "medscale-0.3.0.tar.gz"
CORE_SHA = "1cb9ccfeada45b6fa6514c404355f5901c2433f9"
DEMO_SHA = "852ca86aaad391beb9153c0b96941bd5546d85f3"
TRUSTED_ARTIFACTS = {
    WHEEL: "a718b77794c817dfcf6a711cd97324b3626e4d65382ba39c670a7c303fae07e7",
    SDIST: "7225385db4ed0b5d24ef3180c4ebcbfb7fe45921239c21a390c367a124600482",
}
MANIFEST = "BUNDLE_MANIFEST.json"
SUMS = "SHA256SUMS.txt"
PROVENANCE = "provenance/MEDORIGIN_SOURCE_PROVENANCE.json"
EXPECTED_PATHS = frozenset(
    {
        MANIFEST,
        SUMS,
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "README_UNPUBLISHED_QA.md",
        PROVENANCE,
        f"artifacts/{WHEEL}",
        f"artifacts/{SDIST}",
        *(ROOT + name for name in EXAMPLES),
    }
)
MAX_MEMBER = 2_000_000
MAX_TOTAL = 5_000_000
SHA_LINE = re.compile(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)\Z")


class HandoffIntegrityError(ValueError):
    """A nonqualifying, untrusted local handoff."""


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise HandoffIntegrityError("ambiguous JSON key")
        result[key] = value
    return result


def json_object(data: bytes) -> dict[str, object]:
    try:
        parsed = json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, ValueError) as exc:
        raise HandoffIntegrityError("invalid or ambiguous JSON metadata") from exc
    if not isinstance(parsed, dict):
        raise HandoffIntegrityError("JSON metadata must be an object")
    return parsed


def _is_safe_path(path: str) -> bool:
    if not path or len(path) > 180 or "\\" in path or ":" in path:
        return False
    return all(part not in {"", ".", ".."} for part in path.split("/"))


def _collect_directory(directory: Path) -> dict[str, bytes]:
    if directory.is_symlink():
        raise HandoffIntegrityError("directory symbolic link not permitted")
    result: dict[str, bytes] = {}
    for entry in directory.rglob("*"):
        if entry.is_symlink():
            raise HandoffIntegrityError("file or directory symbolic link not permitted")
        if not entry.is_file():
            continue
        name = entry.relative_to(directory).as_posix()
        if not _is_safe_path(name) or name not in EXPECTED_PATHS or name in result:
            raise HandoffIntegrityError("unexpected local handoff path")
        if entry.stat().st_size > MAX_MEMBER:
            raise HandoffIntegrityError("oversized local handoff member")
        result[name] = entry.read_bytes()
    return result


def _collect_zip(path: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                name = info.filename
                if (
                    info.is_dir()
                    or not _is_safe_path(name)
                    or name not in EXPECTED_PATHS
                    or name in result
                    or info.file_size > MAX_MEMBER
                    or info.flag_bits & 1
                ):
                    raise HandoffIntegrityError("unsafe or unexpected archive member")
                file_kind = stat.S_IFMT(info.external_attr >> 16)
                if file_kind not in {0, stat.S_IFREG}:
                    raise HandoffIntegrityError("nonregular archive member")
                result[name] = archive.read(info)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise HandoffIntegrityError("corrupt or unreadable handoff archive") from exc
    return result


def inspect(
    path: Path,
    *,
    expected_zip_sha256: str | None = None,
    collector: Callable[[Path], dict[str, bytes]] | None = None,
) -> dict[str, object]:
    """Verify a ZIP or directory. No content is ever executed or extracted."""
    if not path.exists():
        raise HandoffIntegrityError("handoff does not exist")
    if path.is_dir():
        if expected_zip_sha256:
            raise HandoffIntegrityError("ZIP digest applies only to archive files")
        members = (collector or _collect_directory)(path)
    else:
        if path.stat().st_size > MAX_TOTAL:
            raise HandoffIntegrityError("oversized handoff ZIP")
        if expected_zip_sha256 is not None:
            if not re.fullmatch(r"[0-9a-f]{64}", expected_zip_sha256):
                raise HandoffIntegrityError("invalid expected ZIP digest")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected_zip_sha256:
                raise HandoffIntegrityError("ZIP digest mismatch")
        members = (collector or _collect_zip)(path)
    if set(members) != EXPECTED_PATHS:
        raise HandoffIntegrityError("missing or extra handoff members")
    if sum(map(len, members.values())) > MAX_TOTAL:
        raise HandoffIntegrityError("handoff uncompressed size exceeded")

    try:
        lines = members[SUMS].decode("ascii").splitlines()
    except UnicodeError as exc:
        raise HandoffIntegrityError("invalid handoff checksum list") from exc
    if len(lines) != len(EXPECTED_PATHS) - 1:
        raise HandoffIntegrityError("handoff checksum inventory incomplete")
    hashes: dict[str, str] = {}
    for line in lines:
        match = SHA_LINE.fullmatch(line)
        if not match:
            raise HandoffIntegrityError("malformed handoff checksum record")
        digest, name = match.groups()
        if name in hashes or name not in EXPECTED_PATHS or name == SUMS:
            raise HandoffIntegrityError("ambiguous handoff checksum record")
        hashes[name] = digest
    if set(hashes) != EXPECTED_PATHS - {SUMS}:
        raise HandoffIntegrityError("checksum coverage incomplete")
    for name, digest in hashes.items():
        if hashlib.sha256(members[name]).hexdigest() != digest:
            raise HandoffIntegrityError("file checksum mismatch")

    manifest = json_object(members[MANIFEST])
    expected_fields: dict[str, object] = {
        "schema": "MEDORIGIN_UNPUBLISHED_QA_HANDOFF_V1",
        "project": "MedOrigin",
        "target_version": "0.3.0",
        "python_distribution": "medscale",
        "core_source_git_commit": CORE_SHA,
        "example_source_git_commit": DEMO_SHA,
        "publication_authorized": False,
        "release_reviewer_approved": False,
        "adr_0044_accepted": False,
        "protected_main_merged": False,
        "developer_examples_in_core_wheel": False,
        "hosted_two_os_rehearsal_run": 40119019407,
        "artifacts_sha256": TRUSTED_ARTIFACTS,
    }
    if manifest != expected_fields or any(
        type(manifest[key]) is not type(value) for key, value in expected_fields.items()
    ):
        raise HandoffIntegrityError("handoff identity or authorization contract differs")
    for name, sha in TRUSTED_ARTIFACTS.items():
        if hashes[f"artifacts/{name}"] != sha:
            raise HandoffIntegrityError("Core artifact digest not qualified")
    provenance = json_object(members[PROVENANCE])
    if (
        provenance.get("source_git_commit") != CORE_SHA
        or provenance.get("publication_authorized") is not False
        or provenance.get("frozen_pyproject_sha256")
        != "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
        or provenance.get("frozen_lock_sha256")
        != "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"
    ):
        raise HandoffIntegrityError("Core provenance identity differs")
    return {
        "status": "MEDORIGIN_UNPUBLISHED_QA_INTEGRITY_PASS",
        "checked_files": len(members),
        "core_source_git_commit": CORE_SHA,
        "example_source_git_commit": DEMO_SHA,
        "publication_authorized": False,
        "independent_review_completed": False,
        "cryptographically_signed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--expected-zip-sha256", help="Trusted external digest of ZIP")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.handoff, expected_zip_sha256=args.expected_zip_sha256)
    except (HandoffIntegrityError, OSError, ValueError, KeyError):
        print("MEDORIGIN_UNPUBLISHED_QA_INTEGRITY_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
