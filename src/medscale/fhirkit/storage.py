"""FHIR artifact storage contract: content-addressed, immutable, deterministic."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

from medscale._layout import fhirkit_reports_dir
from medscale._windows_path_admission import reject_unsafe_windows_local_path
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


def _read_bounded_regular_report(target_path: Path) -> str:
    """Read only a bounded regular artifact; never wait on a FIFO or device.

    O_NONBLOCK prevents POSIX FIFO opens from waiting for a writer, and
    O_NOFOLLOW refuses a final-component symlink where supported. Parent
    directory races and Windows reparse-point races are not fully solved by
    these portable checks; this is not a hostile-filesystem isolation claim.
    """
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(target_path, flags), "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise FhirStorageError("FHIR report artifact is not a regular file")
        if metadata.st_size > _MAX_REPORT_ARTIFACT_BYTES:
            raise FhirStorageError("FHIR report artifact exceeds size limit")
        raw = source.read(_MAX_REPORT_ARTIFACT_BYTES + 1)
    if len(raw) > _MAX_REPORT_ARTIFACT_BYTES:
        raise FhirStorageError("FHIR report artifact exceeds size limit")
    return raw.decode("utf-8")


def _default_root() -> Path:
    return Path("data") / "fhirkit"


def _reject_unsafe_windows_report_root(root: Path) -> None:
    """Refuse network/device/ADS report roots before any filesystem probe."""
    try:
        reject_unsafe_windows_local_path(root, subject="FHIR report root")
    except ValueError as exc:
        raise FhirStorageError("FHIR report root must be a local regular file path") from exc


def _reject_report_directory_symlinks(root: Path, digest: str) -> None:
    """Reject static symlink redirection below a caller-approved storage root.

    This is a path-layout safeguard, not an OS-enforced guarantee against a
    hostile process swapping directories between checks and file operations.
    """
    reports_dir = fhirkit_reports_dir(root)
    for directory in (reports_dir.parent, reports_dir, reports_dir / digest):
        if directory.is_symlink():
            raise FhirStorageError("refusing a symlinked report directory")


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
    _reject_report_directory_symlinks(root, report_hash_value)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _reject_report_directory_symlinks(root, report_hash_value)
    try:
        # Exclusive creation is atomic: never truncate an existing artifact or
        # follow a pre-existing report.json symlink to an unrelated user file.
        with target_path.open("x", encoding="utf-8", newline="\n") as output:
            output.write(report_json)
    except FileExistsError as exc:
        if target_path.is_symlink():
            raise FhirStorageError("refusing a symlink at the FHIR report path") from exc
        try:
            existing = _read_bounded_regular_report(target_path)
        except (OSError, UnicodeError) as read_exc:
            raise FhirStorageError("existing FHIR report is unreadable") from read_exc
        if existing != report_json:
            raise FhirStorageError("existing FHIR report differs from canonical content") from exc
    except OSError as exc:
        raise FhirStorageError("unable to create FHIR report artifact") from exc
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
        raw = _read_bounded_regular_report(target_path)
    except (OSError, UnicodeError) as exc:
        raise FhirStorageError("missing or unreadable FHIR report artifact") from exc
    try:
        report = load_report_from_json(raw)
        if report_hash(report) != report_hash_value or report_to_json(report) != raw:
            raise FhirStorageError("invalid or noncanonical FHIR report artifact")
    except (InvalidReportError, KeyError, TypeError, ValueError) as exc:
        raise FhirStorageError("invalid or noncanonical FHIR report artifact") from exc
    return raw
