"""Private synthetic-only Core -> encrypted Clinical Workspace integration.

Core owns FHIR Bundle ingestion preflight and UUID translation. Workspace
owns its storage, FHIR profile, key, provenance and audit internals behind
one narrow, independently validating public test-only function.
"""

from __future__ import annotations

# mypy: disable-error-code="import-not-found"
# The Workspace package under apps/workspace is deliberately outside strict mypy's
# file set while Issue #464 item 1 is open; it is imported at runtime. Declaring
# the missing import here keeps that deferral explicit.
import json
from typing import Any, cast

from medscale.fhirkit.bundle import inspect_synthetic_bundle
from medscale.fhirkit.input import MAX_FHIR_INPUT_BYTES


class SyntheticWorkspaceImportError(ValueError):
    """Fixed redacted reason code; never contains raw patient fields or paths."""


def _translate_resource(
    resource: dict[str, Any],
    full_url_types: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    """Convert two admitted local UUID reference fields to Workspace form.

    All other payload fields remain unchanged; the Workspace side rejects
    unsupported content rather than silently dropping it.
    """
    converted = dict(resource)
    for field in ("subject", "encounter"):
        if field not in converted:
            continue
        reference = converted[field]["reference"]
        kind, fhir_id = full_url_types[reference]
        converted[field] = {"reference": kind + "/" + fhir_id}
    return converted


def ingest_synthetic_bundle_atomic(
    bundle: dict[str, Any],
    store: object,
    *,
    test_key_provider: object,
    actor_id: str,
    occurred_at: str,
    synthetic_only: bool = False,
) -> dict[str, object]:
    """Preflight a fictional Bundle then atomically commit into a test store.

    Caller must explicitly supply the in-memory test key provider matching
    its existing store. Full HL7 conformance, PHI admission and production
    key custody are NOT asserted and cannot be enabled by this wrapper.
    """
    try:
        from medscale_workspace.fhir_batch import (
            SyntheticFhirBatchError,
            commit_synthetic_fhir_batch_atomic,
        )
    except ImportError as exc:
        raise SyntheticWorkspaceImportError("optional_workspace_runtime_missing") from exc

    if synthetic_only is not True:
        raise SyntheticWorkspaceImportError("explicit_synthetic_attestation_required")

    # Freeze a canonical JSON-only snapshot, excluding NaN/Infinity and
    # mutable data callers could change after preflight. Upper-bound size
    # before running any downstream evaluator or persistent operation.
    try:
        encoded = json.dumps(
            bundle,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if len(encoded) > MAX_FHIR_INPUT_BYTES:
            raise SyntheticWorkspaceImportError("synthetic_bundle_input_size_refused")
        admitted_bundle = json.loads(encoded)
    except SyntheticWorkspaceImportError:
        raise
    except (TypeError, ValueError, OverflowError, UnicodeError, RecursionError) as exc:
        raise SyntheticWorkspaceImportError("synthetic_bundle_json_snapshot_refused") from exc

    try:
        preflight = inspect_synthetic_bundle(admitted_bundle)
    except ValueError as exc:
        raise SyntheticWorkspaceImportError("synthetic_bundle_preflight_refused") from exc
    # inspect_synthetic_bundle always reports resource_count as len(resources).
    if cast(int, preflight["resource_count"]) > 16:
        raise SyntheticWorkspaceImportError("atomic_test_batch_exceeds_16_resources")

    full_url_types: dict[str, tuple[str, str]] = {
        entry["fullUrl"]: (
            entry["resource"]["resourceType"],
            entry["resource"]["id"],
        )
        for entry in admitted_bundle["entry"]
    }
    try:
        converted = tuple(
            _translate_resource(entry["resource"], full_url_types)
            for entry in admitted_bundle["entry"]
        )
    except (TypeError, KeyError, ValueError, AttributeError) as exc:
        raise SyntheticWorkspaceImportError("workspace_atomic_prepare_refused") from exc

    try:
        outcome = commit_synthetic_fhir_batch_atomic(
            store=store,
            test_key_provider=test_key_provider,
            resources=converted,
            source_content_sha256=str(preflight["source_content_sha256"]),
            actor_id=actor_id,
            occurred_at=occurred_at,
            synthetic_only=True,
            source_bundle=admitted_bundle,
        )
    except SyntheticFhirBatchError as exc:
        # Workspace errors only expose fixed reviewed tokens, not input.
        raise SyntheticWorkspaceImportError(str(exc)) from None

    return {
        "schema": "medorigin-synthetic-workspace-atomic-ingest/v1",
        "status": "synthetic_test_store_committed",
        "source_content_sha256": preflight["source_content_sha256"],
        "resource_count": outcome["resource_count"],
        "provenance_records_written": outcome["provenance_records_written"],
        "audit_events_written": outcome["audit_events_written"],
        "encrypted_import_manifests_written": outcome["encrypted_import_manifests_written"],
        "audit_head_digest": outcome["audit_head_digest"],
        "payload_included": False,
        "production_key_provider_used": False,
        "clinical_use_authorized": False,
        "full_fhir_r4_conformance_established": False,
        "release_authorized": False,
    }
