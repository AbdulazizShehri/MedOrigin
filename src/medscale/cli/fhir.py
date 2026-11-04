"""FHIR boundary CLI: ``medscale fhir validate``.

Stability: supported public CLI surface for the FHIR boundary introduced in
M5.  Uses :mod:`argparse` directly, consistent with the rest of the shipped
MedScale CLI, so no additional runtime dependencies are required.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from medscale.fhirkit.errors import FhirStorageError
from medscale.fhirkit.report import load_report_from_json, report_to_json
from medscale.fhirkit.storage import store_report
from medscale.fhirkit.validate import validate_fhir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="medscale fhir validate",
        description="Record a deterministic local FHIR report without claiming schema conformance.",
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to a local FHIR-shaped JSON file (no schema validation by default).",
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
            "When omitted, local provenance is recorded with status not_validated."
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
        payload = json.loads(args.input_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"input read error: {exc}", file=sys.stderr)
        return 1

    if args.summary_only:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        return 0

    if args.validator_command:
        print(
            "external FHIR validator integration is not wired in this baseline; "
            "the local path only records unverified provenance.",
            file=sys.stderr,
        )
        return 2

    report = validate_fhir(payload, created_at=args.created_at)
    try:
        path = store_report(report, root=args.output_dir)
    except FhirStorageError:
        # Filesystem exceptions may contain absolute patient-workspace paths.
        # Do not print a positive FHIR report or disclose those paths.
        print("FHIR_REPORT_STORAGE_BLOCKED", file=sys.stderr)
        return 2
    print(report_to_json(load_report_from_json(report_to_json(report))))
    print(f"report stored at: {path}", file=sys.stderr)
    # Exit nonzero unless an actual validated status is available; an
    # unverified provenance receipt must not masquerade as FHIR validation.
    return 0 if report.status == "valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
