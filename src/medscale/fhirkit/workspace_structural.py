"""Core orchestration: official offline R4 *structural* Outcome to encrypted store.

The source must already exist in a synthetic encrypted import. The original
Bundle is reloaded from the source-pinned manifest, then the exact official
schema structurally checks THAT source. No arbitrary caller ValidationReport
can be passed to make a false 'valid' receipt. A source-bound, nonclinical
OperationOutcome is atomically committed with provenance and audit.
"""

from __future__ import annotations

from pathlib import Path

from medscale.fhirkit.r4_outcome import structural_outcome_for_report
from medscale.fhirkit.r4_schema import validate_offline_r4_json_structure


class SyntheticStructuralStoreError(ValueError):
    """A fixed redacted Core boundary refusal with no source content."""


def validate_and_store_imported_synthetic_bundle_structure(
    *,
    store: object,
    test_key_provider: object,
    source_content_sha256: str,
    import_audit_event_digest: str,
    expected_current_audit_head_digest: str,
    official_r4_schema_archive: Path,
    actor_id: str,
    occurred_at: str,
    synthetic_only: bool = False,
    allow_encrypted_receipt_write: bool = False,
) -> dict[str, object]:
    """Revalidate the ACTUAL encrypted original against official pinned R4.

    No pre-supplied report/outcome or caller-provided plaintext FHIR is
    accepted. The result is explicitly partial and never authorizes clinical
    use, patient records, or full FHIR R4 conformance.
    """
    if synthetic_only is not True:
        raise SyntheticStructuralStoreError("explicit_synthetic_attestation_required")
    if allow_encrypted_receipt_write is not True:
        raise SyntheticStructuralStoreError("explicit_encrypted_receipt_write_required")
    try:
        from medscale_workspace.fhir_readback import (
            read_synthetic_fhir_bundle_in_memory,
        )
        from medscale_workspace.fhir_structural_receipt import (
            commit_verified_synthetic_structural_outcome,
        )
    except ImportError as exc:
        raise SyntheticStructuralStoreError("optional_workspace_runtime_missing") from exc

    try:
        reconstructed = read_synthetic_fhir_bundle_in_memory(
            store=store,
            test_key_provider=test_key_provider,
            source_content_sha256=source_content_sha256,
            expected_audit_head_digest=import_audit_event_digest,
            expected_current_audit_head_digest=expected_current_audit_head_digest,
            actor_id=actor_id,
            synthetic_only=True,
            allow_in_memory_readback=True,
        )
    except Exception as exc:
        raise SyntheticStructuralStoreError("encrypted_source_import_verification_refused") from exc

    try:
        # The same exact SHA-pinned official JSON Schema and dependency
        # version gate used by the existing Core structural-outcome CLI.
        report = validate_offline_r4_json_structure(
            reconstructed["bundle"], official_r4_schema_archive
        )
        outcome = structural_outcome_for_report(report)
    except Exception as exc:
        raise SyntheticStructuralStoreError("official_r4_structural_check_unavailable") from exc

    try:
        receipt = commit_verified_synthetic_structural_outcome(
            store=store,
            test_key_provider=test_key_provider,
            source_content_sha256=source_content_sha256,
            import_audit_event_digest=import_audit_event_digest,
            expected_current_audit_head_digest=expected_current_audit_head_digest,
            outcome=outcome,
            structural_status=str(report.status),
            actor_id=actor_id,
            occurred_at=occurred_at,
            synthetic_only=True,
            allow_encrypted_receipt_write=True,
        )
    except Exception as exc:
        raise SyntheticStructuralStoreError("encrypted_structural_receipt_refused") from exc
    return {
        "schema": "medorigin-core-encrypted-r4-structural-check/v1",
        "status": "synthetic_structural_result_encrypted",
        "source_content_sha256": source_content_sha256,
        "import_audit_event_digest": import_audit_event_digest,
        "structural_status": report.status,
        "receipt_sha256": receipt["receipt_sha256"],
        "audit_head_digest": receipt["audit_head_digest"],
        "encrypted_objects_written": receipt["objects_written"],
        "outcome_payload_included": False,
        "fhir_conformance_validated": False,
        "clinical_use_authorized": False,
        "release_authorized": False,
    }


def read_imported_synthetic_structural_result(
    *,
    store: object,
    test_key_provider: object,
    source_content_sha256: str,
    import_audit_event_digest: str,
    expected_current_audit_head_digest: str,
    expected_receipt_sha256: str,
    actor_id: str,
    synthetic_only: bool = False,
    allow_in_memory_readback: bool = False,
) -> dict[str, object]:
    """Read back a real encrypted, immutable, source/audit-linked Outcome."""
    if synthetic_only is not True or allow_in_memory_readback is not True:
        raise SyntheticStructuralStoreError("explicit_synthetic_receipt_read_required")
    try:
        from medscale_workspace.fhir_structural_receipt import (
            read_verified_synthetic_structural_outcome,
        )
    except ImportError as exc:
        raise SyntheticStructuralStoreError("optional_workspace_runtime_missing") from exc

    try:
        recovered = read_verified_synthetic_structural_outcome(
            store=store,
            test_key_provider=test_key_provider,
            source_content_sha256=source_content_sha256,
            import_audit_event_digest=import_audit_event_digest,
            expected_current_audit_head_digest=expected_current_audit_head_digest,
            expected_receipt_sha256=expected_receipt_sha256,
            actor_id=actor_id,
            synthetic_only=True,
            allow_in_memory_readback=True,
        )
    except Exception as exc:
        raise SyntheticStructuralStoreError("encrypted_structural_receipt_read_refused") from exc

    # Independently refuse a switched or expanded payload at Core boundary.
    from medscale.fhirkit.r4_outcome import (
        _ALLOWED_VALIDATOR_KEYWORDS,
        _WARNING,
    )

    result = recovered["outcome"]
    if (
        not isinstance(result, dict)
        or set(result) != {"resourceType", "issue"}
        or result["resourceType"] != "OperationOutcome"
        or not isinstance(result["issue"], list)
        or not 1 <= len(result["issue"]) <= 14
        or recovered.get("fhir_conformance_validated") is not False
        or recovered.get("clinical_use_authorized") is not False
        or recovered.get("release_authorized") is not False
    ):
        raise SyntheticStructuralStoreError("source_verified_outcome_contract_refused")
    for i, issue in enumerate(result["issue"]):
        if (
            not isinstance(issue, dict)
            or set(issue) != {"severity", "code", "details"}
            or not isinstance(issue["details"], dict)
            or set(issue["details"]) != {"text"}
        ):
            raise SyntheticStructuralStoreError("source_verified_outcome_issue_refused")
        message = issue["details"]["text"]
        if not isinstance(message, str):
            raise SyntheticStructuralStoreError("source_verified_outcome_text_refused")
        if i == len(result["issue"]) - 1:
            if (
                issue["severity"] != "warning"
                or issue["code"] != "informational"
                or message != _WARNING
            ):
                raise SyntheticStructuralStoreError("source_verified_outcome_warning_refused")
        elif (
            issue["severity"] != "error"
            or issue["code"] != "structure"
            or not (
                (
                    message.startswith("FHIR R4 JSON Schema structural keyword:")
                    and message.split(":", 1)[-1].strip() in _ALLOWED_VALIDATOR_KEYWORDS
                )
                or (
                    message == "Further structural errors were omitted after the fixed limit."
                    and i == 12
                    and len(result["issue"]) == 14
                )
            )
        ):
            raise SyntheticStructuralStoreError("source_verified_outcome_diagnostic_refused")
    if (recovered["structural_status"] == "invalid") != (len(result["issue"]) > 1):
        raise SyntheticStructuralStoreError("source_verified_outcome_status_refused")
    return {
        "schema": "medorigin-core-encrypted-r4-structural-readback/v1",
        "source_content_sha256": recovered["source_content_sha256"],
        "structural_status": recovered["structural_status"],
        "outcome": result,
        "receipt_sha256": recovered["receipt_sha256"],
        "audit_head_digest": recovered["audit_head_digest"],
        "fhir_conformance_validated": False,
        "clinical_use_authorized": False,
        "release_authorized": False,
    }
