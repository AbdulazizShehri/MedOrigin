"""FHIR artifact storage contract: content-addressed, immutable, deterministic."""

from __future__ import annotations

import re
from pathlib import Path

from medscale._layout import fhirkit_reports_dir
from medscale.fhirkit.errors import FhirStorageError
from medscale.fhirkit.report import (
    ValidationReport,
    load_report_from_json,
    report_hash,
    report_to_json,
)

__all__ = ["fhirkit_reports_dir", "load_report", "store_report"]

_DEFAULT_FILENAME = "report.json"


def _default_root() -> Path:
    return Path("data") / "fhirkit"


def store_report(report: ValidationReport, root: Path | None = None) -> Path:
    """Store a report in deterministic content-addressed storage."""
    root = root or _default_root()
    report_json = report_to_json(report)
    report_hash_value = report_hash(report)
    target_dir = fhirkit_reports_dir(root) / report_hash_value
    target_path = target_dir / _DEFAULT_FILENAME
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Exclusive creation is atomic: never truncate an existing artifact or
        # follow a pre-existing report.json symlink to an unrelated user file.
        with target_path.open("x", encoding="utf-8", newline="\n") as output:
            output.write(report_json)
    except FileExistsError as exc:
        if target_path.is_symlink():
            raise FhirStorageError("refusing a symlink at the FHIR report path") from exc
        try:
            existing = target_path.read_text(encoding="utf-8")
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
    target_path = fhirkit_reports_dir(root) / report_hash_value / _DEFAULT_FILENAME
    if target_path.is_symlink():
        raise FhirStorageError("refusing a symlink at the FHIR report path")
    try:
        raw = target_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FhirStorageError("missing or unreadable FHIR report artifact") from exc
    try:
        report = load_report_from_json(raw)
        if report_hash(report) != report_hash_value or report_to_json(report) != raw:
            raise FhirStorageError("invalid or noncanonical FHIR report artifact")
    except (KeyError, TypeError, ValueError) as exc:
        raise FhirStorageError("invalid or noncanonical FHIR report artifact") from exc
    return raw
