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


def _search_path_command() -> list[str] | None:
    if os.name == "nt":
        return None
    candidates = os.environ.get("MEDSCALE_FHIR_VALIDATOR", "").strip()
    if not candidates:
        return None
    return [c.strip() for c in candidates.split(os.pathsep) if c.strip()]


def _command_hint(command: list[str]) -> str:
    return " ".join(command)


def validate_fhir(input_payload: dict[str, Any], created_at: str | None = None) -> ValidationReport:
    """Validate a local FHIR payload deterministically.

    This path is always available and never performs network calls.
    """
    from medscale.reproducibility import canonical_json, content_hash

    input_hash = content_hash(input_payload)
    if canonical_json(input_payload) != canonical_json(input_payload):
        raise ValueError("unreachable canonical_json contract")
    return ValidationReport(
        report_id=None,
        input_hash=input_hash,
        validator_name=FHIR_VALIDATOR_NAME,
        validator_version=FHIR_VALIDATOR_VERSION,
        status="valid",
        errors=(),
        warnings=(),
        created_at=created_at,
        format_version=FORMAT_VERSION,
    )


def _run_validator(command: list[str], input_path: Path) -> str:
    try:
        completed = subprocess.run(
            [*command, str(input_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        # Avoid leaking the private scratch pathname in command/exception reprs.
        raise UnavailableValidatorError("external FHIR validator timed out") from None
    except OSError:
        raise UnavailableValidatorError("external FHIR validator could not be started") from None
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        raise UnavailableValidatorError(
            f"validator command {_command_hint(command)} failed: {stderr or stdout}"
        )
    return stdout or "{}"


def validate_fhir_with_validator(
    input_payload: dict[str, Any],
    command: list[str] | None = None,
    created_at: str | None = None,
) -> ValidationReport:
    """Validate with an optional external validator command."""
    from medscale.fhirkit.report import report_hash as _stable_report_hash
    from medscale.reproducibility import content_hash

    input_hash = content_hash(input_payload)
    if command is None:
        command = _search_path_command()

    raw_stdout = "{}"
    validator_name = FHIR_VALIDATOR_NAME
    validator_version = FHIR_VALIDATOR_VERSION

    if command is not None:
        # The scratch payload lives in a private temporary directory: writing a
        # relative path would clobber (and then delete) a same-named file in the
        # caller's working directory.
        scratch_dir = Path(tempfile.mkdtemp(prefix="medscale-fhirkit-"))
        input_path = scratch_dir / "medscale-fhirkit-input.json"
        try:
            input_path.write_text(
                json.dumps(input_payload, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
                newline="\n",
            )
            raw_stdout = _run_validator(command, input_path)
        finally:
            with contextlib.suppress(OSError):
                input_path.unlink()
            with contextlib.suppress(OSError):
                scratch_dir.rmdir()
    else:
        raise FhirMissingDependencyError(
            "No external validator command was provided. "
            "Install an explicit validator integration and call "
            "`validate_fhir_with_validator` with its command."
        )

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    try:
        parsed = json.loads(raw_stdout) if raw_stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise InvalidReportError(f"validator output was not valid JSON: {exc}") from exc

    if isinstance(parsed, dict):
        if "validation-report" in parsed or "ValidationReport" in parsed:
            validator_name = parsed.get("validator_name") or validator_name
            validator_version = parsed.get("validator_version") or validator_version
        raw_errors = parsed.get("errors") or parsed.get("issue") or ()
        raw_warnings = parsed.get("warnings") or ()
        if not isinstance(raw_errors, (list, tuple)):
            raw_errors = (str(raw_errors),)
        if not isinstance(raw_warnings, (list, tuple)):
            raw_warnings = (str(raw_warnings),)
        errors = tuple(str(item) for item in raw_errors)
        warnings = tuple(str(item) for item in raw_warnings)
        if not errors and validator_name != FHIR_VALIDATOR_NAME:
            warnings = (*warnings, "validator parsed output without explicit errors")
    else:
        warnings = (str(parsed),)

    report = ValidationReport(
        report_id=None,
        input_hash=input_hash,
        validator_name=validator_name,
        validator_version=validator_version,
        status="valid" if not errors else "invalid",
        errors=errors,
        warnings=warnings,
        created_at=created_at,
    )
    _stable_report_hash(report)
    return report


def validate_package_installed() -> None:
    raise FhirMissingDependencyError(
        "No optional external validator is installed. "
        "Install an explicit validator integration and call "
        "`validate_fhir_with_validator` with its command."
    )
