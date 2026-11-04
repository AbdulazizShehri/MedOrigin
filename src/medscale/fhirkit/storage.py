"""FHIR artifact storage contract: content-addressed, immutable, deterministic.

Only a locally trusted output directory is supported. Exclusive file creation
prevents replacing a preexisting file or following a final-component link.
Link checks on directory components are a best-effort preflight, NOT a defence
against a malicious concurrent process swapping directories (TOCTOU).
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

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
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def _default_root() -> Path:
    return Path("data") / "fhirkit"


def _linked(path: Path) -> bool:
    junction = getattr(path, "is_junction", None)
    return path.is_symlink() or (junction is not None and junction())


def _reject_links(path: Path) -> None:
    """Refuse symlink/junction components without resolving through them."""
    current = path.absolute()
    for candidate in (current, *current.parents):
        if _linked(candidate):
            raise FhirStorageError("linked FHIR report path forbidden")


def _read_existing_report(path: Path, expected: bytes | None = None) -> bytes:
    _reject_links(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise FhirStorageError("FHIR report unavailable") from exc
    try:
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise FhirStorageError("linked or nonregular FHIR report forbidden")
            if expected is not None and info.st_size != len(expected):
                raise FhirStorageError("existing FHIR report content mismatch")
            contents = stream.read()
            if len(contents) != info.st_size:
                raise FhirStorageError("FHIR report changed during read")
            if expected is not None and contents != expected:
                raise FhirStorageError("existing FHIR report content mismatch")
            return contents
    except OSError as exc:
        raise FhirStorageError("FHIR report unavailable") from exc


def store_report(report: ValidationReport, root: Path | None = None) -> Path:
    """Store a report exactly once, never replacing any existing filesystem item.

    A byte-identical, already stored *regular single-link* report may be
    returned without rewriting it. A changed artifact is evidence of corruption
    and must never be silently repaired or overwritten.
    """
    root = root if root is not None else _default_root()
    report_bytes = report_to_json(report).encode("utf-8")
    report_id = report_hash(report)
    if _HASH_PATTERN.fullmatch(report_id) is None:
        raise FhirStorageError("invalid FHIR report artifact id")
    target_dir = fhirkit_reports_dir(root) / report_id
    target_path = target_dir / _DEFAULT_FILENAME

    _reject_links(target_dir)
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FhirStorageError("FHIR report directory unavailable") from exc
    _reject_links(target_dir)
    if not target_dir.is_dir():
        raise FhirStorageError("FHIR report directory unavailable")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(target_path, flags, 0o600)
    except FileExistsError:
        _read_existing_report(target_path, expected=report_bytes)
        return target_path
    except OSError as exc:
        raise FhirStorageError("FHIR report cannot be created") from exc

    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(report_bytes)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        # Leave any partially-created file in place for explicit corruption
        # diagnosis; never replace/delete a path after an ambiguous write.
        raise FhirStorageError("FHIR report write incomplete") from exc
    return target_path


def load_report(report_hash_value: str, root: Path | None = None) -> str:
    """Load only a well-formed content-addressed report from a trusted root."""
    if _HASH_PATTERN.fullmatch(report_hash_value) is None:
        raise FhirStorageError("invalid FHIR report artifact id")
    root = root if root is not None else _default_root()
    target_path = fhirkit_reports_dir(root) / report_hash_value / _DEFAULT_FILENAME
    raw = _read_existing_report(target_path)
    try:
        serialized = raw.decode("utf-8")
        parsed = load_report_from_json(serialized)
        if report_hash(parsed) != report_hash_value or report_to_json(parsed) != serialized:
            raise FhirStorageError("FHIR report checksum or canonical bytes mismatch")
        return serialized
    except (UnicodeError, InvalidReportError, ValueError, TypeError, KeyError) as exc:
        raise FhirStorageError("FHIR report contents invalid") from exc
