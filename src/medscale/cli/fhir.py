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

from medscale.fhirkit.report import load_report_from_json, report_to_json
from medscale.fhirkit.storage import store_report
from medscale.fhirkit.validate import validate_fhir


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
        payload = json.loads(args.input_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"input read error: {exc}", file=sys.stderr)
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
