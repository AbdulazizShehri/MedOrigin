"""Optional FHIR validator boundary."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from medscale.fhirkit.errors import (
    FhirMissingDependencyError,
    InvalidReportError,
    UnavailableValidatorError,
)
from medscale.fhirkit.report import (
    FORMAT_VERSION,
    ValidationReport,
)

FHIR_VALIDATOR_NAME = "medscale-fhirkit-local"
FHIR_VALIDATOR_VERSION = "0.1.0"
EXTERNAL_UNQUALIFIED_VALIDATOR_NAME = "medscale-fhirkit-external-unqualified"
EXTERNAL_UNQUALIFIED_WARNING = (
    "External FHIR validator output is not source-qualified; "
    "FHIR R4 structural/profile/terminology and clinical conformance "
    "remain unverified."
)
EXTERNAL_UNQUALIFIED_ERROR = "external_validator_reported_errors_unverified"
_MAX_EXTERNAL_OUTPUT = 64_000
_MAX_EXTERNAL_ISSUES = 32
LOCAL_UNVERIFIED_WARNING = (
    "FHIR R4 schema, terminology, and profile validation were not performed; "
    "this local report records deterministic provenance only."
)


def _search_path_command() -> list[str] | None:
    if os.name == "nt":
        return None
    candidates = os.environ.get("MEDSCALE_FHIR_VALIDATOR", "").strip()
    if not candidates:
        return None
    return [c.strip() for c in candidates.split(os.pathsep) if c.strip()]


def validate_fhir(input_payload: dict[str, Any], created_at: str | None = None) -> ValidationReport:
    """Record local FHIR-shaped JSON provenance without asserting conformance.

    No FHIR R4 schema/profile/terminology validator runs in this baseline.
    Returning "valid" would falsely certify unvalidated data. This path
    remains deterministic and never performs network calls.
    """
    from medscale.reproducibility import content_hash

    input_hash = content_hash(input_payload)
    return ValidationReport(
        report_id=None,
        input_hash=input_hash,
        validator_name=FHIR_VALIDATOR_NAME,
        validator_version=FHIR_VALIDATOR_VERSION,
        status="not_validated",
        errors=(),
        warnings=(LOCAL_UNVERIFIED_WARNING,),
        created_at=created_at,
        format_version=FORMAT_VERSION,
    )


def _run_validator(command: list[str], input_path: Path) -> str:
    """Bound the untrusted subprocess and never echo its stdout/stderr/path."""
    if (
        type(command) is not list
        or not 1 <= len(command) <= 16
        or any(
            type(piece) is not str or not piece or "\\x00" in piece or len(piece) > 2048
            for piece in command
        )
    ):
        raise UnavailableValidatorError("external_validator_command_refused")
    try:
        completed = subprocess.run(
            [*command, str(input_path)],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise UnavailableValidatorError("external_validator_execution_refused") from exc
    if completed.returncode != 0:
        raise UnavailableValidatorError("external_validator_nonzero_exit_refused")
    if not 0 < len(completed.stdout) <= _MAX_EXTERNAL_OUTPUT:
        raise InvalidReportError("external_validator_output_bounds_refused")
    return completed.stdout


def _unqualified_external_issue_presence(parsed: object) -> bool:
    """Admit only issue/severity SHAPE; never copy validator-generated text.

    A nonempty explicit error list, or a FHIR OperationOutcome with error/
    fatal issue severity, may classify the source as structurally suspect.
    An empty response, 'success', or a warning-only response can NEVER
    certify validity: its only permitted result is 'not_validated'.
    """
    if not isinstance(parsed, dict):
        raise InvalidReportError("external_validator_json_shape_refused")

    explicit_errors = parsed.get("errors", [])
    raw_issues = parsed.get("issue", [])
    raw_warnings = parsed.get("warnings", [])
    if (
        type(explicit_errors) is not list
        or type(raw_issues) is not list
        or type(raw_warnings) is not list
        or any(
            len(array) > _MAX_EXTERNAL_ISSUES
            for array in (explicit_errors, raw_issues, raw_warnings)
        )
    ):
        raise InvalidReportError("external_validator_issues_shape_refused")
    has_errors = bool(explicit_errors)
    for item in raw_issues:
        if not isinstance(item, dict):
            raise InvalidReportError("external_validator_issue_item_refused")
        severity = item.get("severity")
        if severity not in ("error", "fatal", "warning", "information"):
            raise InvalidReportError("external_validator_issue_severity_refused")
        if severity in ("error", "fatal"):
            has_errors = True
    return has_errors


def validate_fhir_with_validator(
    input_payload: dict[str, Any],
    command: list[str] | None = None,
    created_at: str | None = None,
) -> ValidationReport:
    """Run a caller-supplied external tool but NEVER assert FHIR conformance.

    No source-qualified external protocol or trust chain exists here. Even a
    response claiming success is unverified, never 'valid'; reported issues
    are reduced to one fixed, non-content-bearing error token. This API is
    a deprecated/experimental untrusted adapter, not a clinical validator.
    """
    from medscale.fhirkit.report import report_hash as _stable_report_hash
    from medscale.reproducibility import content_hash

    input_hash = content_hash(input_payload)
    if command is None:
        command = _search_path_command()
    if command is None:
        raise FhirMissingDependencyError(
            "No source-qualified external FHIR validator is configured."
        )

    # The existing sandbox is intentionally private and disposable, but this
    # explicit legacy adapter is still unsuitable for PHI or untrusted tools.
    scratch_dir = Path(tempfile.mkdtemp(prefix="medscale-fhirkit-"))
    input_path = scratch_dir / "medscale-fhirkit-input.json"
    try:
        input_path.write_text(
            json.dumps(input_payload, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
            newline=None,
        )
        raw = _run_validator(command, input_path)
    finally:
        with contextlib.suppress(OSError):
            input_path.unlink()
        with contextlib.suppress(OSError):
            scratch_dir.rmdir()

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise InvalidReportError("external_validator_json_refused") from exc
    has_errors = _unqualified_external_issue_presence(parsed)
    report = ValidationReport(
        report_id=None,
        input_hash=input_hash,
        validator_name=EXTERNAL_UNQUALIFIED_VALIDATOR_NAME,
        validator_version=FHIR_VALIDATOR_VERSION,
        status="invalid" if has_errors else "not_validated",
        errors=(EXTERNAL_UNQUALIFIED_ERROR,) if has_errors else (),
        warnings=(EXTERNAL_UNQUALIFIED_WARNING,),
        created_at=created_at,
        format_version=FORMAT_VERSION,
    )
    _stable_report_hash(report)
    return report


def validate_package_installed() -> None:
    raise FhirMissingDependencyError(
        "No optional external validator is installed. "
        "Install an explicit validator integration and call "
        "`validate_fhir_with_validator` with its command."
    )
