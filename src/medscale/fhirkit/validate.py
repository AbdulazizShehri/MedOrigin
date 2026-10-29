"""Optional FHIR validator boundary."""

from __future__ import annotations

import contextlib
import json
import math
import os
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from medscale.fhirkit.errors import (
    FhirMissingDependencyError,
    FhirValidationError,
    InvalidReportError,
    UnavailableValidatorError,
)
from medscale.fhirkit.report import (
    FORMAT_VERSION,
    ValidationReport,
)

FHIR_VALIDATOR_NAME = "medscale-fhirkit-local"
FHIR_VALIDATOR_VERSION = "0.1.0"
_VALIDATOR_TIMEOUT_SECONDS = 120
_VALIDATOR_OUTPUT_LIMIT_BYTES = 1024 * 1024


def _search_path_command() -> list[str] | None:
    if os.name == "nt":
        return None
    candidates = os.environ.get("MEDSCALE_FHIR_VALIDATOR", "").strip()
    if not candidates:
        return None
    return [c.strip() for c in candidates.split(os.pathsep) if c.strip()]


def _require_strict_json_values(payload: dict[str, Any]) -> None:
    """Fail before hashing or launching a validator on non-JSON Python input.

    This is an RFC 8259 value/key check, not FHIR schema conformance.
    """

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str):
                    raise FhirValidationError("FHIR JSON object keys must be strings")
                visit(key)
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str):
            # json.dumps defaults to ensure_ascii=True, which can hide lone
            # surrogates until UTF-8 encoding fails during report hashing.
            if any("\ud800" <= char <= "\udfff" for char in value):
                raise FhirValidationError("FHIR input contains invalid Unicode JSON text")
        elif value is None or isinstance(value, (int, bool)):
            return
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise FhirValidationError("FHIR input contains non-finite JSON values")
        else:
            raise FhirValidationError("FHIR input contains unsupported JSON values")

    try:
        visit(payload)
        json.dumps(payload, sort_keys=True, allow_nan=False)
    except (RecursionError, TypeError, ValueError, OverflowError):
        raise FhirValidationError("FHIR input contains invalid JSON values") from None


def validate_fhir(input_payload: dict[str, Any], created_at: str | None = None) -> ValidationReport:
    """Check the minimum FHIR resource envelope without network access.

    This deterministic local path does *not* check FHIR schemas, profiles,
    element cardinalities or clinical correctness. A positive result is
    only a resource-envelope preflight, not complete FHIR conformance.
    """
    from medscale.reproducibility import content_hash

    if not isinstance(input_payload, dict):
        raise FhirValidationError("FHIR resource must be a JSON object")
    _require_strict_json_values(input_payload)

    resource_type = input_payload.get("resourceType")
    valid_envelope = (
        isinstance(resource_type, str)
        and re.fullmatch(r"[A-Z][A-Za-z0-9]*", resource_type) is not None
    )
    return ValidationReport(
        report_id=None,
        input_hash=content_hash(input_payload),
        validator_name=FHIR_VALIDATOR_NAME,
        validator_version=FHIR_VALIDATOR_VERSION,
        status="valid" if valid_envelope else "invalid",
        errors=() if valid_envelope else ("invalid or missing FHIR resourceType",),
        warnings=(),
        created_at=created_at,
        format_version=FORMAT_VERSION,
    )


def _strict_validator_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON object properties at any nesting depth."""
    parsed: dict[str, Any] = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError("duplicate validator JSON member")
        parsed[key] = value
    return parsed


def _reject_validator_nonfinite_constant(_value: str) -> Any:
    raise ValueError("non-finite validator JSON constant")


def _run_validator(command: list[str], input_path: Path) -> str:
    """Capture both streams with bounded memory and terminate noisy validators."""
    try:
        process = subprocess.Popen(
            [*command, str(input_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, ValueError, TypeError, IndexError):
        # Never leak untrusted executable/argument content on spawn failures.
        raise UnavailableValidatorError("external FHIR validator could not be started") from None

    captured = (bytearray(), bytearray())
    excessive_output = threading.Event()
    reader_error = threading.Event()

    def read_bounded(stream: Any, result: bytearray) -> None:
        try:
            while True:
                chunk = stream.read1(8192)
                if not chunk:
                    return
                if len(result) + len(chunk) > _VALIDATOR_OUTPUT_LIMIT_BYTES:
                    excessive_output.set()
                    return
                result.extend(chunk)
        except (OSError, ValueError):
            reader_error.set()
        finally:
            # Close in the reader itself. BufferedReader.close() acquires its
            # read lock, and calling it from the controller may hang if a
            # descendant still has this pipe open after the direct child exits.
            with contextlib.suppress(OSError, ValueError):
                stream.close()

    assert process.stdout is not None and process.stderr is not None
    readers = [
        threading.Thread(target=read_bounded, args=(process.stdout, captured[0]), daemon=True),
        threading.Thread(target=read_bounded, args=(process.stderr, captured[1]), daemon=True),
    ]
    for reader in readers:
        reader.start()

    deadline = time.monotonic() + _VALIDATOR_TIMEOUT_SECONDS
    try:
        while process.poll() is None:
            if excessive_output.is_set():
                raise UnavailableValidatorError("external FHIR validator exceeded output limit")
            if reader_error.is_set():
                raise UnavailableValidatorError("external FHIR validator output could not be read")
            if time.monotonic() >= deadline:
                raise UnavailableValidatorError("external FHIR validator timed out")
            excessive_output.wait(min(0.02, max(0.0, deadline - time.monotonic())))

        for reader in readers:
            reader.join(timeout=max(0.0, deadline - time.monotonic()))
        if any(reader.is_alive() for reader in readers):
            raise UnavailableValidatorError("external FHIR validator timed out")
        if excessive_output.is_set():
            raise UnavailableValidatorError("external FHIR validator exceeded output limit")
        if reader_error.is_set():
            raise UnavailableValidatorError("external FHIR validator output could not be read")
        try:
            stdout = captured[0].decode("utf-8").strip()
            captured[1].decode("utf-8")
        except UnicodeError:
            raise UnavailableValidatorError(
                "external FHIR validator produced undecodable output"
            ) from None
        if process.returncode != 0:
            raise UnavailableValidatorError(
                "external FHIR validator returned a nonzero exit status"
            )
        return stdout
    finally:
        if process.poll() is None:
            with contextlib.suppress(OSError):
                process.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=1)
        for reader in readers:
            reader.join(timeout=0.1)
        # Readers still blocked on an inherited pipe must own its close;
        # a controller-side close can wait indefinitely for their read lock.


def validate_fhir_with_validator(
    input_payload: dict[str, Any],
    command: list[str] | None = None,
    created_at: str | None = None,
) -> ValidationReport:
    """Validate with an optional external validator command."""
    from medscale.fhirkit.report import report_hash as _stable_report_hash
    from medscale.reproducibility import content_hash

    if not isinstance(input_payload, dict):
        raise FhirValidationError("FHIR resource must be a JSON object")
    _require_strict_json_values(input_payload)
    input_hash = content_hash(input_payload)
    if command is None:
        command = _search_path_command()

    raw_stdout = ""
    validator_name = FHIR_VALIDATOR_NAME
    validator_version = FHIR_VALIDATOR_VERSION

    if command is not None:
        # Validate the command before writing even synthetic payloads to disk.
        # Empty, non-string and NUL-bearing arguments would otherwise bubble
        # up from Popen as untyped ValueError/TypeError/IndexError exceptions.
        if (
            not isinstance(command, list)
            or not command
            or not command[0]
            or any(not isinstance(arg, str) or "\x00" in arg for arg in command)
        ):
            raise UnavailableValidatorError("invalid external validator command")
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
        parsed = (
            json.loads(
                raw_stdout,
                object_pairs_hook=_strict_validator_members,
                parse_constant=_reject_validator_nonfinite_constant,
            )
            if raw_stdout.strip()
            else None
        )
        # Python's JSON parser also permits overflow from e.g. 1e999.
        # Reject it without reproducing sensitive validator output.
        json.dumps(parsed, allow_nan=False)
    except (json.JSONDecodeError, ValueError):
        raise InvalidReportError("external validator output was not strict JSON") from None

    # No implicit success from empty stdout, '{}', arrays, scalars, or
    # OperationOutcome documents whose severities are not yet interpreted.
    # This adapter accepts only the explicit status-bearing JSON report
    # protocol; a full HL7 OperationOutcome adapter is a separate gate.
    if not isinstance(parsed, dict) or parsed.get("status") not in ("valid", "invalid"):
        raise InvalidReportError("external validator requires explicit valid or invalid status")

    if "validation-report" in parsed or "ValidationReport" in parsed:
        validator_name = parsed.get("validator_name") or validator_name
        validator_version = parsed.get("validator_version") or validator_version
    # Only accept simple text-array diagnostics from this custom protocol.
    # Arbitrary JSON values must not be stringified into user-facing reports
    # (HL7 OperationOutcome issues require a separate semantic adapter).
    for field_name in ("errors", "issue", "warnings"):
        value = parsed.get(field_name)
        if value is not None and (
            not isinstance(value, list) or not all(isinstance(item, str) for item in value)
        ):
            raise InvalidReportError("external validator diagnostics must be text arrays")
    raw_errors = parsed.get("errors") or parsed.get("issue") or ()
    raw_warnings = parsed.get("warnings") or ()
    errors = tuple(raw_errors)
    warnings = tuple(raw_warnings)
    if not errors and validator_name != FHIR_VALIDATOR_NAME:
        warnings = (*warnings, "validator parsed output without explicit errors")

    report = ValidationReport(
        report_id=None,
        input_hash=input_hash,
        validator_name=validator_name,
        validator_version=validator_version,
        status="invalid" if parsed["status"] == "invalid" or errors else "valid",
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
