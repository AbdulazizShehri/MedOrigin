"""FHIR boundary CLI: ``medscale fhir validate``.

Stability: supported public CLI surface for the FHIR boundary introduced in
M5.  Uses :mod:`argparse` directly, consistent with the rest of the shipped
MedScale CLI, so no additional runtime dependencies are required.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path

from medscale.fhirkit.errors import FhirStorageError
from medscale.fhirkit.report import load_report_from_json, report_to_json
from medscale.fhirkit.storage import store_report
from medscale.fhirkit.validate import validate_fhir


def _unique_json_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject repeated property names at any depth of a FHIR JSON document."""
    unique: dict[str, object] = {}
    for key, value in pairs:
        if key in unique:
            raise ValueError("duplicate FHIR JSON property")
        unique[key] = value
    return unique


def _reject_non_json_constant(_constant: str) -> object:
    """Python's JSON decoder otherwise accepts NaN and infinities."""
    raise ValueError("non-finite number is not valid JSON")


MAX_FHIR_JSON_DEPTH = 256
# Preview CLI admission bound: prevent unbounded local-file reads before JSON parsing.
MAX_FHIR_INPUT_BYTES = 8 * 1024 * 1024


def _reject_excessive_json_nesting(raw: str) -> None:
    """Bound nesting consistently across Python JSON parser implementations.

    JSON quotes and escapes must not make literal brackets count as structure.
    This cheap scan precedes recursive parsing and performs no file writes.
    The JSON parser remains authoritative for syntax validation.
    """
    depth = 0
    quoted = False
    escaped = False
    for character in raw:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            if depth > MAX_FHIR_JSON_DEPTH:
                raise ValueError("FHIR JSON nesting limit exceeded")
        elif character in "]}":
            depth -= 1



def _read_bounded_regular_fhir_input(input_path: Path) -> bytes:
    """Read a bounded regular input without waiting on POSIX FIFOs or devices.

    Refuse final-component symlinks and use O_NOFOLLOW when available.
    Parent-directory replacement races and Windows reparse-point races are
    not fully addressed; this is not an OS sandbox or egress guarantee.
    """
    if input_path.is_symlink():
        raise ValueError("FHIR JSON input must be a regular non-symlink file")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(input_path, flags)
    except OSError:
        raise ValueError("FHIR JSON input must be a readable regular file") from None
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("FHIR JSON input must be a regular file")
        if metadata.st_size > MAX_FHIR_INPUT_BYTES:
            raise ValueError("FHIR JSON input exceeds 8 MiB limit")
        return source.read(MAX_FHIR_INPUT_BYTES + 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="medscale fhir validate",
        description="Validate a local FHIR JSON object and store the deterministic report.",
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to a local FHIR JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/fhirkit"),
        help="Directory for content-addressed FHIR report storage.",
    )
    parser.add_argument(
        "--with-validator",
        dest="validator_command",
        default=None,
        help=(
            "Optional external validator command, split on whitespace. "
            "When omitted, the deterministic local validator path is used."
        ),
    )
    parser.add_argument(
        "--created-at",
        default=None,
        help="Override report timestamp in ISO-8601 format. Defaults to now.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        default=False,
        help="Print the normalized JSON payload and exit without validation.",
    )
    # Public command is 'medscale fhir validate <file>'. Historically this
    # module also accepted the bare 'medscale fhir <file>' spelling; keep both.
    tokens = list(sys.argv[1:] if argv is None else argv)
    if tokens and tokens[0] == "validate":
        tokens.pop(0)
    args = parser.parse_args(tokens)
    if args.input_file is None or not args.input_file.exists():
        print(f"input read error: {args.input_file} does not exist", file=sys.stderr)
        return 1

    try:
        raw_bytes = _read_bounded_regular_fhir_input(args.input_file)
        if len(raw_bytes) > MAX_FHIR_INPUT_BYTES:
            raise ValueError("FHIR JSON input exceeds 8 MiB limit")
        raw_json = raw_bytes.decode("utf-8")
        _reject_excessive_json_nesting(raw_json)
        payload = json.loads(
            raw_json,
            object_pairs_hook=_unique_json_members,
            parse_constant=_reject_non_json_constant,
        )
        # json.loads accepts exponent overflow as +/-inf and escaped lone
        # surrogates as Python strings. Reject both before summary-only can
        # emit invalid JSON or validation can raise an uncaught exception.
        json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, OSError, RecursionError) as exc:
        print(f"input read error: {exc}", file=sys.stderr)
        return 1

    # A FHIR resource cannot have a scalar or array JSON root. Reject these
    # before the summary-only shortcut or any content-addressed report writes.
    if not isinstance(payload, dict):
        print("input read error: FHIR resource must be a JSON object", file=sys.stderr)
        return 1
    # This is only an essential FHIR resource envelope check. It does not
    # claim that the other elements conform to a FHIR resource/profile schema.
    resource_type = payload.get("resourceType")
    if (
        not isinstance(resource_type, str)
        or re.fullmatch(r"[A-Z][A-Za-z0-9]*", resource_type) is None
    ):
        print("input read error: FHIR resourceType must be a nonempty type name", file=sys.stderr)
        return 1

    if args.summary_only:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        return 0

    if args.validator_command:
        print(
            "external validator command is not wired in this baseline; "
            "use the local validator path instead.",
            file=sys.stderr,
        )
        return 2

    report = validate_fhir(payload, created_at=args.created_at)
    try:
        path = store_report(report, root=args.output_dir)
    except (FhirStorageError, OSError):
        # No traceback or private filesystem paths in the CLI's diagnostic.
        # Never print a successful report if it was not safely persisted.
        print("report storage error: unable to persist FHIR report", file=sys.stderr)
        return 1
    print(report_to_json(load_report_from_json(report_to_json(report))))
    print(f"report stored at: {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
