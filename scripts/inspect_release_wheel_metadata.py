"""Read-only Core wheel metadata readiness for a future MedOrigin software release.

This check is NOT publication authorization. It never rewrites metadata,
changes source files, creates tags, invokes publishers, or accesses the network.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import re
import stat
import sys
import unicodedata
import zipfile
import zlib
from contextlib import ExitStack
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

HOME = "https://github.com/AbdulazizShehri/MedOrigin"
EXPECTED_URLS = {
    "Homepage": HOME,
    "Repository": HOME,
    "Documentation": HOME + "/tree/main/docs",
    "Issues": HOME + "/issues",
}


def _wheel_filename_matches(path: Path, distribution: str, version: str | None) -> bool:
    """Bind strict candidate archive names to their PEP 427 identity and tag fields."""
    if not version or not path.name.endswith(".whl"):
        return False
    parts = path.name[:-4].split("-")
    if len(parts) not in (5, 6):
        return False
    normalized_name = re.sub(r"[-_.]+", "_", distribution).lower()
    if parts[0] != normalized_name or parts[1] != version:
        return False
    if len(parts) == 6 and not re.fullmatch(r"[0-9][A-Za-z0-9_]*", parts[2]):
        return False
    # Compressed compatibility tags may contain dots, but not empty members.
    return all(
        re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", tag) is not None for tag in parts[-3:]
    )


def _wheel_archive_member_issues(archive: zipfile.ZipFile) -> list[str]:
    """Reject platform-ambiguous or escaping ZIP entries before publication.

    Path comparison is case-insensitive and NFC-normalized so entries cannot
    collide after extraction on Windows/macOS. This inspects headers only;
    no archive member is extracted to disk.
    """
    seen: set[str] = set()
    unsafe_path = False
    duplicate = False
    symlink = False
    members = archive.infolist()
    too_many = len(members) > 10_000
    oversized = False
    oversized_total = False
    extreme_ratio = False
    uncompressed_total = 0
    for member in members:
        # Bound central-directory claims *before* any payload extraction. A
        # tiny archive can claim an arbitrarily large inflated footprint.
        uncompressed_total += member.file_size
        if member.file_size > 64 * 1024 * 1024:
            oversized = True
        if uncompressed_total > 256 * 1024 * 1024:
            oversized_total = True
        if member.file_size > member.compress_size * 1_000:
            extreme_ratio = True
        name = member.filename.removesuffix("/")
        segments = name.split("/")
        normalized_segments = [
            unicodedata.normalize("NFC", segment).casefold() for segment in segments
        ]
        # Windows strips trailing spaces/dots and treats device names as special
        # even when they carry an extension. Reject them rather than guessing
        # how an installer or filesystem would interpret the ZIP member.
        windows_ambiguous = any(
            segment != segment.rstrip(" .")
            or re.fullmatch(
                r"(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?",
                segment.rstrip(" ."),
            )
            is not None
            for segment in normalized_segments
        )
        if (
            not name
            or "\\" in name
            or any(char in name for char in '<>"|?*:')
            or any(segment in ("", ".", "..") for segment in segments)
            or any(ord(char) < 32 or ord(char) == 127 for char in name)
            or windows_ambiguous
        ):
            unsafe_path = True
        portable_name = "/".join(segment.rstrip(" .") for segment in normalized_segments)
        if portable_name in seen:
            duplicate = True
        seen.add(portable_name)
        if stat.S_ISLNK(member.external_attr >> 16):
            symlink = True
    issues: list[str] = []
    if unsafe_path:
        issues.append("wheel archive contains unsafe ZIP member path")
    if duplicate:
        issues.append("wheel archive contains duplicate ZIP member name")
    if symlink:
        issues.append("wheel archive contains symlink ZIP member")
    if too_many:
        issues.append("wheel archive contains too many ZIP members")
    if oversized:
        issues.append("wheel archive uncompressed member exceeds safety limit")
    if oversized_total:
        issues.append("wheel archive uncompressed total exceeds safety limit")
    if extreme_ratio:
        issues.append("wheel archive member compression ratio exceeds safety limit")
    return issues


def _wheel_record_issues(archive: zipfile.ZipFile, metadata_path: str) -> list[str]:
    """Verify the bounded, installable bytes against PEP 376 RECORD.

    Read each member through zipfile in streaming chunks; never extract files
    into the filesystem. This is an integrity test, not publisher provenance.
    """
    dist_info = metadata_path.rsplit("/", 1)[0]
    record_name = f"{dist_info}/RECORD"
    wheel_name = f"{dist_info}/WHEEL"
    files = {info.filename: info for info in archive.infolist() if not info.is_dir()}
    if record_name not in files or wheel_name not in files:
        return ["wheel RECORD or WHEEL missing"]
    record_info = files[record_name]
    if record_info.file_size > 4 * 1024 * 1024:
        return ["wheel RECORD exceeds safety limit"]

    try:
        text = archive.read(record_name).decode("utf-8")
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except (csv.Error, UnicodeError):
        return ["wheel RECORD is malformed"]
    declared: dict[str, tuple[str, str]] = {}
    for row in rows:
        if len(row) != 3:
            return ["wheel RECORD is malformed"]
        path, recorded_hash, recorded_size = row
        if path in declared:
            return ["wheel RECORD contains duplicate path"]
        declared[path] = (recorded_hash, recorded_size)
    if declared.keys() != files.keys():
        return ["wheel RECORD does not cover archive files"]
    if declared[record_name] != ("", ""):
        return ["wheel RECORD self-entry must have empty hash and size"]

    total_read = 0
    for name, (entry_hash, entry_size) in declared.items():
        if name == record_name:
            continue
        kind, sep, encoded = entry_hash.partition("=")
        if not sep or kind not in {"sha256", "sha384", "sha512"} or not encoded:
            return ["wheel RECORD uses unsupported or missing hash"]
        if not entry_size.isascii() or not entry_size.isdecimal():
            return ["wheel RECORD member size mismatch"]
        claimed_size = int(entry_size)
        if claimed_size != files[name].file_size:
            return ["wheel RECORD member size mismatch"]
        digest = hashlib.new(kind)
        size = 0
        with archive.open(files[name], "r") as source:
            while chunk := source.read(64 * 1024):
                size += len(chunk)
                total_read += len(chunk)
                if size > 64 * 1024 * 1024 or total_read > 256 * 1024 * 1024:
                    return ["wheel RECORD member exceeds actual read safety limit"]
                digest.update(chunk)
        if size != claimed_size:
            return ["wheel RECORD member size mismatch"]
        actual = base64.urlsafe_b64encode(digest.digest()).decode("ascii").rstrip("=")
        if encoded != actual:
            return ["wheel RECORD member hash mismatch"]
    return []



def _wheel_header_issues(
    archive: zipfile.ZipFile, metadata_path: str, filename: str
) -> list[str]:
    """Bind WHEEL compatibility tags to the actual archive filename.

    A valid RECORD hash proves internal consistency, not that a Wheel has
    installable identity headers or that its tag declarations agree.
    """
    wheel_name = f"{metadata_path.rsplit('/', 1)[0]}/WHEEL"
    info = archive.getinfo(wheel_name)
    if info.file_size > 64 * 1024:
        return ["wheel WHEEL exceeds safety limit"]

    message = BytesParser(policy=default).parsebytes(archive.read(wheel_name))
    if any(
        len(message.get_all(field, [])) != 1
        for field in ("Wheel-Version", "Root-Is-Purelib")
    ):
        return ["wheel WHEEL identity headers invalid"]
    if message.get("Wheel-Version") != "1.0":
        return ["wheel WHEEL version unsupported"]
    if message.get("Root-Is-Purelib") not in ("true", "false"):
        return ["wheel WHEEL Root-Is-Purelib invalid"]

    declared_tags = message.get_all("Tag", [])
    if not declared_tags or len(declared_tags) > 256:
        return ["wheel WHEEL tags disagree with archive filename"]
    python_tags, abi_tags, platform_tags = [
        field.split(".") for field in filename[:-4].split("-")[-3:]
    ]
    # Bound expansion of compressed wheel tags before computing the product.
    if len(python_tags) * len(abi_tags) * len(platform_tags) > 256:
        return ["wheel WHEEL tags disagree with archive filename"]
    expected_tags = {
        f"{python_tag}-{abi_tag}-{platform_tag}"
        for python_tag in python_tags
        for abi_tag in abi_tags
        for platform_tag in platform_tags
    }
    if len(set(declared_tags)) != len(declared_tags) or set(declared_tags) != expected_tags:
        return ["wheel WHEEL tags disagree with archive filename"]
    return []


def inspect_wheel(
    path: Path,
    *,
    expected_version: str | None = None,
    distribution: str = "medscale",
    require_core_only: bool = False,
) -> dict[str, object]:
    """Inspect the bytes to be installed, never source pyproject or inferred URLs."""
    issues: list[str] = []
    version: str | None = None
    actual: dict[str, str] = {}
    digest: str | None = None
    try:
        # Hash in bounded memory and inspect the exact same open file handle.
        # A path replacement between hashing and ZIP inspection must not bind
        # a digest from one artifact to metadata from another artifact.
        with ExitStack() as stack:
            stream = stack.enter_context(path.open("rb"))
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            stream.seek(0)
            archive = stack.enter_context(zipfile.ZipFile(stream))
            if require_core_only:
                issues.extend(_wheel_archive_member_issues(archive))
            metadata_paths = [
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_paths) != 1:
                issues.append("wheel must contain exactly one .dist-info/METADATA")
            else:
                info = archive.getinfo(metadata_paths[0])
                if info.file_size > 2_000_000:
                    issues.append("wheel METADATA exceeds safety limit")
                else:
                    message = BytesParser(policy=default).parsebytes(
                        archive.read(metadata_paths[0])
                    )
                    # Identity fields must be singular. Email-style parsing
                    # otherwise reads the first value and silently ignores
                    # duplicated/conflicting Name or Version headers.
                    for field in ("Metadata-Version", "Name", "Version"):
                        if len(message.get_all(field, [])) != 1:
                            issues.append(f"wheel {field} must appear exactly once")
                    version = message.get("Version")
                    if message.get("Name") != distribution:
                        issues.append(f"distribution name must remain {distribution}")
                    if require_core_only:
                        # Candidate Core-only release must not advertise *any*
                        # installable extras (even if the default install has
                        # zero dependencies). Existing frozen research extras
                        # remain blocked under #622 until a separately governed
                        # new package lineage is qualified.
                        if message.get_all("Provides-Extra"):
                            issues.append("core-only wheel advertises optional extras")
                        if message.get_all("Requires-Dist"):
                            issues.append("core-only wheel declares dependencies")
                    if not version:
                        issues.append("wheel version missing")
                    elif expected_version is not None and version != expected_version:
                        issues.append("wheel version disagrees with expected candidate")
                    if require_core_only and not _wheel_filename_matches(
                        path, distribution, version
                    ):
                        issues.append(
                            "wheel filename does not match distribution/version and wheel tags"
                        )
                    if version:
                        # Bind the inspected METADATA to the actual top-level
                        # wheel distribution/version directory, not an unrelated
                        # or nested .dist-info entry with plausible headers.
                        directory_names = {distribution, distribution.replace("-", "_")}
                        expected_paths = {
                            f"{name}-{version}.dist-info/METADATA" for name in directory_names
                        }
                        if metadata_paths[0] not in expected_paths:
                            issues.append("wheel METADATA path does not match distribution/version")
                    for item in message.get_all("Project-URL", []):
                        key, sep, value = str(item).partition(",")
                        key, value = key.strip(), value.strip()
                        if not sep or not key or key in actual:
                            issues.append("invalid or duplicate Project-URL")
                        else:
                            actual[key] = value
                    for key, url in EXPECTED_URLS.items():
                        if actual.get(key) != url:
                            issues.append(f"{key}: missing or noncanonical URL")
                    if require_core_only and actual.keys() - EXPECTED_URLS.keys():
                        # A candidate with the four approved links plus an
                        # unreviewed fifth URL must not pass the strict gate.
                        issues.append("unexpected Project-URL")
            if require_core_only and not issues and len(metadata_paths) == 1:
                issues.extend(_wheel_record_issues(archive, metadata_paths[0]))
                if not issues:
                    issues.extend(
                        _wheel_header_issues(archive, metadata_paths[0], path.name)
                    )
            # Rehash after ZIP inspection: keeping one open handle prevents a
            # path-swap race, but does not prevent an in-place write to that
            # handle between the first digest and metadata parsing.
            stream.seek(0)
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                issues.append("wheel changed during inspection")
                digest = None
    except (
        OSError,
        zipfile.BadZipFile,
        RuntimeError,
        EOFError,
        ValueError,
        NotImplementedError,
        zlib.error,
    ) as exc:
        issues.append(f"wheel unreadable: {type(exc).__name__}")

    return {
        "artifact": path.name,
        "sha256": digest,
        "distribution": distribution,
        "version": version,
        "status": "METADATA_QUALIFIED_ONLY" if not issues else "BLOCKED",
        "publication_authorized": False,
        "core_only_required": require_core_only,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument(
        "--require-core-only",
        action="store_true",
        help="Fail closed if the built wheel advertises any extras or Requires-Dist",
    )
    parser.add_argument(
        "--distribution", choices=("medscale", "medscale-workspace"), default="medscale"
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.wheel.is_file():
        parser.error("wheel file does not exist")
    result = inspect_wheel(
        args.wheel,
        expected_version=args.expected_version,
        distribution=args.distribution,
        require_core_only=args.require_core_only,
    )
    encoded = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.json_out is not None:
        args.json_out.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)
    return 0 if result["status"] == "METADATA_QUALIFIED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
