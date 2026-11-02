"""Bounded, read-only integrity checks for a dependency-free pure-Python Wheel.

A RECORD hash is not an external signature or a guarantee of clinical security.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import re
import stat
import zipfile
from email.parser import BytesParser
from email.policy import default

MAX_MEMBERS = 10000
MAX_TOTAL_UNCOMPRESSED = 256 * 1024 * 1024
MAX_MEMBER_UNCOMPRESSED = 16 * 1024 * 1024
MAX_METADATA = 65536
FORBIDDEN_PAYLOAD_SUFFIXES = (
    ".pyd",
    ".dll",
    ".so",
    ".dylib",
    ".exe",
    ".pth",
    ".pyc",
    ".pyo",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
)


def inspect_core_wheel_archive(
    archive: zipfile.ZipFile, *, metadata_path: str, distribution: str, version: str
) -> list[str]:
    """Reject malformed layout, missing payload hash coverage, and hostile members."""
    issues: list[str] = []
    name = re.sub(r"[-_.]+", "_", distribution)
    prefix = f"{name}-{version}.dist-info/"
    if metadata_path != prefix + "METADATA":
        issues.append("core wheel METADATA path disagrees with distribution/version")

    infos = archive.infolist()
    if len(infos) > MAX_MEMBERS:
        return ["core wheel has too many members"]
    files: dict[str, zipfile.ZipInfo] = {}
    folded: set[str] = set()
    total_size = 0
    for info in infos:
        path = info.filename
        components = path.split("/")
        if (
            not path
            or path.startswith("/")
            or "\\" in path
            or ":" in path
            or "\x00" in path
            or any(part in {"", ".", ".."} for part in components[:-1])
            or (not info.is_dir() and components[-1] in {"", ".", ".."})
            or (info.is_dir() and components[-1] != "")
        ):
            issues.append("core wheel contains unsafe member path")
            continue
        if path.casefold() in folded:
            issues.append("core wheel contains duplicate or case-colliding members")
        folded.add(path.casefold())
        if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
            issues.append("core wheel contains symbolic link")
        if not info.is_dir() and not path.startswith(prefix):
            lowered = path.casefold()
            if lowered.endswith(FORBIDDEN_PAYLOAD_SUFFIXES) or ".data/" in lowered:
                issues.append("core wheel contains native executable or installer payload")
        if info.file_size > MAX_MEMBER_UNCOMPRESSED:
            issues.append("core wheel member exceeds size bound")
        total_size += info.file_size
        if not info.is_dir():
            files[path] = info
    if total_size > MAX_TOTAL_UNCOMPRESSED:
        issues.append("core wheel expanded payload exceeds size bound")
    if issues:
        return sorted(set(issues))

    wheel_name = prefix + "WHEEL"
    record_name = prefix + "RECORD"
    if wheel_name not in files or record_name not in files:
        return ["core wheel WHEEL or RECORD missing"]
    if files[wheel_name].file_size > MAX_METADATA or files[record_name].file_size > 2_000_000:
        return ["core wheel control metadata exceeds size bound"]
    if any(path.endswith(".dist-info/METADATA") and path != metadata_path for path in files):
        return ["core wheel has conflicting metadata directories"]

    wheel_meta = BytesParser(policy=default).parsebytes(archive.read(wheel_name))
    if (
        wheel_meta.get_all("Wheel-Version") != ["1.0"]
        or wheel_meta.get_all("Root-Is-Purelib") != ["true"]
        or wheel_meta.get_all("Tag") != ["py3-none-any"]
    ):
        issues.append("core wheel purity or platform tag is not qualified")

    try:
        record_text = archive.read(record_name).decode("utf-8")
        rows = list(csv.reader(io.StringIO(record_text, newline=""), strict=True))
    except (UnicodeError, csv.Error):
        return [*issues, "core wheel RECORD invalid UTF-8 or CSV"]
    index: dict[str, tuple[str, str]] = {}
    for row in rows:
        if len(row) != 3 or not row[0] or row[0] in index:
            issues.append("core wheel RECORD contains malformed or duplicate row")
            continue
        index[row[0]] = (row[1], row[2])
    if set(index) != set(files):
        issues.append("core wheel RECORD must cover each archive file exactly once")
    if index.get(record_name) != ("", ""):
        issues.append("core wheel RECORD self-entry must have empty digest and size")
    if issues:
        return sorted(set(issues))

    for path, info in files.items():
        if path == record_name:
            continue
        stored_digest, size = index[path]
        if not re.fullmatch(r"sha256=[A-Za-z0-9_-]{43}", stored_digest):
            issues.append("core wheel RECORD must use canonical SHA-256")
            break
        if size != str(info.file_size):
            issues.append("core wheel RECORD size differs from archive")
            break
        hasher = hashlib.sha256()
        count = 0
        with archive.open(info) as reader:
            while chunk := reader.read(1024 * 1024):
                count += len(chunk)
                if count > MAX_MEMBER_UNCOMPRESSED:
                    issues.append("core wheel streamed member exceeds bound")
                    break
                hasher.update(chunk)
        encoded = base64.urlsafe_b64encode(hasher.digest()).rstrip(b"=").decode("ascii")
        if stored_digest != "sha256=" + encoded or count != info.file_size:
            issues.append("core wheel RECORD digest mismatch")
            break
    return sorted(set(issues))
