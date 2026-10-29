"""FHIR boundary CLI: ``medscale fhir validate``.

Stability: supported public CLI surface for the FHIR boundary introduced in
M5.  Uses :mod:`argparse` directly, consistent with the rest of the shipped
MedScale CLI, so no additional runtime dependencies are required.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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
        payload = json.loads(
            args.input_file.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_members,
            parse_constant=_reject_non_json_constant,
        )
    except (ValueError, UnicodeError, OSError) as exc:
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
    path = store_report(report, root=args.output_dir)
    print(report_to_json(load_report_from_json(report_to_json(report))))
    print(f"report stored at: {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
