"""Opt-in, synthetic-only in-memory FHIR Bundle readback from Workspace.

No CLI or automatic data export is provided. This wrapper re-preflights
the reconstructed original Bundle under Core's narrow synthetic contract,
and deliberately does not assert full HL7 FHIR R4 or clinical conformance.
"""

from __future__ import annotations

import json

from medscale.fhirkit.bundle import inspect_synthetic_bundle
from medscale.fhirkit.input import MAX_FHIR_INPUT_BYTES


class SyntheticWorkspaceReadbackError(ValueError):
    """Never relay untrusted source JSON or sensitive operating-system paths."""


def read_synthetic_bundle_in_memory(
    store: object,
    *,
    test_key_provider: object,
    source_content_sha256: str,
    expected_audit_head_digest: str,
    actor_id: str,
    synthetic_only: bool = False,
    allow_in_memory_readback: bool = False,
) -> dict[str, object]:
    """Return only a source-verified, fully linked fictional Bundle in RAM.

    Requires explicitly authorizing the in-memory read and passing the
    source hash and external audit-head anchor from the original import
    receipt. This developer/test API has no destination, network or upload.
    """
    if synthetic_only is not True:
        raise SyntheticWorkspaceReadbackError("explicit_synthetic_attestation_required")
    if allow_in_memory_readback is not True:
        raise SyntheticWorkspaceReadbackError("explicit_in_memory_readback_required")

    try:
        from medscale_workspace.fhir_readback import (
            SyntheticFhirReadbackError,
            read_synthetic_fhir_bundle_in_memory,
        )
    except ImportError as exc:
        raise SyntheticWorkspaceReadbackError("optional_workspace_runtime_missing") from exc
    try:
        result = read_synthetic_fhir_bundle_in_memory(
            store=store,
            test_key_provider=test_key_provider,
            source_content_sha256=source_content_sha256,
            expected_audit_head_digest=expected_audit_head_digest,
            actor_id=actor_id,
            synthetic_only=True,
            allow_in_memory_readback=True,
        )
    except SyntheticFhirReadbackError as exc:
        raise SyntheticWorkspaceReadbackError(str(exc)) from None

    try:
        source = result["bundle"]
        serialized = json.dumps(
            source,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if len(serialized) > MAX_FHIR_INPUT_BYTES:
            raise SyntheticWorkspaceReadbackError("source_readback_size_refused")
        reconstructed = json.loads(serialized)
        preflight = inspect_synthetic_bundle(reconstructed)
        if (
            preflight["source_content_sha256"] != source_content_sha256
            or preflight["resource_count"] != result["resource_count"]
            or result["audit_head_digest"] != expected_audit_head_digest
        ):
            raise SyntheticWorkspaceReadbackError("source_readback_preflight_mismatch")
    except SyntheticWorkspaceReadbackError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        raise SyntheticWorkspaceReadbackError("source_readback_preflight_refused") from exc

    return {
        "schema": "medorigin-core-synthetic-fhir-memory-readback/v1",
        "source_content_sha256": source_content_sha256,
        "audit_head_digest": expected_audit_head_digest,
        "resource_count": preflight["resource_count"],
        "bundle": reconstructed,
        "filesystem_export_performed": False,
        "clinical_use_authorized": False,
        "full_fhir_r4_conformance_established": False,
        "release_authorized": False,
    }
