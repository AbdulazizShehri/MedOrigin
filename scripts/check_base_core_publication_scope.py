"""Fail closed before publishing a synthetic-only MedOrigin base Core distribution.

Check both the exact Wheel and sdist metadata: neither may advertise *any*
optional extra or third-party runtime dependency until that distribution
scope has a separate security review and approved source-bound projection.

This is an additional read-only publisher gate, NOT a tag/release creator,
independent security signoff, or scientific source migration.
"""

from __future__ import annotations

import argparse
import json
import re
import tarfile
import zipfile
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path

_MAX_ARCHIVE_BYTES = 30_000_000
_MAX_METADATA_BYTES = 262_144
_WHEEL_METADATA = re.compile(r"medscale-[^/]+[.]dist-info/METADATA")
_SDIST_METADATA = re.compile(r"medscale-[^/]+/PKG-INFO")


class PublicationScopeError(ValueError):
    """Nonclinical base Core publication scope is not demonstrably safe."""


def _metadata(raw: bytes, label: str) -> EmailMessage:
    if not raw or len(raw) > _MAX_METADATA_BYTES:
        raise PublicationScopeError(f"{label}: missing or oversized metadata")
    try:
        metadata = BytesParser(policy=policy.default).parsebytes(raw)
        if not isinstance(metadata, EmailMessage) or metadata.defects:
            raise PublicationScopeError(f"{label}: malformed metadata")
        for key in ("Name", "Version", "Metadata-Version"):
            if len(metadata.get_all(key, [])) != 1:
                raise PublicationScopeError(f"{label}: ambiguous {key}")
        if metadata["Name"] != "medscale":
            raise PublicationScopeError(f"{label}: unexpected distribution")
        version = str(metadata["Version"])
        if re.fullmatch(r"[0-9]+(?:[.][0-9]+)+(?:[A-Za-z0-9.+_-]*)", version) is None:
            raise PublicationScopeError(f"{label}: invalid version")
        return metadata
    except (UnicodeError, TypeError, ValueError) as exc:
        if isinstance(exc, PublicationScopeError):
            raise
        raise PublicationScopeError(f"{label}: unreadable metadata") from exc


def _check_policy(message: EmailMessage, label: str) -> list[str]:
    issues: list[str] = []
    if message.get_all("Provides-Extra", []):
        issues.append(f"{label}: optional extras must not be published in the base beta")
    if message.get_all("Requires-Dist", []):
        issues.append(f"{label}: runtime dependencies must be separately qualified")
    for dynamic in message.get_all("Dynamic", []):
        if str(dynamic).casefold() in {"provides-extra", "requires-dist"}:
            issues.append(f"{label}: dynamic dependency/extra metadata forbidden")
    return issues


def _wheel(path: Path) -> EmailMessage:
    try:
        with zipfile.ZipFile(path) as archive:
            matches = [m for m in archive.infolist() if _WHEEL_METADATA.fullmatch(m.filename)]
            if len(matches) != 1 or matches[0].is_dir():
                raise PublicationScopeError("wheel: exactly one METADATA required")
            item = matches[0]
            if item.file_size > _MAX_METADATA_BYTES:
                raise PublicationScopeError("wheel: METADATA exceeds budget")
            raw = archive.read(item)
            return _metadata(raw, "wheel")
    except (OSError, RuntimeError, zipfile.BadZipFile, ValueError) as exc:
        if isinstance(exc, PublicationScopeError):
            raise
        raise PublicationScopeError("wheel: invalid archive") from exc


def _sdist(path: Path) -> EmailMessage:
    try:
        with tarfile.open(path, "r:gz") as archive:
            matches = [m for m in archive.getmembers() if _SDIST_METADATA.fullmatch(m.name)]
            if len(matches) != 1 or not matches[0].isfile():
                raise PublicationScopeError("sdist: exactly one regular PKG-INFO required")
            item = matches[0]
            if item.size > _MAX_METADATA_BYTES:
                raise PublicationScopeError("sdist: PKG-INFO exceeds budget")
            member = archive.extractfile(item)
            if member is None:
                raise PublicationScopeError("sdist: PKG-INFO unreadable")
            with member:
                raw = member.read(_MAX_METADATA_BYTES + 1)
            return _metadata(raw, "sdist")
    except (OSError, EOFError, tarfile.TarError, ValueError) as exc:
        if isinstance(exc, PublicationScopeError):
            raise
        raise PublicationScopeError("sdist: invalid archive") from exc


def inspect(dist: Path) -> dict[str, object]:
    issues: list[str] = []
    packages = {
        "wheel": list(dist.glob("medscale-*.whl")),
        "sdist": list(dist.glob("medscale-*.tar.gz")),
    }
    for kind in ("wheel", "sdist"):
        if len(packages[kind]) != 1:
            issues.append(f"{kind}: exactly one MedOrigin artifact required")
    versions: dict[str, str] = {}
    if not issues:
        for kind, check in (("wheel", _wheel), ("sdist", _sdist)):
            item = packages[kind][0]
            if item.is_symlink() or not item.is_file() or item.stat().st_size > _MAX_ARCHIVE_BYTES:
                issues.append(f"{kind}: missing, linked or oversized archive")
                continue
            try:
                metadata = check(item)
                versions[kind] = str(metadata["Version"])
                issues.extend(_check_policy(metadata, kind))
            except PublicationScopeError as exc:
                issues.append(str(exc))
        if len(versions) == 2 and versions["wheel"] != versions["sdist"]:
            issues.append("Wheel and sdist package versions disagree")
    return {
        "status": "BASE_CORE_PUBLICATION_SCOPE_CLEAN" if not issues else "BLOCKED",
        "scope": "base_synthetic_only",
        "versions": versions,
        "publication_authorized": False,
        "independent_security_review_complete": False,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = inspect(args.dist)
    except OSError:
        result = {
            "status": "BLOCKED",
            "issues": ["artifact directory unavailable"],
            "publication_authorized": False,
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "BASE_CORE_PUBLICATION_SCOPE_CLEAN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
