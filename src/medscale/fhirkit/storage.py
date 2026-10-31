"""FHIR artifact storage contract: content-addressed, immutable, deterministic."""

from __future__ import annotations

import os
import re
import stat
import tempfile
from contextlib import suppress
from pathlib import Path, PureWindowsPath

from medscale._layout import fhirkit_reports_dir
from medscale.fhirkit.errors import FhirStorageError, InvalidReportError
from medscale.fhirkit.report import (
    ValidationReport,
    load_report_from_json,
    report_hash,
    report_to_json,
)

__all__ = ["fhirkit_reports_dir", "load_report", "store_report"]

_DEFAULT_FILENAME = "report.json"
# Reversible developer-Beta admission bound; not an approved release policy.
_MAX_REPORT_ARTIFACT_BYTES = 8 * 1024 * 1024


def _open_posix_directory_nofollow(directory: Path, *, create: bool = False) -> int:
    """Return a pinned directory FD, walking from / without following symlinks.

    For creation, mkdirat operates relative to each pinned parent, rather than
    allowing a checked pathname to be swapped to an attacker-owned directory.
    The caller owns the returned descriptor.
    """
    absolute = directory.absolute()
    if ".." in absolute.parts:
        raise FhirStorageError("refusing a noncanonical FHIR report path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory_fd = os.open(absolute.anchor, flags)
    try:
        for component in absolute.parts[1:]:
            if create:
                with suppress(FileExistsError):
                    os.mkdir(component, dir_fd=directory_fd)
            child_fd = os.open(component, flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = child_fd
        result, directory_fd = directory_fd, -1
        return result
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)


def _open_posix_report_nofollow(target_path: Path, flags: int) -> int:
    """Open a report relative to a pinned, symlink-free POSIX directory."""
    directory_fd = _open_posix_directory_nofollow(target_path.parent)
    try:
        return os.open(target_path.name, flags, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)


def _read_bounded_regular_descriptor(descriptor: int) -> str:
    """Consume and close an already-open regular-file FD under the size bound."""
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise FhirStorageError("FHIR report artifact is not a regular file")
        if metadata.st_size > _MAX_REPORT_ARTIFACT_BYTES:
            raise FhirStorageError("FHIR report artifact exceeds size limit")
        raw = source.read(_MAX_REPORT_ARTIFACT_BYTES + 1)
    if len(raw) > _MAX_REPORT_ARTIFACT_BYTES:
        raise FhirStorageError("FHIR report artifact exceeds size limit")
    return raw.decode("utf-8")


def _read_bounded_regular_report(target_path: Path, *, secure_posix_ancestors: bool = False) -> str:
    """Read only a bounded regular artifact; never wait on a FIFO or device.

    O_NONBLOCK prevents POSIX FIFO opens from waiting for a writer. On load,
    POSIX opens every ancestor with O_NOFOLLOW using pinned directory FDs.
    Windows and the separate report-creation path still require race hardening.
    """
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = (
        _open_posix_report_nofollow(target_path, flags)
        if secure_posix_ancestors and os.name != "nt"
        else os.open(target_path, flags)
    )
    return _read_bounded_regular_descriptor(descriptor)


def _default_root() -> Path:
    return Path("data") / "fhirkit"


def reject_unsafe_windows_local_path(
    path: str | Path, *, windows: bool | None = None, subject: str = "FHIR JSON input"
) -> None:
    """Reject UNC/device/ADS paths and ambiguous Win32 aliases without IO."""
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return

    raw = str(path).replace("/", "\\")
    parsed = PureWindowsPath(raw)
    message = f"{subject} must be a local regular file path"
    if raw.startswith("\\") or (parsed.drive and not parsed.is_absolute()):
        raise ValueError(message)
    prefix = 2 if len(raw) >= 2 and raw[0].isalpha() and raw[1] == ":" else 0
    if ":" in raw[prefix:]:
        raise ValueError(message)
    for component in parsed.parts:
        if component in (parsed.anchor, parsed.drive, ".", ".."):
            continue
        stem = component.split(".", 1)[0].rstrip(" ").upper()
        if (
            component.rstrip(" .") != component
            or stem in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
            or re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", stem) is not None
        ):
            raise ValueError(message)


def _reject_unsafe_windows_report_root(root: Path) -> None:
    """Refuse network/device/ADS report roots before any filesystem probe."""
    try:
        reject_unsafe_windows_local_path(root, subject="FHIR report root")
    except ValueError as exc:
        raise FhirStorageError("FHIR report root must be a local regular file path") from exc


def _reject_report_directory_symlinks(root: Path, digest: str) -> None:
    """Reject static symlinks and Windows junctions in report directory paths.

    This is a path-layout safeguard, not an OS-enforced guarantee against a
    hostile process swapping directories between checks and file operations.
    """
    reports_dir = fhirkit_reports_dir(root)
    # A POSIX ancestor can be a symlink even when root itself is not.
    # Check every lexical root ancestor on all platforms, then the generated
    # report directories. Windows additionally checks junction/reparse flags.
    absolute_root = root.absolute()
    directories: tuple[Path, ...] = (
        *absolute_root.parents,
        absolute_root,
        reports_dir.parent,
        reports_dir,
        reports_dir / digest,
    )
    for directory in directories:
        if directory.is_symlink():
            raise FhirStorageError("refusing a symlinked report directory")
        if os.name == "nt":
            try:
                metadata = directory.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise FhirStorageError("unable to inspect FHIR report directory") from exc
            if getattr(metadata, "st_file_attributes", 0) & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
            ):
                raise FhirStorageError("refusing a Windows reparse-point report directory")


def _assert_posix_store_directory_pinned(target_dir: Path, directory_fd: int) -> None:
    """Fail if the public path no longer points to the pinned store directory."""
    verification_fd = _open_posix_directory_nofollow(target_dir)
    try:
        pinned, current = os.fstat(directory_fd), os.fstat(verification_fd)
        if (pinned.st_dev, pinned.st_ino) != (current.st_dev, current.st_ino):
            raise FhirStorageError("FHIR report directory changed during publication")
    finally:
        os.close(verification_fd)


def _store_posix_report(
    report_json: str, root: Path, digest: str, target_dir: Path, target_path: Path
) -> Path:
    """Stage, link and clean up relative to one pinned POSIX directory inode.

    This blocks symlink-swap redirection of mkdir, temporary writes, hard-link
    publication and cleanup. A hostile rename *after return* is not preventable
    by a file API and is not a filesystem-ownership or release-security proof.
    """
    _reject_report_directory_symlinks(root, digest)
    directory_fd = -1
    temporary_name: str | None = None
    try:
        directory_fd = _open_posix_directory_nofollow(target_dir, create=True)
        _reject_report_directory_symlinks(root, digest)
        _assert_posix_store_directory_pinned(target_dir, directory_fd)
        temporary_name = f".report-{os.urandom(16).hex()}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        temporary_fd = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        with os.fdopen(temporary_fd, "w", encoding="utf-8", newline="\n") as output:
            output.write(report_json)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(
                temporary_name,
                _DEFAULT_FILENAME,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            try:
                existing_fd = os.open(
                    _DEFAULT_FILENAME,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=directory_fd,
                )
                existing = _read_bounded_regular_descriptor(existing_fd)
            except (OSError, UnicodeError) as read_exc:
                raise FhirStorageError("existing FHIR report is unreadable") from read_exc
            if existing != report_json:
                raise FhirStorageError(
                    "existing FHIR report differs from canonical content"
                ) from exc
        _assert_posix_store_directory_pinned(target_dir, directory_fd)
    except OSError as exc:
        raise FhirStorageError("unable to create FHIR report artifact") from exc
    finally:
        if directory_fd >= 0:
            try:
                if temporary_name is not None:
                    with suppress(FileNotFoundError):
                        os.unlink(temporary_name, dir_fd=directory_fd)
            except OSError as exc:
                raise FhirStorageError("unable to clean temporary FHIR report artifact") from exc
            finally:
                os.close(directory_fd)
    return target_path


def store_report(report: ValidationReport, root: Path | None = None) -> Path:
    """Store a report in deterministic content-addressed storage."""
    root = root or _default_root()
    _reject_unsafe_windows_report_root(root)
    report_json = report_to_json(report)
    if len(report_json.encode("utf-8")) > _MAX_REPORT_ARTIFACT_BYTES:
        raise FhirStorageError("FHIR report artifact exceeds size limit")
    report_hash_value = report_hash(report)
    target_dir = fhirkit_reports_dir(root) / report_hash_value
    target_path = target_dir / _DEFAULT_FILENAME
    if os.name != "nt":
        return _store_posix_report(report_json, root, report_hash_value, target_dir, target_path)
    _reject_report_directory_symlinks(root, report_hash_value)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _reject_report_directory_symlinks(root, report_hash_value)
    temporary_path: Path | None = None
    try:
        # Writing directly to report.json exposes a truncated canonical file
        # if the process stops midway. Stage complete bytes on the same volume,
        # flush before publication, then use a no-clobber hard link. An
        # unsupported hard-link filesystem fails closed; never use os.replace.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".report-",
            suffix=".tmp",
            dir=target_dir,
            delete=False,
        ) as output:
            temporary_path = Path(output.name)
            output.write(report_json)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary_path, target_path)
        except FileExistsError as exc:
            if target_path.is_symlink():
                raise FhirStorageError("refusing a symlink at the FHIR report path") from exc
            try:
                existing = _read_bounded_regular_report(target_path)
            except (OSError, UnicodeError) as read_exc:
                raise FhirStorageError("existing FHIR report is unreadable") from read_exc
            if existing != report_json:
                raise FhirStorageError(
                    "existing FHIR report differs from canonical content"
                ) from exc
    except OSError as exc:
        raise FhirStorageError("unable to create FHIR report artifact") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError as exc:
                raise FhirStorageError("unable to clean temporary FHIR report artifact") from exc
    return target_path


def load_report(report_hash_value: str, root: Path | None = None) -> str:
    """Load a stored report by deterministic artifact id."""
    if (
        not isinstance(report_hash_value, str)
        or re.fullmatch(r"[0-9a-f]{64}", report_hash_value) is None
    ):
        raise FhirStorageError("report address must be a canonical SHA-256 digest")
    root = root or _default_root()
    _reject_unsafe_windows_report_root(root)
    target_path = fhirkit_reports_dir(root) / report_hash_value / _DEFAULT_FILENAME
    _reject_report_directory_symlinks(root, report_hash_value)
    if target_path.is_symlink():
        raise FhirStorageError("refusing a symlink at the FHIR report path")
    try:
        raw = _read_bounded_regular_report(target_path, secure_posix_ancestors=True)
    except (OSError, UnicodeError) as exc:
        raise FhirStorageError("missing or unreadable FHIR report artifact") from exc
    try:
        report = load_report_from_json(raw)
        if report_hash(report) != report_hash_value or report_to_json(report) != raw:
            raise FhirStorageError("invalid or noncanonical FHIR report artifact")
    except (InvalidReportError, KeyError, TypeError, ValueError) as exc:
        raise FhirStorageError("invalid or noncanonical FHIR report artifact") from exc
    return raw
