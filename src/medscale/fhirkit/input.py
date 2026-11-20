"""Bounded, unambiguous local FHIR JSON admission for Core CLI.

This is an input parser, NOT FHIR structural/profile/clinical validation.
"""

from __future__ import annotations

import json
import math
import os
import stat
from pathlib import Path
from typing import Any

MAX_FHIR_INPUT_BYTES = 2 * 1024 * 1024
MAX_FHIR_JSON_DEPTH = 64
MAX_FHIR_INTEGER_DIGITS = 128


class FhirInputError(ValueError):
    """A local document was refused before a report can be created."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise FhirInputError("duplicate_json_key")
        output[key] = value
    return output


def _reject_nonfinite(value: str) -> None:
    raise FhirInputError("nonfinite_json_number")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise FhirInputError("nonfinite_json_number")
    return parsed


def _bounded_int(value: str) -> int:
    if len(value.lstrip("-")) > MAX_FHIR_INTEGER_DIGITS:
        raise FhirInputError("json_integer_too_long")
    return int(value)


def _check_depth(root: Any) -> None:
    stack = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        if depth > MAX_FHIR_JSON_DEPTH:
            raise FhirInputError("json_nesting_too_deep")
        if isinstance(node, dict):
            stack.extend(
                (item, depth + 1) for item in node.values() if isinstance(item, (dict, list))
            )
        elif isinstance(node, list):
            stack.extend((item, depth + 1) for item in node if isinstance(item, (dict, list)))


def read_fhir_json_document(source: Path) -> dict[str, Any]:
    """Read one regular UTF-8 JSON object without ambiguous input or unbounded I/O.

    No network, implicit filename normalization, external schema, or JSON
    coercion is performed. POSIX opens use O_NOFOLLOW for the final component.
    This is NOT a Windows junction/ancestor-reparse or concurrent-writer defense.
    """
    if source.is_symlink():
        raise FhirInputError("symlink_input_refused")
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(source, flags)
        with os.fdopen(fd, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise FhirInputError("input_not_regular_file")
            if metadata.st_size > MAX_FHIR_INPUT_BYTES:
                raise FhirInputError("input_size_limit_exceeded")
            raw = stream.read(MAX_FHIR_INPUT_BYTES + 1)
    except OSError as exc:
        raise FhirInputError("input_file_unavailable") from exc

    if len(raw) > MAX_FHIR_INPUT_BYTES:
        raise FhirInputError("input_size_limit_exceeded")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise FhirInputError("input_not_utf8") from exc
    if text.startswith("\ufeff"):
        raise FhirInputError("utf8_bom_not_allowed")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
            parse_float=_finite_float,
            parse_int=_bounded_int,
        )
    except FhirInputError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise FhirInputError("malformed_json") from exc
    if not isinstance(value, dict):
        raise FhirInputError("json_root_not_object")
    _check_depth(value)
    return value
