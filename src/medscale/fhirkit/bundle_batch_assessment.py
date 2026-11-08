"""Read-only, bounded, redacted local multi-Bundle FHIR synthetic assessment.

Each source receives the existing narrow synthetic relationship check plus
the exact offline HL7 R4 JSON Schema structural check. Neither passing check
establishes full FHIR R4/clinical conformance or the absence of PHI.
No output or partial results on an unqualified source.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from medscale.fhirkit.bundle_assessment import assess_synthetic_bundle_offline
from medscale.fhirkit.r4_outcome import (
    _ALLOWED_VALIDATOR_KEYWORDS,
    _WARNING,
)
from medscale.fhirkit.r4_schema import OFFICIAL_R4_SCHEMA_ZIP_SHA256

MAX_BATCH_DOCUMENTS = 8
MAX_BATCH_RESOURCES = 256
_SOURCE_SHA = re.compile(r"[0-9a-f]{64}\Z")


class SyntheticBatchAssessmentError(ValueError):
    """Fixed source-safe refusal; no source payloads, filenames or paths."""


def assess_synthetic_bundle_batch_offline(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    official_r4_schema_archive: Path,
    *,
    synthetic_only: bool = False,
) -> dict[str, object]:
    """Preflight all local fictional Bundles; return only redacted per-file results.

    Callers must not feed patient data. The synthetic tag is an assertion,
    not a sufficient mechanism for detecting PHI. Every item is independently
    source-verified, with no cross-Bundle reference or identity federation.
    """
    if synthetic_only is not True:
        raise SyntheticBatchAssessmentError("batch_synthetic_attestation_required")
    if type(payloads) not in (list, tuple) or not 2 <= len(payloads) <= MAX_BATCH_DOCUMENTS:
        raise SyntheticBatchAssessmentError("batch_document_count_refused")
    if any(type(item) is not dict for item in payloads):
        raise SyntheticBatchAssessmentError("batch_source_type_refused")

    outputs: list[dict[str, object]] = []
    hashes: set[str] = set()
    total_resources = 0
    invalid_count = 0
    for index, source in enumerate(payloads, 1):
        # The separately audited single-Bundle assessor MUST qualify each
        # source before any batch output is exposed.
        receipt = assess_synthetic_bundle_offline(
            source, official_r4_schema_archive, synthetic_only=True
        )
        digest = receipt.get("source_content_sha256")
        count = receipt.get("resource_count")
        counts = receipt.get("resource_counts")
        checked = receipt.get("local_references_checked")
        status = receipt.get("r4_structural_status")
        outcome = receipt.get("r4_operation_outcome")
        if (
            type(digest) is not str
            or _SOURCE_SHA.fullmatch(digest) is None
            or digest in hashes
            or receipt.get("schema") != "medorigin-synthetic-fhir-bundle-dual-assessment/v1"
            or receipt.get("status") != "SYNTHETIC_R4_BUNDLE_PRECHECK_ONLY"
            or receipt.get("relationship_status") != "local_relationship_preflight_only"
            or receipt.get("synthetic_marker_verified_as_assertion_only") is not True
            or receipt.get("official_r4_archive_sha256") != OFFICIAL_R4_SCHEMA_ZIP_SHA256
            or type(count) is not int
            or not 1 <= count <= 128
            or type(checked) is not int
            or not 0 <= checked <= count * 3
            or type(counts) is not dict
            or set(counts) != {"Patient", "Encounter", "Observation"}
            or any(type(v) is not int or v < 0 for v in counts.values())
            or sum(counts.values()) != count
            or status not in ("invalid", "not_validated")
            or type(outcome) is not dict
            or set(outcome) != {"resourceType", "issue"}
            or outcome["resourceType"] != "OperationOutcome"
            or type(outcome["issue"]) is not list
            or not 1 <= len(outcome["issue"]) <= 14
            or any(
                receipt.get(field) is not False
                for field in (
                    "payload_included",
                    "output_persisted",
                    "network_access_performed",
                    "fhir_r4_conformance_validated",
                    "terminology_profiles_invariants_verified",
                    "clinical_use_authorized",
                    "publication_authorized",
                )
            )
        ):
            raise SyntheticBatchAssessmentError("batch_assessment_contract_refused")
        # Never relay arbitrary downstream fields, paths, patient identities
        # or content; only schema-checked fixed outcome issues are admitted.
        for issue_index, issue in enumerate(outcome["issue"]):
            if (
                type(issue) is not dict
                or set(issue) != {"severity", "code", "details"}
                or type(issue["details"]) is not dict
                or set(issue["details"]) != {"text"}
                or type(issue["details"]["text"]) is not str
            ):
                raise SyntheticBatchAssessmentError("batch_outcome_contract_refused")
            issue_text = issue["details"]["text"]
            if issue_index == len(outcome["issue"]) - 1:
                if (
                    issue["severity"] != "warning"
                    or issue["code"] != "informational"
                    or issue_text != _WARNING
                ):
                    raise SyntheticBatchAssessmentError("batch_outcome_contract_refused")
            else:
                prefix = "FHIR R4 JSON Schema structural keyword: "
                if (
                    issue["severity"] != "error"
                    or issue["code"] != "structure"
                    or not (
                        issue_text
                        == "Further structural errors were omitted after the fixed limit."
                        or (
                            issue_text.startswith(prefix)
                            and issue_text[len(prefix) :] in _ALLOWED_VALIDATOR_KEYWORDS
                        )
                    )
                ):
                    raise SyntheticBatchAssessmentError("batch_outcome_contract_refused")
        if (status == "invalid") != any(
            issue["severity"] == "error" for issue in outcome["issue"]
        ) or outcome["issue"][-1]["severity"] != "warning":
            raise SyntheticBatchAssessmentError("batch_outcome_contract_refused")
        hashes.add(digest)
        total_resources += count
        invalid_count += status == "invalid"
        if total_resources > MAX_BATCH_RESOURCES:
            raise SyntheticBatchAssessmentError("batch_total_resource_limit_refused")
        outputs.append(
            {
                "document_ordinal": index,
                "source_content_sha256": digest,
                "resource_count": count,
                "resource_counts": {
                    "Encounter": counts["Encounter"],
                    "Observation": counts["Observation"],
                    "Patient": counts["Patient"],
                },
                "local_references_checked": checked,
                "relationship_status": "local_relationship_preflight_only",
                "r4_structural_status": status,
                "r4_operation_outcome": {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": issue["severity"],
                            "code": issue["code"],
                            "details": {"text": issue["details"]["text"]},
                        }
                        for issue in outcome["issue"]
                    ],
                },
            }
        )
    return {
        "schema": "medorigin-core-synthetic-fhir-batch-dual-assessment/v1",
        "status": "SYNTHETIC_BATCH_PARTIAL_R4_PRECHECK_ONLY",
        "document_count": len(outputs),
        "total_resource_count": total_resources,
        "structural_not_validated_count": len(outputs) - invalid_count,
        "structural_invalid_count": invalid_count,
        "documents": outputs,
        "official_r4_archive_sha256": OFFICIAL_R4_SCHEMA_ZIP_SHA256,
        "source_filenames_included": False,
        "resource_payload_included": False,
        "result_persisted": False,
        "network_access_performed": False,
        "cross_bundle_patient_join_performed": False,
        "fhir_r4_conformance_validated": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }


def synthetic_bundle_batch_assessment_json(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    official_r4_schema_archive: Path,
    *,
    synthetic_only: bool = False,
) -> str:
    return (
        json.dumps(
            assess_synthetic_bundle_batch_offline(
                payloads, official_r4_schema_archive, synthetic_only=synthetic_only
            ),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    )
