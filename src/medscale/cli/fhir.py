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


def _multi_timeline_demo_main(argv: list[str]) -> int:
    """Real encrypted fictional two-import chronology, never identity joining."""
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir multi-timeline-demo "
            "--synthetic-only --ephemeral-demo\n"
            "Multiple independently source-verified fictional imports, "
            "per-import activity timeline only. NO cross-import patient "
            "identity linkage, clinical authority, or patient source inputs."
        )
        return 0
    if argv != ["--synthetic-only", "--ephemeral-demo"]:
        print(
            "multi timeline demo refused: exact_synthetic_ephemeral_flags_required",
            file=sys.stderr,
        )
        return 2
    try:
        from medscale.fhirkit.workspace_multi_timeline_demo import receipt_json

        result = receipt_json()
    except Exception:
        print(
            "multi timeline demo refused: encrypted_fictional_multi_timeline_unavailable",
            file=sys.stderr,
        )
        return 2
    print(result)
    return 0


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


def _file_batch_readiness_main(argv: list[str]) -> int:
    """Read-only local import preview; no encrypted store or patient output."""
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir file-batch-readiness --synthetic-only "
            "[--offline-r4-schema OFFICIAL_R4_ZIP] "
            "FICTIONAL_BUNDLE_1 FICTIONAL_BUNDLE_2 "
            "[FICTIONAL_BUNDLE_3 ... FICTIONAL_BUNDLE_4]\n"
            "Offline dry run for 2-4 invented local Bundles: reviewed source "
            "relationships, timeline/date readiness and optional source-pinned "
            "official R4 structure. Reports only per-source day/count summary. "
            "NO storage, PHI, full FHIR conformance, or clinical approval."
        )
        return 0
    refused = "file readiness refused: explicit_fictional_readonly_batch_required"
    if not 3 <= len(argv) <= 7 or argv[0] != "--synthetic-only":
        print(refused, file=sys.stderr)
        return 2
    cursor = 1
    schema: Path | None = None
    if len(argv) > 2 and argv[1] == "--offline-r4-schema":
        if (
            len(argv) < 5
            or not argv[2]
            or argv[2].startswith("--")
        ):
            print(refused, file=sys.stderr)
            return 2
        schema = Path(argv[2])
        cursor = 3
    names = argv[cursor:]
    if not 2 <= len(names) <= 4 or any(
        not name or name.startswith("--") for name in names
    ):
        print(refused, file=sys.stderr)
        return 2
    try:
        sources = [read_fhir_json_document(Path(name)) for name in names]
    except FhirInputError:
        print("file readiness refused: fictional_source_input_refused", file=sys.stderr)
        return 1
    try:
        from medscale.fhirkit.workspace_file_readiness import (
            fictional_file_batch_readiness_json,
        )

        receipt = fictional_file_batch_readiness_json(
            sources, synthetic_only=True, offline_r4_schema=schema
        )
    except Exception:
        print("file readiness refused: source_or_timeline_preflight_refused", file=sys.stderr)
        return 2
    print(receipt, end="")
    # A read-only preview, even with official R4 JSON Schema, is NOT
    # a successful FHIR/clinical conformance assertion.
    return 2


def _fictional_encrypted_file_batch_demo_main(argv: list[str]) -> int:
    """Actual caller-selected invented JSON -> encrypted ephemeral cold reopen.

    The explicit fictional-only flags and 2-4 local files are mandatory.
    Never echo user-supplied paths, parse errors or patient-like content.
    """
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir file-batch-encrypted-demo "
            "--synthetic-only --ephemeral-demo "
            "[--from-day YYYY-MM-DD] [--through-day YYYY-MM-DD] "
            "[--event-type Encounter|Observation] "
            "[--offline-r4-schema OFFICIAL_FHIR_R4_ZIP] "
            "FICTIONAL_BUNDLE_1 FICTIONAL_BUNDLE_2 "
            "[FICTIONAL_BUNDLE_3 ... FICTIONAL_BUNDLE_4]\\n"
            "Imports invented source files into a temporary AES-GCM Workspace, "
            "physically closes and reopens it, independently verifies audit, "
            "source catalog and per-import timelines, then deletes it. "
            "NO permanent import, PHI, FHIR R4/clinical validation or release."
        )
        return 0
    refused = "file batch demo refused: exact_fictional_ephemeral_file_flags_required"
    if len(argv) < 4 or argv[0:2] != ["--synthetic-only", "--ephemeral-demo"]:
        print(refused, file=sys.stderr)
        return 2
    # Admit optional bounded filters only BEFORE positional fictional files.
    # No argparse error can disclose caller-supplied filenames or values.
    filter_names = {
        "--from-day": "from_day_utc",
        "--through-day": "through_day_utc",
        "--event-type": "resource_type",
        "--offline-r4-schema": "offline_r4_schema",
    }
    filters: dict[str, str] = {}
    cursor = 2
    while cursor < len(argv) and argv[cursor] in filter_names:
        name = filter_names[argv[cursor]]
        if (
            name in filters
            or cursor + 1 >= len(argv)
            or not argv[cursor + 1]
            or argv[cursor + 1].startswith("--")
        ):
            print(refused, file=sys.stderr)
            return 2
        filters[name] = argv[cursor + 1]
        cursor += 2
    paths = argv[cursor:]
    if not 2 <= len(paths) <= 4 or any(not p or p.startswith("--") for p in paths):
        print(refused, file=sys.stderr)
        return 2
    try:
        from medscale.fhirkit.workspace_file_batch_demo import fictional_file_batch_receipt_json

        sources = [read_fhir_json_document(Path(name)) for name in paths]
    except FhirInputError:
        print("file batch demo refused: source_file_refused", file=sys.stderr)
        return 1
    except Exception:
        print("file batch demo refused: source_reader_unavailable", file=sys.stderr)
        return 2
    try:
        official_zip = filters.pop("offline_r4_schema", None)
        output = fictional_file_batch_receipt_json(
            sources,
            synthetic_only=True,
            ephemeral_demo=True,
            offline_r4_schema=Path(official_zip) if official_zip is not None else None,
            **filters,
        )
    except Exception:
        print(
            "file batch demo refused: verified_encrypted_fictional_batch_refused",
            file=sys.stderr,
        )
        return 2
    print(output, end="")
    # A proven ephemeral synthetic demo is not FHIR R4 or clinical validation.
    return 2


def _batch_bundle_local_diagnostics_main(argv: list[str]) -> int:
    """Developer-only triage of marked invented Bundle-local relationships.

    No schema validation, network or partial output from unmarked sources.
    Names and raw errors never appear in output. Exit 2 even when triage
    succeeds; a passing preflight is NOT successful clinical validation.
    """
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir batch-bundle-diagnose --synthetic-only "
            "FICTIONAL_BUNDLE_1 FICTIONAL_BUNDLE_2 "
            "[FICTIONAL_BUNDLE_3 ... FICTIONAL_BUNDLE_8]\n"
            "Separate redacted local-reference OperationOutcome for every "
            "synthetic-marker-qualified invented Bundle. No filenames or "
            "patient data. NOT HL7 R4 schema/profile/clinical validation."
        )
        return 0
    if (
        not 3 <= len(argv) <= 9
        or argv[0] != "--synthetic-only"
        or any(not name or name.startswith("--") for name in argv[1:])
    ):
        print(
            "batch diagnostics refused: explicit_fictional_batch_flags_required",
            file=sys.stderr,
        )
        return 2
    try:
        from medscale.fhirkit.bundle_batch_diagnostics import (
            synthetic_bundle_batch_triage_json,
        )

        payloads = [read_fhir_json_document(Path(name)) for name in argv[1:]]
    except FhirInputError:
        print("batch diagnostics refused: source_input_refused", file=sys.stderr)
        return 1
    except Exception:
        print("batch diagnostics refused: source_reader_unavailable", file=sys.stderr)
        return 2
    try:
        result = synthetic_bundle_batch_triage_json(payloads, synthetic_only=True)
    except Exception:
        print("batch diagnostics refused: source_qualification_refused", file=sys.stderr)
        return 2
    print(result, end="")
    return 2


def _batch_bundle_structural_assessment_main(argv: list[str]) -> int:
    """Bounded multi-document synthetic relationship + offline R4 structural check.

    Exact argument order, no caller-provided filename/path echoes, no partial
    output on any source/read/validator error. No clinical validation success.
    """
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir batch-bundle-assess "
            "--synthetic-only --offline-r4-schema OFFICIAL_R4_ZIP "
            "FICTIONAL_BUNDLE_1 FICTIONAL_BUNDLE_2 "
            "[FICTIONAL_BUNDLE_3 ... FICTIONAL_BUNDLE_8]\n"
            "Each invented Bundle independently receives local relationship "
            "preflight and source-pinned R4 JSON Schema structural assessment. "
            "No patient identity joins, filenames in output, network, "
            "full FHIR R4 clinical conformance or successful validation exit."
        )
        return 0
    if (
        not 5 <= len(argv) <= 11
        or argv[0:2] != ["--synthetic-only", "--offline-r4-schema"]
        or not argv[2]
        or any(not item or item.startswith("--") for item in argv[2:])
    ):
        print(
            "batch assessment refused: explicit_synthetic_offline_batch_flags_required",
            file=sys.stderr,
        )
        return 2
    try:
        from medscale.fhirkit.bundle_batch_assessment import (
            synthetic_bundle_batch_assessment_json,
        )
        from medscale.fhirkit.input import read_fhir_json_document

        # Validate all documents before any result, and never retain raw data
        # across process exit. Per-file diagnostics deliberately lack paths.
        sources = [read_fhir_json_document(Path(name)) for name in argv[3:]]
    except FhirInputError:
        print("batch assessment refused: source_input_refused", file=sys.stderr)
        return 1
    except Exception:
        print("batch assessment refused: bounded_batch_source_unavailable", file=sys.stderr)
        return 2
    try:
        output = synthetic_bundle_batch_assessment_json(
            sources,
            Path(argv[2]),
            synthetic_only=True,
        )
    except (UnavailableValidatorError, FhirMissingDependencyError):
        print("batch assessment unavailable: qualified_offline_schema_missing", file=sys.stderr)
        return 2
    except Exception:
        print("batch assessment refused: verified_batch_contract_refused", file=sys.stderr)
        return 2
    print(output, end="")
    # Not a validation-conformance or clinical-readiness success.
    return 2


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


def _filtered_multi_timeline_demo_main(argv: list[str]) -> int:
    """Real encrypted fictional filtered chronology, source verified before view."""
    if argv in (["--help"], ["-h"]):
        print(
            "usage: medscale fhir filtered-multi-timeline-demo "
            "--synthetic-only --ephemeral-demo "
            "[--from-day YYYY-MM-DD] [--through-day YYYY-MM-DD] "
            "[--event-type Encounter|Observation]\n"
            "Source-verified per-import fictional event search only; never "
            "patient identity joining, FHIR R4 validation or clinical authorization."
        )
        return 0
    if (
        len(argv) not in (4, 6, 8)
        or argv[:2] != ["--synthetic-only", "--ephemeral-demo"]
        or (len(argv) - 2) % 2 != 0
    ):
        print("filtered timeline refused: explicit_fictional_flags_required", file=sys.stderr)
        return 2
    accepted = {"--from-day", "--through-day", "--event-type"}
    opts: dict[str, str] = {}
    for i in range(2, len(argv), 2):
        flag, value = argv[i : i + 2]
        if flag not in accepted or flag in opts:
            print("filtered timeline refused: unsupported_filter", file=sys.stderr)
            return 2
        opts[flag] = value
    try:
        from medscale.fhirkit.workspace_multi_timeline import _checked_day

        start = _checked_day(opts.get("--from-day"))
        end = _checked_day(opts.get("--through-day"))
        if start is not None and end is not None and start > end:
            raise ValueError("invalid_day_range")
        kind = opts.get("--event-type")
        if kind is not None and kind not in ("Encounter", "Observation"):
            raise ValueError("unknown_event_type")
        from medscale.fhirkit.workspace_multi_timeline_demo import receipt_json

        result = receipt_json(
            from_day_utc=start,
            through_day_utc=end,
            resource_type=kind,
        )
    except Exception:
        # Do not forward caller text, raw bundled data or any absolute paths.
        print("filtered timeline refused: source_verified_view_unavailable", file=sys.stderr)
        return 2
    print(result)
    return 0


def _windows_protected_audit_preview_main(argv: list[str]) -> int:
    """Real owner Windows protected-key synthetic audit-only lifecycle CLI.

    No user JSON/document inputs. Strict positional flags, fixed diagnostic
    strings; neither absolute paths, UUID values nor OS exceptions are echoed.
    """
    if argv in (["-h"], ["--help"]):
        print(
            "usage: medscale fhir windows-audit-preview "
            "create|verify|forget --synthetic-only --developer-preview "
            "--store-root EXISTING_MEDORIGIN_FICTIONAL_WORKSPACE_PREVIEW_DIRECTORY "
            "--workspace-id UUIDV4 "
            "[--expected-head LOWERCASE_SHA256] "
            "[--acknowledge-irreversible-key-loss]\\n"
            "Windows Credential Manager-backed encrypted audit-only "
            "fictional developer preview. create prints an independent "
            "audit head; verify and forget REQUIRE that head. "
            "forget irrevocably deletes the preview key but preserves "
            "the now-unreadable encrypted store. No patient records, "
            "FHIR import, clinical permission or production key custody."
        )
        return 0
    refusal = "windows audit preview refused: exact_fictional_protected_flags_required"
    if (
        len(argv) < 7
        or argv[0] not in ("create", "verify", "forget")
        or argv[1:5]
        != [
            "--synthetic-only",
            "--developer-preview",
            "--store-root",
            argv[4],
        ]
        or argv[5] != "--workspace-id"
    ):
        print(refusal, file=sys.stderr)
        return 2
    action = argv[0]
    wanted = {"create": 7, "verify": 9, "forget": 10}[action]
    if len(argv) != wanted or not argv[4] or not argv[6]:
        print(refusal, file=sys.stderr)
        return 2
    if action != "create" and (argv[7] != "--expected-head" or not argv[8]):
        print(refusal, file=sys.stderr)
        return 2
    if action == "forget" and argv[9] != "--acknowledge-irreversible-key-loss":
        print(refusal, file=sys.stderr)
        return 2
    try:
        from uuid import UUID

        from medscale.fhirkit.windows_protected_audit_preview import (
            run_windows_audit_preview,
        )

        wid = UUID(argv[6])
        if wid.version != 4 or str(wid) != argv[6]:
            raise ValueError("noncanonical UUIDv4")
        result = run_windows_audit_preview(
            action,
            Path(argv[4]),
            wid,
            argv[8] if action != "create" else None,
            synthetic_only=True,
            developer_preview=True,
            irreversible_delete_acknowledged=action == "forget",
        )
    except Exception:
        print(
            "windows audit preview refused: encrypted_fictional_protected_workspace_unavailable",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    if tokens and tokens[0] == "windows-audit-preview":
        return _windows_protected_audit_preview_main(tokens[1:])
    if tokens and tokens[0] == "filtered-multi-timeline-demo":
        return _filtered_multi_timeline_demo_main(tokens[1:])
    if tokens and tokens[0] == "multi-timeline-demo":
        return _multi_timeline_demo_main(tokens[1:])
    if tokens and tokens[0] == "timeline-demo":
        return _timeline_demo_main(tokens[1:])
    if tokens and tokens[0] == "file-batch-readiness":
        return _file_batch_readiness_main(tokens[1:])
    if tokens and tokens[0] == "file-batch-encrypted-demo":
        return _fictional_encrypted_file_batch_demo_main(tokens[1:])
    if tokens and tokens[0] == "batch-bundle-diagnose":
        return _batch_bundle_local_diagnostics_main(tokens[1:])
    if tokens and tokens[0] == "batch-bundle-assess":
        return _batch_bundle_structural_assessment_main(tokens[1:])
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
