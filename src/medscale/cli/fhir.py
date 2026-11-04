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

from medscale.fhirkit.bundle import BundlePreflightError, inspect_synthetic_bundle
from medscale.fhirkit.errors import FhirMissingDependencyError, UnavailableValidatorError
from medscale.fhirkit.input import FhirInputError, read_fhir_json_document
from medscale.fhirkit.r4_schema import validate_offline_r4_json_structure
from medscale.fhirkit.report import load_report_from_json, report_to_json
from medscale.fhirkit.storage import store_report
from medscale.fhirkit.validate import validate_fhir


def _bundle_preflight_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="medscale fhir bundle-preflight",
        description=(
            "Read-only, synthetic-only local FHIR Bundle relationship check; "
            "NOT full FHIR R4 validation or permission to process patient data."
        ),
    )
    parser.add_argument("input_file", type=Path)
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Explicitly attest the input contains only invented synthetic fixtures.",
    )
    args = parser.parse_args(argv)
    if not args.synthetic_only:
        print("bundle preflight refused: synthetic_only_attestation_required", file=sys.stderr)
        return 2
    try:
        payload = read_fhir_json_document(args.input_file)
    except FhirInputError as exc:
        print(f"bundle input refused: {exc}", file=sys.stderr)
        return 1
    try:
        receipt = inspect_synthetic_bundle(payload)
    except BundlePreflightError as exc:
        print(f"bundle preflight refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


def _workspace_demo_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="medscale fhir workspace-demo",
        description=(
            "Offline encrypted ephemeral Workspace proof with a built-in "
            "fictional FHIR Bundle; NOT clinical validation or production use."
        ),
    )
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--ephemeral-demo", action="store_true")
    if argv in (["-h"], ["--help"]):
        print(parser.format_help())
        return 0
    # Exact token admission: argparse's default error echo can disclose
    # an unknown file path or other caller-provided secret in stderr.
    if len(argv) != 2 or set(argv) != {"--synthetic-only", "--ephemeral-demo"}:
        print("workspace demo refused: explicit_synthetic_demo_flags_required", file=sys.stderr)
        return 2
    try:
        from medscale.fhirkit.workspace_demo import receipt_json

        result = receipt_json()
    except ImportError:
        print("workspace demo unavailable: optional_workspace_runtime_missing", file=sys.stderr)
        return 2
    except Exception:
        # Never display caller paths, object contents or cryptographic material.
        print("workspace demo refused: encrypted_synthetic_demo_blocked", file=sys.stderr)
        return 2
    print(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    if tokens and tokens[0] == "workspace-demo":
        return _workspace_demo_main(tokens[1:])
    if tokens and tokens[0] == "bundle-preflight":
        return _bundle_preflight_main(tokens[1:])
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
        "--offline-r4-schema",
        type=Path,
        default=None,
        metavar="OFFICIAL_FHIR_R4_ZIP",
        help=(
            "Optional locally supplied, source-pinned HL7 FHIR R4 v4.0.1 JSON "
            "Schema ZIP. Runs structural checks only; a pass is not full FHIR "
            "conformance. Needs locally installed jsonschema==4.25.1."
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
    if tokens and tokens[0] == "validate":
        tokens.pop(0)
    args = parser.parse_args(tokens)
    try:
        payload = read_fhir_json_document(args.input_file)
    except FhirInputError as exc:
        # Never echo input bytes, file path, JSON snippets or PII in errors.
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

    if args.offline_r4_schema is not None:
        try:
            report = validate_offline_r4_json_structure(
                payload, args.offline_r4_schema, created_at=args.created_at
            )
        except (UnavailableValidatorError, FhirMissingDependencyError) as exc:
            print(f"offline R4 structural validator unavailable: {exc}", file=sys.stderr)
            return 2
    else:
        report = validate_fhir(payload, created_at=args.created_at)
    path = store_report(report, root=args.output_dir)
    print(report_to_json(load_report_from_json(report_to_json(report))))
    print(f"report stored at: {path}", file=sys.stderr)
    # Exit nonzero unless an actual validated status is available; an
    # unverified provenance receipt must not masquerade as FHIR validation.
    return 0 if report.status == "valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
