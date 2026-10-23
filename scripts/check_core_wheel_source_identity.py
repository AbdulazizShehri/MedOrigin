"""Read-only, fail-closed Core wheel-to-committed-Git source attestation.

Only the prepublication MedOrigin Core lane uses this strict exact-source
contract. A matching wheel METADATA or self-authored RECORD is not proof that
the installed Python payload came from the qualified source tree.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

DIST_INFO = "medscale-0.3.0.dist-info/"
DIST_INFO_FILES = frozenset(
    {
        DIST_INFO + "METADATA",
        DIST_INFO + "WHEEL",
        DIST_INFO + "entry_points.txt",
        DIST_INFO + "licenses/LICENSE",
        DIST_INFO + "RECORD",
    }
)
MAX_MEMBERS = 2_000
MAX_MEMBER_SIZE = 30_000_000
MAX_TOTAL_SIZE = 50_000_000


def _git(repository: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        check=True,
    ).stdout


def inspect(path: Path, repository: Path) -> dict[str, object]:
    issues: list[str] = []
    sources: dict[str, bytes] = {}
    members: dict[str, bytes] = {}
    commit = ""
    license_bytes = b""
    try:
        commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
        source_archive = _git(repository, "archive", "--format=zip", commit, "--", "src/medscale")
        with zipfile.ZipFile(io.BytesIO(source_archive)) as source_zip:
            for info in source_zip.infolist():
                if info.is_dir():
                    continue
                if not info.filename.startswith("src/medscale/"):
                    issues.append("Git source archive contains an unexpected path")
                    continue
                name = info.filename.removeprefix("src/")
                if name in sources:
                    issues.append("duplicate committed source path")
                    continue
                sources[name] = source_zip.read(info)
        if len(sources) < 200 or "medscale/__init__.py" not in sources:
            issues.append("committed Core package source set is incomplete")
        license_bytes = _git(repository, "show", f"{commit}:LICENSE")

        total = 0
        with zipfile.ZipFile(path) as wheel:
            for info in wheel.infolist():
                name = info.filename
                if info.is_dir():
                    continue
                if name in members:
                    issues.append("duplicate wheel entry")
                    continue
                if (
                    name.startswith("/")
                    or "\\" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    or name != name.strip()
                ):
                    issues.append("unsafe wheel path")
                    continue
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    issues.append("wheel symlink prohibited")
                    continue
                if info.file_size > MAX_MEMBER_SIZE:
                    issues.append("wheel member exceeds byte budget")
                    break
                total += info.file_size
                if total > MAX_TOTAL_SIZE or len(members) >= MAX_MEMBERS:
                    issues.append("wheel exceeds content budget")
                    break
                members[name] = wheel.read(info)
    except (
        OSError,
        subprocess.CalledProcessError,
        UnicodeError,
        ValueError,
        EOFError,
        zipfile.BadZipFile,
    ):
        issues.append("wheel or Git source could not be read")

    if members:
        payload = {name: data for name, data in members.items() if name.startswith("medscale/")}
        expected_names = set(sources)
        if set(payload) != expected_names:
            issues.append("wheel Python payload membership differs from committed Git source")
        for name in sorted(expected_names & set(payload)):
            if payload[name] != sources[name]:
                issues.append("wheel payload bytes differ from committed Git source: " + name)
                break
        meta = set(members) - set(payload)
        if meta != DIST_INFO_FILES:
            issues.append("wheel distribution metadata membership differs from allowlist")
        if members.get(DIST_INFO + "licenses/LICENSE") != license_bytes:
            issues.append("wheel license bytes differ from committed Git")
        record_bytes = members.get(DIST_INFO + "RECORD")
        if record_bytes is None:
            issues.append("wheel RECORD missing")
        else:
            try:
                rows = list(csv.reader(io.StringIO(record_bytes.decode("utf-8"))))
                seen: set[str] = set()
                for row in rows:
                    if len(row) != 3 or row[0] in seen or row[0] not in members:
                        issues.append("invalid or duplicate wheel RECORD entry")
                        break
                    name, digest, size = row
                    seen.add(name)
                    if name == DIST_INFO + "RECORD":
                        if digest or size:
                            issues.append("wheel RECORD self-entry must be unbound")
                            break
                        continue
                    expected = (
                        base64.urlsafe_b64encode(hashlib.sha256(members[name]).digest())
                        .rstrip(b"=")
                        .decode("ascii")
                    )
                    if digest != "sha256=" + expected or size != str(len(members[name])):
                        issues.append("wheel RECORD hash or size does not match payload")
                        break
                if seen != set(members):
                    issues.append("wheel RECORD membership differs from payload")
            except (UnicodeError, csv.Error, ValueError):
                issues.append("unreadable wheel RECORD")
    elif not issues:
        issues.append("wheel contains no files")

    return {
        "status": "SOURCE_BOUND_WHEEL_QUALIFIED_ONLY" if not issues else "BLOCKED",
        "source_git_commit": commit,
        "source_file_count": len(sources),
        "wheel_members": len(members),
        "publication_authorized": False,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--verify-source-checkout", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.wheel.is_file():
        parser.error("wheel file not found")
    report = inspect(args.wheel, args.verify_source_checkout)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "SOURCE_BOUND_WHEEL_QUALIFIED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
