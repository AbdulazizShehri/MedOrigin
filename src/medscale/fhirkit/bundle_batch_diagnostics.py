"""Actionable per-file local-relationship diagnostics for marked fictional Bundles.

No official R4 schema or clinical validation: this is an offline, bounded
preflight TRIAGE view for synthetic developer fixtures. Bad/missing fictional
markers block *all* output, not a per-file diagnostic.
"""

from __future__ import annotations

import json
import re
from typing import Any

from medscale.fhirkit.bundle import (
    BundlePreflightError,
    _synthetic_marker,
    inspect_synthetic_bundle,
)
from medscale.fhirkit.bundle_diagnostics import (
    _FIXED_LOCAL_FAILURES,
    _FIXED_WARNING,
    rejected_synthetic_bundle_operation_outcome,
)
from medscale.reproducibility import content_hash

_MAX_DOCUMENTS = 8
_MAX_TOTAL_ENTRIES = 256
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class SyntheticBatchDiagnosticsError(ValueError):
    """Fixed source-safe refusal, never an untrusted error or filename."""


def diagnose_synthetic_bundle_batch_local(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    synthetic_only: bool = False,
) -> dict[str, object]:
    """Collect actionable fixed OperationOutcomes without partial admission.

    A marked-but-invalid synthetic relationship gets a redacted per-source
    error, unlike the atomic dual R4 assessment which refuses all findings.
    A missing marker, ambiguous/duplicate source or unbounded input refuses
    the entire operation. No source identity SHA is emitted for rejected
    sources, even if marked. Results must never be confused with full R4.
    """
    if synthetic_only is not True:
        raise SyntheticBatchDiagnosticsError("batch_diagnostics_synthetic_only_required")
    if type(payloads) not in (list, tuple) or not 2 <= len(payloads) <= _MAX_DOCUMENTS:
        raise SyntheticBatchDiagnosticsError("batch_diagnostics_document_bounds_refused")
    if any(type(p) is not dict or not _synthetic_marker(p) for p in payloads):
        raise SyntheticBatchDiagnosticsError("batch_diagnostics_marker_refused")

    # The entire batch is admitted before computing any outward-facing result.
    seen: set[str] = set()
    total_input_entries = 0
    for p in payloads:
        entries = p.get("entry")
        if type(entries) is not list or len(entries) > 128:
            raise SyntheticBatchDiagnosticsError("batch_diagnostics_entry_bounds_refused")
        total_input_entries += len(entries)
        if total_input_entries > _MAX_TOTAL_ENTRIES:
            raise SyntheticBatchDiagnosticsError("batch_diagnostics_entry_bounds_refused")
        try:
            digest = content_hash(p)
        except (TypeError, ValueError, OverflowError) as exc:
            raise SyntheticBatchDiagnosticsError(
                "batch_diagnostics_unqualified_source_refused"
            ) from exc
        if type(digest) is not str or _SHA256.fullmatch(digest) is None or digest in seen:
            raise SyntheticBatchDiagnosticsError("batch_diagnostics_duplicate_source_refused")
        seen.add(digest)

    items: list[dict[str, object]] = []
    rejected = 0
    for ordinal, p in enumerate(payloads, 1):
        try:
            checked = inspect_synthetic_bundle(p)
        except BundlePreflightError as exc:
            if str(exc) not in _FIXED_LOCAL_FAILURES:
                raise SyntheticBatchDiagnosticsError(
                    "batch_diagnostics_unqualified_failure_refused"
                ) from exc
            outcome = rejected_synthetic_bundle_operation_outcome(p, exc)
            expected = [
                {
                    "severity": "error",
                    "code": "structure",
                    "details": {"text": _FIXED_LOCAL_FAILURES[str(exc)]},
                },
                {
                    "severity": "warning",
                    "code": "informational",
                    "details": {"text": _FIXED_WARNING},
                },
            ]
            if outcome != {"resourceType": "OperationOutcome", "issue": expected}:
                raise SyntheticBatchDiagnosticsError(
                    "batch_diagnostics_outcome_contract_refused"
                ) from exc
            rejected += 1
            items.append(
                {
                    "document_ordinal": ordinal,
                    "local_relationship_status": "rejected",
                    "r4_schema_check_run": False,
                    "operation_outcome": {
                        "resourceType": "OperationOutcome",
                        "issue": expected,
                    },
                }
            )
        else:
            counts = checked.get("resource_counts")
            total = checked.get("resource_count")
            refs = checked.get("local_references_checked")
            source_sha = checked.get("source_content_sha256")
            if (
                checked.get("schema") != "medorigin-synthetic-fhir-bundle-preflight/v1"
                or checked.get("status") != "local_relationship_preflight_only"
                or checked.get("data_class") != "SYNTHETIC_ASSERTED_NOT_VERIFIED"
                or type(total) is not int
                or not 1 <= total <= 128
                or type(refs) is not int
                or not 0 <= refs <= 3 * total
                or type(source_sha) is not str
                or _SHA256.fullmatch(source_sha) is None
                or source_sha != content_hash(p)
                or type(counts) is not dict
                or set(counts) != {"Encounter", "Observation", "Patient"}
                or any(type(x) is not int or x < 0 for x in counts.values())
                or sum(counts.values()) != total
                or any(
                    checked.get(flag) is not False
                    for flag in (
                        "payload_content_included",
                        "input_persisted",
                        "network_access_performed",
                        "full_fhir_r4_conformance_established",
                        "clinical_use_authorized",
                    )
                )
            ):
                raise SyntheticBatchDiagnosticsError("batch_diagnostics_accepted_contract_refused")
            items.append(
                {
                    "document_ordinal": ordinal,
                    "local_relationship_status": "preflight_only",
                    "source_content_sha256": source_sha,
                    "resource_count": total,
                    "resource_counts": {
                        "Encounter": counts["Encounter"],
                        "Observation": counts["Observation"],
                        "Patient": counts["Patient"],
                    },
                    "local_references_checked": refs,
                    "r4_schema_check_run": False,
                }
            )

    return {
        "schema": "medorigin-core-fictional-batch-local-triage/v1",
        "status": "LOCAL_FICTIONAL_BUNDLE_TRIAGE_ONLY",
        "document_count": len(items),
        "preflight_only_count": len(items) - rejected,
        "rejected_local_count": rejected,
        "documents": items,
        "source_filenames_included": False,
        "patient_identifiers_included": False,
        "resource_payload_included": False,
        "filesystem_export_performed": False,
        "network_access_performed": False,
        "cross_bundle_patient_identity_join_performed": False,
        "official_r4_json_schema_check_performed": False,
        "full_fhir_r4_conformance_established": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }


def synthetic_bundle_batch_triage_json(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    synthetic_only: bool = False,
) -> str:
    return (
        json.dumps(
            diagnose_synthetic_bundle_batch_local(payloads, synthetic_only=synthetic_only),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    )
