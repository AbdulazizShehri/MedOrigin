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


def _timeline_demo_main(argv: list[str]) -> int:
    """Real encrypted fictional source -> verified chronological patient UI data."""
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir timeline-demo --synthetic-only --ephemeral-demo\n"
            "Real AES-GCM encrypted fictional Bundle, closed/reopened verified "
            "source timeline, bounded UTC-day metadata. NO patient files, "
            "production keys, EHR, FHIR conformance or clinical authorization."
        )
        return 0
    if argv != ["--synthetic-only", "--ephemeral-demo"]:
        print(
            "timeline demo refused: exact_synthetic_ephemeral_flags_required",
            file=sys.stderr,
        )
        return 2
    try:
        from medscale.fhirkit.workspace_timeline_demo import timeline_json

        receipt = timeline_json()
    except Exception:
        print(
            "timeline demo refused: encrypted_fictional_timeline_unavailable",
            file=sys.stderr,
        )
        return 2
    print(receipt)
    return 0


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


def _bundle_structural_assessment_main(argv: list[str]) -> int:
    """Real relationship + official R4 structural-only check, source-redacted."""
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir bundle-assess "
            "--synthetic-only --offline-r4-schema OFFICIAL_R4_ZIP "
            "FICTIONAL_LOCAL_BUNDLE_JSON\n"
            "Offline narrow synthetic Bundle relationships and source-pinned "
            "HL7 FHIR R4 v4.0.1 JSON Schema (jsonschema==4.25.1). "
            "Both checks are PARTIAL and NOT full FHIR/clinical validation."
        )
        return 0
    if (
        len(argv) != 4
        or argv[0] != "--synthetic-only"
        or argv[1] != "--offline-r4-schema"
        or not argv[2]
        or not argv[3]
        or argv[2].startswith("--")
        or argv[3].startswith("--")
    ):
        print(
            "bundle assessment refused: explicit_synthetic_offline_schema_flags_required",
            file=sys.stderr,
        )
        return 2
    try:
        source = read_fhir_json_document(Path(argv[3]))
    except FhirInputError:
        print("bundle assessment refused: source_input_refused", file=sys.stderr)
        return 1
    try:
        from medscale.fhirkit.bundle_assessment import synthetic_bundle_assessment_json

        result = synthetic_bundle_assessment_json(source, Path(argv[2]), synthetic_only=True)
    except BundlePreflightError as refusal:
        # A marker-backed synthetic failure may return an actual finite
        # FHIR-shaped OperationOutcome with no source data, without running
        # the official R4 schema. A missing/malformed marker stays silent.
        try:
            from medscale.fhirkit.bundle_diagnostics import (
                rejected_synthetic_bundle_outcome_json,
            )

            negative_outcome = rejected_synthetic_bundle_outcome_json(source, refusal)
        except Exception:
            print("bundle assessment refused: relationship_preflight_refused", file=sys.stderr)
            return 2
        print(negative_outcome, end="")
        return 2
    except (UnavailableValidatorError, FhirMissingDependencyError):
        print("bundle assessment unavailable: qualified_offline_schema_missing", file=sys.stderr)
        return 2
    except Exception:
        print("bundle assessment refused: dual_assessment_contract_refused", file=sys.stderr)
        return 2
    print(result, end="")
    # This exit is NEVER clinical or full FHIR R4 validation success:
    # 'not_validated' means JSON Schema has no structural errors only.
    return 2


def _r4_structural_outcome_main(argv: list[str]) -> int:
    """Source-pinned optional local structural-only FHIR OperationOutcome.

    The only admitted order is explicit synthetic consent, a user-supplied
    official-schema ZIP path, then a fictional source JSON file. Neither
    caller path nor raw FHIR content ever appears in stdout/stderr.
    """
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir structural-outcome "
            "--synthetic-only --offline-r4-schema OFFICIAL_R4_ZIP "
            "FICTIONAL_FHIR_JSON\n"
            "Requires source-pinned official R4 4.0.1 JSON Schema and "
            "jsonschema 4.25.1 installed locally. Structure ONLY; "
            "NOT full FHIR R4 clinical conformance. Never pass patient data."
        )
        return 0
    if (
        len(argv) != 4
        or argv[0] != "--synthetic-only"
        or argv[1] != "--offline-r4-schema"
        or not argv[2]
        or not argv[3]
        or argv[2].startswith("--")
        or argv[3].startswith("--")
    ):
        print(
            "structural outcome refused: explicit_synthetic_offline_schema_flags_required",
            file=sys.stderr,
        )
        return 2
    try:
        from medscale.fhirkit.r4_outcome import structural_outcome_to_json
    except ImportError:
        print("structural outcome unavailable: core_outcome_module_missing", file=sys.stderr)
        return 2
    try:
        payload = read_fhir_json_document(Path(argv[3]))
    except FhirInputError:
        print("structural outcome refused: source_input_refused", file=sys.stderr)
        return 1
    try:
        report = validate_offline_r4_json_structure(payload, Path(argv[2]))
        encoded = structural_outcome_to_json(report)
    except (UnavailableValidatorError, FhirMissingDependencyError):
        print("structural outcome unavailable: qualified_offline_schema_missing", file=sys.stderr)
        return 2
    except Exception:
        print("structural outcome refused: bounded_structural_diagnostic_failure", file=sys.stderr)
        return 2
    # Only fixed issue keywords and general caveat in the stdout document.
    # A structurally passing input *must not* yield validated/success exit.
    print(encoded, end="")
    return 2


def _encrypted_structural_demo_main(argv: list[str]) -> int:
    """Only a hardcoded fictional Bundle; caller supplies a qualified schema ZIP."""
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir encrypted-structural-demo "
            "--synthetic-only --ephemeral-demo --offline-r4-schema OFFICIAL_R4_ZIP\n"
            "Offline, source-pinned official R4 JSON Schema and pinned jsonschema; "
            "structural check only, NOT full FHIR/clinical conformance."
        )
        return 0
    if (
        len(argv) != 4
        or argv[0] != "--synthetic-only"
        or argv[1] != "--ephemeral-demo"
        or argv[2] != "--offline-r4-schema"
        or not argv[3]
        or argv[3].startswith("--")
    ):
        print(
            "encrypted structural demo refused: exact_synthetic_demo_schema_flags_required",
            file=sys.stderr,
        )
        return 2
    try:
        from medscale.fhirkit.workspace_structural_demo import receipt_json

        result = receipt_json(Path(argv[3]))
    except ImportError:
        print(
            "encrypted structural demo unavailable: optional_workspace_runtime_missing",
            file=sys.stderr,
        )
        return 2
    except Exception:
        print(
            "encrypted structural demo refused: synthetic_structural_receipt_blocked",
            file=sys.stderr,
        )
        return 2
    print(result)
    # Demo process integrity success is NOT a FHIR structural/conformance
    # validation success; the report contains the negative-truth status.
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


def _workspace_catalog_demo_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="medscale fhir workspace-catalog-demo",
        description=(
            "Ephemeral, offline synthetic-only encrypted FHIR import catalog; "
            "no arbitrary file, real patient data, EHR or clinical conformance."
        ),
    )
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--ephemeral-demo", action="store_true")
    if argv in (["-h"], ["--help"]):
        print(parser.format_help())
        return 0
    # Exact flag admission: never echo unknown source filenames, tokens
    # or patient-like text through argparse's default errors.
    if len(argv) != 2 or set(argv) != {"--synthetic-only", "--ephemeral-demo"}:
        print("catalog demo refused: explicit_synthetic_demo_flags_required", file=sys.stderr)
        return 2
    try:
        from medscale.fhirkit.workspace_catalog_demo import receipt_json

        result = receipt_json()
    except ImportError:
        print("catalog demo unavailable: optional_workspace_runtime_missing", file=sys.stderr)
        return 2
    except Exception:
        print("catalog demo refused: encrypted_synthetic_catalog_blocked", file=sys.stderr)
        return 2
    print(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    if tokens and tokens[0] == "timeline-demo":
        return _timeline_demo_main(tokens[1:])
    if tokens and tokens[0] == "bundle-assess":
        return _bundle_structural_assessment_main(tokens[1:])
    if tokens and tokens[0] == "encrypted-structural-demo":
        return _encrypted_structural_demo_main(tokens[1:])
    if tokens and tokens[0] == "structural-outcome":
        return _r4_structural_outcome_main(tokens[1:])
    if tokens and tokens[0] == "workspace-catalog-demo":
        return _workspace_catalog_demo_main(tokens[1:])
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
