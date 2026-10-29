"""ValidationReport contract and deterministic helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from medscale.fhirkit.errors import InvalidReportError
from medscale.reproducibility import canonical_json

FORMAT_VERSION = "fhirkit-validation-report/v1"
_NULLABLE_STRINGS = (
    "report_id",
    "input_hash",
    "validator_name",
    "validator_version",
    "status",
    "created_at",
    "format_version",
)
_LIST_FIELDS = ("errors", "warnings")


@dataclass(frozen=True)
class ValidationReport:
    """Deterministic validation report for FHIR boundary outputs."""

    report_id: str | None = None
    input_hash: str | None = None
    validator_name: str | None = None
    validator_version: str | None = None
    status: str | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    created_at: str | None = None
    format_version: str = FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_report_schema(self)


def validate_report_schema(report: ValidationReport) -> None:
    """Fail fast on incompatible report shapes."""
    if not isinstance(report, ValidationReport):
        raise InvalidReportError("report must be a ValidationReport instance")
    if report.format_version != FORMAT_VERSION:
        raise InvalidReportError(
            f"format_version must be {FORMAT_VERSION!r}, got {report.format_version!r}"
        )
    for key in ("report_id", "input_hash", "validator_name", "validator_version", "created_at"):
        value = getattr(report, key)
        if value is not None and not isinstance(value, str):
            raise InvalidReportError("report metadata must be text or null")
    if report.status is not None and report.status not in ("valid", "invalid"):
        raise InvalidReportError("report status must be valid, invalid or null")
    for diagnostics in (report.errors, report.warnings):
        if not isinstance(diagnostics, tuple) or not all(
            isinstance(item, str) for item in diagnostics
        ):
            raise InvalidReportError("report diagnostics must be text tuples")
    # Prevent a persisted report from contradicting its own diagnostics:
    # success must never coexist with an explicit validation error.
    if report.status == "valid" and report.errors:
        raise InvalidReportError("valid report cannot contain errors")


def _sorted_report_payload(report: ValidationReport) -> dict[str, Any]:
    payload = asdict(report)
    for key in _NULLABLE_STRINGS:
        if payload.get(key) is None:
            payload[key] = ""
    payload["errors"] = sorted(payload.get("errors", []) or [])
    payload["warnings"] = sorted(payload.get("warnings", []) or [])
    return payload


def report_hash(report: ValidationReport) -> str:
    """Return a stable SHA-256 for the report payload."""
    validate_report_schema(report)
    payload = _sorted_report_payload(report)
    serialized = canonical_json(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def report_to_json(report: ValidationReport) -> str:
    """Serialize a report to stable JSON with deterministic field ordering."""
    validate_report_schema(report)
    payload = _sorted_report_payload(report)
    return canonical_json(payload) + "\n"


def _unique_report_properties(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate report JSON key")
        obj[key] = value
    return obj


def _reject_nonfinite_report_number(_value: str) -> Any:
    raise ValueError("non-finite report number")


def load_report_from_json(raw: str) -> ValidationReport:
    """Read a legacy-compatible report, rejecting ambiguous/untyped JSON."""
    try:
        data = json.loads(
            raw,
            object_pairs_hook=_unique_report_properties,
            parse_constant=_reject_nonfinite_report_number,
        )
        json.dumps(data, allow_nan=False)
    except (json.JSONDecodeError, TypeError, ValueError, OverflowError):
        # Do not reproduce untrusted report contents in exception messages.
        raise InvalidReportError("report JSON must be strict and unambiguous") from None
    if not isinstance(data, dict):
        raise InvalidReportError("report JSON must decode to an object")
    data.setdefault("format_version", FORMAT_VERSION)
    for key in _LIST_FIELDS:
        value = data.get(key)
        if value is None:
            data[key] = []
        elif not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise InvalidReportError("report errors and warnings must be text arrays")
    for key in _NULLABLE_STRINGS:
        data.setdefault(key, None)
        if data[key] is not None and not isinstance(data[key], str):
            raise InvalidReportError("report metadata must be text or null")
    report = ValidationReport(
        report_id=data["report_id"],
        input_hash=data["input_hash"],
        validator_name=data["validator_name"],
        validator_version=data["validator_version"],
        status=data["status"],
        errors=tuple(data.get("errors", []) or []),
        warnings=tuple(data.get("warnings", []) or []),
        created_at=data["created_at"],
        format_version=data["format_version"],
    )
    validate_report_schema(report)
    return report
