"""Fail closed before publishing a synthetic-only MedOrigin base Core distribution.

Check both the exact Wheel and sdist metadata: neither may advertise *any*
optional extra or third-party runtime dependency until that distribution
scope has a separate security review and approved source-bound projection.

This is an additional read-only publisher gate, NOT a tag/release creator,
independent security signoff, or scientific source migration.
"""

from __future__ import annotations

import argparse
import gzip
import io
import itertools
import json
import os
import re
import stat
import struct
import tarfile
import tempfile
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path

_MAX_ARCHIVE_BYTES = 30_000_000
_MAX_METADATA_BYTES = 262_144
_MAX_MEMBERS = 2000
_MAX_SINGLE_MEMBER_BYTES = 30_000_000
_MAX_TOTAL_DECLARED_BYTES = 50_000_000
_MAX_TAR_INFLATED_BYTES = _MAX_TOTAL_DECLARED_BYTES + _MAX_MEMBERS * 2048
_WHEEL_METADATA = re.compile(r"medscale-[^/]+[.]dist-info/METADATA")
_SDIST_METADATA = re.compile(r"medscale-[^/]+/PKG-INFO")
_ZIP_EOCD = struct.Struct("<4s4H2LH")
_ZIP_LOCAL_HEADER = struct.Struct("<4s5H3L2H")


class PublicationScopeError(ValueError):
    """Nonclinical base Core publication scope is not demonstrably safe."""


class _BoundedInflatedReader(io.RawIOBase):
    """Bound gzip TAR bytes including headers/PAX before a tar parser sees them."""

    def __init__(self, stream: gzip.GzipFile) -> None:
        super().__init__()
        self._stream = stream
        self._read = 0

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        remaining = _MAX_TAR_INFLATED_BYTES - self._read
        if remaining < 0:
            raise PublicationScopeError("sdist: inflated TAR envelope exceeds budget")
        if size < 0 or size > remaining + 1:
            size = remaining + 1
        chunk = self._stream.read(size)
        self._read += len(chunk)
        if self._read > _MAX_TAR_INFLATED_BYTES:
            raise PublicationScopeError("sdist: inflated TAR envelope exceeds budget")
        return chunk


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


def _verify_wheel_physical_envelope(path: Path, members: list[zipfile.ZipInfo]) -> None:
    """Reject ZIP payload outside a single canonical, comment-free Wheel envelope.

    ZipFile permits prepended self-extracting payloads, trailing junk and
    archive comments. None is required for our bounded release artifacts.
    The central directory must immediately precede the final EOCD record.
    """
    size = path.stat().st_size
    if size < _ZIP_EOCD.size or not members:
        raise PublicationScopeError("wheel: malformed ZIP envelope")
    with path.open("rb") as stream:
        stream.seek(-_ZIP_EOCD.size, io.SEEK_END)
        trailer = stream.read(_ZIP_EOCD.size)
    if len(trailer) != _ZIP_EOCD.size:
        raise PublicationScopeError("wheel: incomplete ZIP trailer")
    (
        signature,
        disk,
        directory_disk,
        disk_members,
        total_members,
        directory_size,
        directory_offset,
        comment_size,
    ) = _ZIP_EOCD.unpack(trailer)
    if (
        signature != b"PK\x05\x06"
        or disk != 0
        or directory_disk != 0
        or disk_members != total_members
        or total_members != len(members)
        or comment_size != 0
    ):
        raise PublicationScopeError("wheel: noncanonical ZIP trailer or comment")
    if directory_offset + directory_size != size - _ZIP_EOCD.size:
        raise PublicationScopeError("wheel: unaccounted ZIP envelope bytes")
    # The central directory can be shifted by editing its EOCD offset while
    # inserting arbitrary bytes between ZIP members and the directory. Verify
    # the exact local-header/data boundaries instead of trusting ZipFile's
    # permissive directory index.
    cursor = 0
    with path.open("rb") as stream:
        for member in sorted(members, key=lambda item: item.header_offset):
            if member.header_offset != cursor:
                raise PublicationScopeError("wheel: hidden ZIP member gap")
            stream.seek(cursor)
            raw = stream.read(_ZIP_LOCAL_HEADER.size)
            if len(raw) != _ZIP_LOCAL_HEADER.size:
                raise PublicationScopeError("wheel: incomplete local ZIP header")
            (
                signature,
                _version,
                flags,
                compression,
                _time,
                _date,
                _crc,
                compressed_size,
                uncompressed_size,
                filename_length,
                extra_length,
            ) = _ZIP_LOCAL_HEADER.unpack(raw)
            if (
                signature != b"PK\x03\x04"
                or flags & 0x08
                or compression != member.compress_type
                or compressed_size != member.compress_size
                or uncompressed_size != member.file_size
            ):
                raise PublicationScopeError("wheel: local ZIP header mismatch")
            cursor += _ZIP_LOCAL_HEADER.size + filename_length + extra_length + member.compress_size
    if cursor != directory_offset:
        raise PublicationScopeError("wheel: hidden ZIP member gap")


def _wheel(path: Path) -> EmailMessage:
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > _MAX_MEMBERS:
                raise PublicationScopeError("wheel: archive member limit exceeded")
            total = 0
            for item in members:
                if item.file_size < 0 or item.file_size > _MAX_SINGLE_MEMBER_BYTES:
                    raise PublicationScopeError("wheel: inflated member exceeds budget")
                total += item.file_size
                if total > _MAX_TOTAL_DECLARED_BYTES:
                    raise PublicationScopeError("wheel: inflated archive exceeds budget")
            _verify_wheel_physical_envelope(path, members)
            matches = [m for m in members if _WHEEL_METADATA.fullmatch(m.filename)]
            if len(matches) != 1 or matches[0].is_dir():
                raise PublicationScopeError("wheel: exactly one METADATA required")
            item = matches[0]
            if item.file_size > _MAX_METADATA_BYTES:
                raise PublicationScopeError("wheel: METADATA exceeds budget")
            raw = archive.read(item)
            parsed = _metadata(raw, "wheel")
            expected = f"medscale-{parsed['Version']}.dist-info/METADATA"
            if item.filename != expected:
                raise PublicationScopeError("wheel: dist-info version disagrees with metadata")
            return parsed
    except (OSError, RuntimeError, zipfile.BadZipFile, ValueError) as exc:
        if isinstance(exc, PublicationScopeError):
            raise
        raise PublicationScopeError("wheel: invalid archive") from exc


def _bounded_sdist_metadata(archive: tarfile.TarFile) -> tuple[EmailMessage, int]:
    total = 0
    matches = 0
    last_member_end = 0
    metadata_bytes: bytes | None = None
    metadata_path: str | None = None
    for count, item in enumerate(archive, start=1):
        if count > _MAX_MEMBERS:
            raise PublicationScopeError("sdist: archive member limit exceeded")
        if item.size < 0 or item.size > _MAX_SINGLE_MEMBER_BYTES:
            raise PublicationScopeError("sdist: inflated member exceeds budget")
        total += item.size
        if total > _MAX_TOTAL_DECLARED_BYTES:
            raise PublicationScopeError("sdist: inflated archive exceeds budget")
        last_member_end = max(last_member_end, item.offset_data + ((item.size + 511) // 512) * 512)
        if _SDIST_METADATA.fullmatch(item.name):
            matches += 1
            if matches > 1 or not item.isfile():
                raise PublicationScopeError("sdist: exactly one regular PKG-INFO required")
            if item.size > _MAX_METADATA_BYTES:
                raise PublicationScopeError("sdist: PKG-INFO exceeds budget")
            member = archive.extractfile(item)
            if member is None:
                raise PublicationScopeError("sdist: PKG-INFO unreadable")
            with member:
                metadata_bytes = member.read(_MAX_METADATA_BYTES + 1)
                metadata_path = item.name
    if matches != 1 or metadata_bytes is None:
        raise PublicationScopeError("sdist: exactly one regular PKG-INFO required")
    parsed = _metadata(metadata_bytes, "sdist")
    if metadata_path != f"medscale-{parsed['Version']}/PKG-INFO":
        raise PublicationScopeError("sdist: source directory version disagrees with metadata")
    return parsed, last_member_end


def _verify_sdist_physical_envelope(path: Path, last_member_end: int) -> None:
    """Reject appended gzip members, invalid footers and hidden TAR bytes.

    This second streaming pass validates every compressed byte; a streaming TAR
    reader alone stops at its logical end and need not check the gzip footer.
    """
    decoder = zlib.decompressobj(wbits=31)
    inflated = 0
    with path.open("rb") as stream:
        while chunk := stream.read(65_536):
            if decoder.eof:
                raise PublicationScopeError("sdist: trailing gzip data")
            capacity = _MAX_TAR_INFLATED_BYTES + 1 - inflated
            if capacity <= 0:
                raise PublicationScopeError("sdist: inflated TAR envelope exceeds budget")
            raw = decoder.decompress(chunk, capacity)
            start = inflated
            inflated += len(raw)
            if inflated > _MAX_TAR_INFLATED_BYTES or decoder.unconsumed_tail:
                raise PublicationScopeError("sdist: inflated TAR envelope exceeds budget")
            if decoder.unused_data:
                raise PublicationScopeError("sdist: appended gzip data")
            trailer_start = max(0, last_member_end - start)
            if trailer_start < len(raw) and any(raw[trailer_start:]):
                raise PublicationScopeError("sdist: hidden TAR trailer")
    if not decoder.eof:
        raise PublicationScopeError("sdist: incomplete gzip stream")
    if inflated < last_member_end + 1024 or inflated % 512:
        raise PublicationScopeError("sdist: malformed TAR terminator")


def _sdist(path: Path) -> EmailMessage:
    try:
        # Stream the gzip TAR; getmembers() materializes the entire inflated
        # index before a caller can enforce a file-count or inflation budget.
        # Bound declared sizes before extracting any metadata entry.
        with (
            gzip.open(path, "rb") as inflater,
            tarfile.open(fileobj=_BoundedInflatedReader(inflater), mode="r|") as archive,
        ):
            metadata, last_member_end = _bounded_sdist_metadata(archive)
        _verify_sdist_physical_envelope(path, last_member_end)
        return metadata
    except (OSError, EOFError, tarfile.TarError, zlib.error, ValueError) as exc:
        if isinstance(exc, PublicationScopeError):
            raise
        raise PublicationScopeError("sdist: invalid archive") from exc


def _has_untrusted_ancestor_alias(dist: Path) -> bool:
    """Fail closed on lexical symlink/junction ancestors of publisher inputs.

    A direct dist.is_symlink() check misses ordinary child directories reached
    through an alias. This is static pathname admission, NOT an atomic
    defense against concurrent filesystem swaps or a security approval.
    """
    # Never query an untrusted Windows UNC/device/extended path, which may
    # reach a remote share or an alternate namespace before lstat.
    if os.name == "nt" and dist.drive.startswith("\\\\"):
        return True
    absolute = dist.absolute()  # Do not resolve(): that hides the alias.
    for component in (absolute, *absolute.parents):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode):
            return True
        if os.name == "nt" and (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            return True
    return False


@contextmanager
def _posix_pinned_scope_archives(
    dist: Path, packages: dict[str, list[Path]]
) -> Iterator[dict[str, list[Path]]]:
    """Read bounded publisher inputs through no-follow dirfds into private copies.

    All ZIP/TAR reads, metadata parsing and physical-envelope passes must use
    the copies, never attacker-replaceable original dist filenames. This is
    source-only gate hardening, not a publish-time filesystem lock or a
    Windows HANDLE-pinning guarantee.
    """
    if os.name == "nt":
        raise PublicationScopeError("POSIX pinned scope is unavailable on Windows")
    names = {kind: packages[kind][0].name for kind in ("wheel", "sdist")}
    if len(set(names.values())) != 2:
        raise PublicationScopeError("dist: artifact filenames are not unique")
    components = dist.absolute().parts
    if (
        not components
        or components[0] != "/"
        or any(part in {".", ".."} for part in components[1:])
    ):
        raise PublicationScopeError("dist: noncanonical POSIX directory")
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = -1
    try:
        descriptor = os.open("/", dir_flags)
        for component in components[1:]:
            next_fd = os.open(component, dir_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
        with os.scandir(descriptor) as listing:
            entries = list(itertools.islice(listing, 3))
        if (
            len(entries) != 2
            or {entry.name for entry in entries} != set(names.values())
            or any(not entry.is_file(follow_symlinks=False) for entry in entries)
        ):
            raise PublicationScopeError("dist: unexpected pinned directory contents")
        with tempfile.TemporaryDirectory(prefix="medorigin-core-scope-pinned-") as temporary:
            private = Path(temporary).resolve(strict=True)
            copies: dict[str, list[Path]] = {}
            for kind, name in names.items():
                fd = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=descriptor,
                )
                with os.fdopen(fd, "rb") as source:
                    before = os.fstat(source.fileno())
                    if not stat.S_ISREG(before.st_mode) or before.st_size > _MAX_ARCHIVE_BYTES:
                        raise PublicationScopeError(f"{kind}: unqualified pinned input")
                    copied = 0
                    target = private / name
                    with target.open("xb") as output:
                        while chunk := source.read(
                            min(1024 * 1024, _MAX_ARCHIVE_BYTES + 1 - copied)
                        ):
                            copied += len(chunk)
                            if copied > _MAX_ARCHIVE_BYTES:
                                raise PublicationScopeError(f"{kind}: pinned input too large")
                            output.write(chunk)
                    after = os.fstat(source.fileno())
                    before_id = (
                        before.st_dev,
                        before.st_ino,
                        before.st_size,
                        before.st_mtime_ns,
                        before.st_ctime_ns,
                    )
                    after_id = (
                        after.st_dev,
                        after.st_ino,
                        after.st_size,
                        after.st_mtime_ns,
                        after.st_ctime_ns,
                    )
                    if copied != before.st_size or before_id != after_id:
                        raise PublicationScopeError(f"{kind}: pinned input mutated")
                    copies[kind] = [target]
            yield copies
    except OSError as exc:
        raise PublicationScopeError("dist: cannot pin publisher archive safely") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


@contextmanager
def _windows_pinned_scope_archives(
    dist: Path, packages: dict[str, list[Path]]
) -> Iterator[dict[str, list[Path]]]:
    """Read original Windows archives from native file HANDLEs into private copies.

    A FILE_SHARE_READ-only, OPEN_REPARSE_POINT CreateFileW handle prevents
    writable/delete-sharing opens while held and refuses the final symlink.
    This is deliberately NOT directory-ancestor HANDLE pinning, atomic
    two-artifact validation, or a guarantee about a later publisher reopen.
    """
    if os.name != "nt":
        raise PublicationScopeError("Windows pinned scope is unavailable on POSIX")
    import ctypes
    import msvcrt

    names = {kind: packages[kind][0].name for kind in ("wheel", "sdist")}
    if len(set(names.values())) != 2:
        raise PublicationScopeError("dist: artifact filenames are not unique")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    create_file.restype = ctypes.c_void_p
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (ctypes.c_void_p,)
    close_handle.restype = ctypes.c_int
    invalid = ctypes.c_void_p(-1).value

    class _FileTime(ctypes.Structure):
        _fields_ = [  # noqa: RUF012 - ctypes requires mutable field descriptors
            ("dwLowDateTime", ctypes.c_uint32),
            ("dwHighDateTime", ctypes.c_uint32),
        ]

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [  # noqa: RUF012 - ctypes requires mutable field descriptors
            ("dwFileAttributes", ctypes.c_uint32),
            ("ftCreationTime", _FileTime),
            ("ftLastAccessTime", _FileTime),
            ("ftLastWriteTime", _FileTime),
            ("dwVolumeSerialNumber", ctypes.c_uint32),
            ("nFileSizeHigh", ctypes.c_uint32),
            ("nFileSizeLow", ctypes.c_uint32),
            ("nNumberOfLinks", ctypes.c_uint32),
            ("nFileIndexHigh", ctypes.c_uint32),
            ("nFileIndexLow", ctypes.c_uint32),
        ]

    get_info = kernel32.GetFileInformationByHandle
    get_info.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(_ByHandleFileInformation),
    )
    get_info.restype = ctypes.c_int
    # Open the *directory* before any final archive paths, denying rename and
    # delete sharing while the two private copies are captured. OPEN_REPARSE_POINT
    # prevents an NTFS junction from being silently dereferenced at this boundary.
    directory_handle = create_file(
        str(dist),
        0x00000080,  # FILE_READ_ATTRIBUTES
        0x00000001,  # FILE_SHARE_READ (no FILE_SHARE_DELETE)
        None,
        3,  # OPEN_EXISTING
        0x02000000 | 0x00200000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
        None,
    )
    if directory_handle is None or directory_handle == invalid:
        raise PublicationScopeError("dist: Windows directory HANDLE open refused")
    try:
        info = _ByHandleFileInformation()
        if not get_info(directory_handle, ctypes.byref(info)):
            raise PublicationScopeError("dist: Windows directory HANDLE cannot be inspected")
        if (info.dwFileAttributes & 0x00000400) or not (
            info.dwFileAttributes & 0x00000010
        ):
            raise PublicationScopeError("dist: Windows junction/reparse directory refused")
        # An attacker may replace a lexical parent with a junction after the
        # initial preflight. Reject that alias a second time *while pinned*.
        try:
            if _has_untrusted_ancestor_alias(dist):
                raise PublicationScopeError("dist: Windows junction/reparse ancestor refused")
        except (OSError, ValueError) as exc:
            raise PublicationScopeError("dist: Windows ancestor cannot be checked") from exc
        with os.scandir(dist) as listing:
            entries = list(itertools.islice(listing, 3))
        if (
            len(entries) != 2
            or {entry.name for entry in entries} != set(names.values())
            or any(not entry.is_file(follow_symlinks=False) for entry in entries)
        ):
            raise PublicationScopeError("dist: pinned Windows directory contents changed")
        with tempfile.TemporaryDirectory(prefix="medorigin-core-scope-pinned-") as temporary:
            private = Path(temporary).resolve(strict=True)
            copies: dict[str, list[Path]] = {}
            for kind, name in names.items():
                raw_handle = create_file(
                    str(dist / name),
                    0x80000000,  # GENERIC_READ
                    0x00000001,  # FILE_SHARE_READ; refuse concurrent WRITE/DELETE share
                    None,
                    3,  # OPEN_EXISTING
                    0x00200000 | 0x08000000,  # OPEN_REPARSE_POINT | SEQUENTIAL_SCAN
                    None,
                )
                if raw_handle is None or raw_handle == invalid:
                    raise PublicationScopeError(f"{kind}: Windows HANDLE open refused")
                try:
                    fd = msvcrt.open_osfhandle(raw_handle, os.O_RDONLY | os.O_BINARY)
                except OSError:
                    close_handle(raw_handle)
                    raise
                with os.fdopen(fd, "rb") as source:
                    before = os.fstat(source.fileno())
                    if (
                        not stat.S_ISREG(before.st_mode)
                        or before.st_size > _MAX_ARCHIVE_BYTES
                        or getattr(before, "st_file_attributes", 0)
                        & stat.FILE_ATTRIBUTE_REPARSE_POINT
                    ):
                        raise PublicationScopeError(f"{kind}: linked or oversized Windows source")
                    copied = 0
                    target = private / name
                    with target.open("xb") as output:
                        while chunk := source.read(
                            min(1024 * 1024, _MAX_ARCHIVE_BYTES + 1 - copied)
                        ):
                            copied += len(chunk)
                            if copied > _MAX_ARCHIVE_BYTES:
                                raise PublicationScopeError(
                                    f"{kind}: Windows source exceeds budget"
                                )
                            output.write(chunk)
                    after = os.fstat(source.fileno())
                    before_id = (
                        before.st_dev,
                        before.st_ino,
                        before.st_size,
                        before.st_mtime_ns,
                        before.st_ctime_ns,
                    )
                    after_id = (
                        after.st_dev,
                        after.st_ino,
                        after.st_size,
                        after.st_mtime_ns,
                        after.st_ctime_ns,
                    )
                    if copied != before.st_size or before_id != after_id:
                        raise PublicationScopeError(f"{kind}: Windows source mutated during read")
                copies[kind] = [target]
            yield copies
    except OSError as exc:
        raise PublicationScopeError("dist: Windows archive HANDLE cannot be pinned") from exc
    finally:
        close_handle(directory_handle)


def _inspect_scope_metadata(
    packages: dict[str, list[Path]], issues: list[str], versions: dict[str, str]
) -> None:
    for kind, check in (("wheel", _wheel), ("sdist", _sdist)):
        item = packages[kind][0]
        if item.is_symlink() or not item.is_file() or item.stat().st_size > _MAX_ARCHIVE_BYTES:
            issues.append(f"{kind}: missing, linked or oversized archive")
            continue
        try:
            metadata = check(item)
            version = str(metadata["Version"])
            versions[kind] = version
            if kind == "wheel":
                prefix = re.escape(f"medscale-{version}")
                filename_ok = (
                    re.fullmatch(
                        rf"{prefix}(?:-[0-9][A-Za-z0-9_.]*)?"
                        r"-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+[.]whl",
                        item.name,
                    )
                    is not None
                )
            else:
                filename_ok = item.name == f"medscale-{version}.tar.gz"
            if not filename_ok:
                issues.append(f"{kind}: filename does not match metadata version")
            issues.extend(_check_policy(metadata, kind))
        except PublicationScopeError as exc:
            issues.append(str(exc))
    if len(versions) == 2 and versions["wheel"] != versions["sdist"]:
        issues.append("Wheel and sdist package versions disagree")


def inspect(dist: Path) -> dict[str, object]:
    issues: list[str] = []
    # The tagged publisher uses dist/*, so checking only medscale-* while
    # ignoring an extra payload is not sufficient. Enumerate at most THREE
    # top-level entries and reject any artifact other than the expected pair.
    # Use lstat-style checks so directories and symlinks cannot be treated
    # as regular publisher inputs. No archive is extracted or uploaded.
    try:
        untrusted_alias = _has_untrusted_ancestor_alias(dist)
    except (OSError, ValueError):
        untrusted_alias = True
    if untrusted_alias or dist.is_symlink() or not dist.is_dir():
        issues.append("unexpected artifact directory contents")
        entries: list[os.DirEntry[str]] = []
    else:
        with os.scandir(dist) as listing:
            entries = list(itertools.islice(listing, 3))
    packages = {
        "wheel": [
            dist / entry.name
            for entry in entries
            if entry.name.startswith("medscale-") and entry.name.endswith(".whl")
        ],
        "sdist": [
            dist / entry.name
            for entry in entries
            if entry.name.startswith("medscale-") and entry.name.endswith(".tar.gz")
        ],
    }
    if (
        len(entries) != 2 or any(not entry.is_file(follow_symlinks=False) for entry in entries)
    ) and entries:
        issues.append("unexpected artifact directory contents")
    for kind in ("wheel", "sdist"):
        if len(packages[kind]) != 1:
            issues.append(f"{kind}: exactly one MedOrigin artifact required")
    versions: dict[str, str] = {}
    if not issues:
        try:
            # Windows pins each final file HANDLE; POSIX pins the full
            # directory ancestry with dirfds. Both analyze private snapshots.
            # Neither makes a later dist/* publisher reopen race-free.
            snapshot = (
                _windows_pinned_scope_archives(dist, packages)
                if os.name == "nt"
                else _posix_pinned_scope_archives(dist, packages)
            )
            with snapshot as pinned:
                _inspect_scope_metadata(pinned, issues, versions)
        except PublicationScopeError as exc:
            issues.append(str(exc))
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
