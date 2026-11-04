"""Experimental atomic synthetic Bundle ingestion into the separate encrypted Workspace.

This is an explicitly opt-in developer/test integration. The production platform
key provider is unavailable, and this module refuses any non-test provider.
The source Bundle is asserted synthetic, never demonstrated PHI-free by a tag.
No CLI, network, EHR, model or cloud entrypoint is registered here.
"""

from __future__ import annotations

import json
from typing import Any

from medscale.fhirkit.bundle import inspect_synthetic_bundle
from medscale.fhirkit.input import MAX_FHIR_INPUT_BYTES


class SyntheticWorkspaceImportError(ValueError):
    """Fail-closed rejection without echoing untrusted document fields."""


def _translate_resource(
    resource: dict[str, Any],
    full_url_types: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    """Convert two FHIR UUID reference fields to the Workspace's bounded form.

    Do not silently discard content. The Workspace validator must admit
    all other fields and their values exactly, or the entire batch fails.
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
    """Commit resources, provenance records, and one audit event atomically.

    Caller must explicitly supply the *same* in-memory test key provider
    used to open the already-existing WorkspaceStore. Not a production API.
    No disk/key provider is provisioned here and no partial resources are
    committed on any prepare/validation/constraint failure.
    """
    # This intentionally has an optional runtime dependency. A standard
    # MedOrigin Core installation does not pull in or select Workspace.
    try:
        from medscale_workspace import fhir_r4 as fhir_mod
        from medscale_workspace.audit import (
            AuditEventType,
            AuditObjectRef,
            AuditTrail,
            prepare_next_event,
        )
        from medscale_workspace.keyprovider import InMemoryTestKeyProvider
        from medscale_workspace.provenance import (
            ProducerIdentity,
            ProducerKind,
            ReviewState,
            SourceKind,
            SourceRef,
            content_digest_of,
            describe_revision,
            provenance_binding_for,
        )
        from medscale_workspace.storage import ObjectWrite, WorkspaceStore
    except ImportError as exc:
        raise SyntheticWorkspaceImportError("optional_workspace_runtime_missing") from exc

    if synthetic_only is not True:
        raise SyntheticWorkspaceImportError("explicit_synthetic_attestation_required")
    if not isinstance(store, WorkspaceStore):
        raise SyntheticWorkspaceImportError("workspace_store_required")
    if not isinstance(test_key_provider, InMemoryTestKeyProvider):
        raise SyntheticWorkspaceImportError("in_memory_test_key_provider_required")
    # The existing production resolver returns an unavailable provider.
    # Explicitly bind this test-only integration to the already-open store.
    if store._key_provider is not test_key_provider:
        raise SyntheticWorkspaceImportError("workspace_test_key_provider_mismatch")

    # Freeze an immutable JSON-only snapshot *before* validation. A caller
    # mutating the original Python dict between preflight and commit cannot
    # change which objects are admitted. Refuse non-JSON and NaN/Infinity.
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

    # The source-bound Core preflight executes *before* any Workspace write.
    try:
        preflight = inspect_synthetic_bundle(admitted_bundle)
    except ValueError as exc:
        raise SyntheticWorkspaceImportError("synthetic_bundle_preflight_refused") from exc
    if preflight["resource_count"] > 16:
        raise SyntheticWorkspaceImportError("atomic_test_batch_exceeds_16_resources")

    # Validate actor/time upfront with Workspace's own admitted contract.
    try:
        actor = fhir_mod._admit_identifier(actor_id, "actor id")
        moment = fhir_mod._admit_occurred_at(occurred_at)
    except ValueError as exc:
        raise SyntheticWorkspaceImportError("import_audit_identity_refused") from exc

    full_url_types: dict[str, tuple[str, str]] = {}
    for entry in admitted_bundle["entry"]:
        source = entry["resource"]
        full_url_types[entry["fullUrl"]] = (source["resourceType"], source["id"])

    # Everything that may fail validation is prepared in memory; never
    # write a Patient and later discover that its Observation is broken.
    writes: list[ObjectWrite] = []
    audit_refs: list[AuditObjectRef] = []
    identities: list[object] = []
    try:
        for entry in admitted_bundle["entry"]:
            payload = _translate_resource(entry["resource"], full_url_types)
            kind = fhir_mod.FhirResourceType(payload["resourceType"])
            fhir_id = payload["id"]
            payload_text = json.dumps(payload, ensure_ascii=True, sort_keys=True)
            report = fhir_mod.validate_payload(kind, fhir_id, payload_text)
            if not (
                report.stage("parse").passed
                and report.stage("structure").passed
                and report.stage("profile").passed
            ):
                raise SyntheticWorkspaceImportError("workspace_resource_subset_refused")

            version = fhir_mod._resource_version(payload)
            identity = fhir_mod.resource_id_for(store.workspace_id, kind, fhir_id, version)
            resource = fhir_mod.FhirResource(
                workspace_id=store.workspace_id,
                resource_id=identity,
                resource_type=kind,
                fhir_id=fhir_id,
                resource_version=version,
                content=fhir_mod._content_entries(payload),
                security_labels=fhir_mod._security_labels(payload),
                references=fhir_mod._resource_references(payload),
                patient_id=fhir_mod._patient_binding(kind, payload),
                source_id=None,
                source_revision=None,
                content_digest=None,
            ).validated()
            binding = fhir_mod.resource_binding(store.workspace_id, identity)
            raw = fhir_mod._canonical_bytes(resource.to_document())
            source_ref = SourceRef(
                kind=SourceKind.FHIR_RESOURCE,
                source_id=str(identity),
                source_revision=version,
                locator=kind.value + "/" + fhir_id,
            )
            provenance = describe_revision(
                binding=binding,
                payload=raw,
                producer=ProducerIdentity(
                    kind=ProducerKind.IMPORT,
                    identifier=actor,
                    version=fhir_mod.PRODUCER_VERSION,
                ),
                source_refs=(source_ref,),
                review_state=ReviewState.IMPORTED,
            )
            writes.extend(
                (
                    ObjectWrite(binding=binding, payload=raw),
                    ObjectWrite(
                        binding=provenance_binding_for(binding),
                        payload=provenance.canonical_bytes(),
                    ),
                )
            )
            audit_refs.append(
                AuditObjectRef(
                    object_id=identity,
                    object_type=binding.object_type,
                    object_revision=binding.object_revision,
                    content_digest=content_digest_of(raw),
                )
            )
            identities.append(identity)
        # No dangling local references in this batch; Core preflight already
        # resolved types and fullUrls before conversion.
        trail = AuditTrail(store)
        event = prepare_next_event(
            trail,
            event_type=AuditEventType.OBJECT_CREATE,
            actor_id=actor,
            occurred_at=moment,
            object_refs=tuple(audit_refs),
            metadata=(
                ("action", "synthetic_bundle_atomic_import"),
                ("bundle_sha256", str(preflight["source_content_sha256"])),
                ("resource_count", str(len(identities))),
            ),
        )
        writes.append(ObjectWrite(binding=event.binding(), payload=event.canonical_bytes()))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise SyntheticWorkspaceImportError("workspace_atomic_prepare_refused") from exc

    try:
        # Existing encrypted SQLite primitive either commits ALL resource
        # payloads, their provenance records and the audit event, or NONE.
        store.put_objects_atomic(tuple(writes))
    except Exception as exc:
        # Stable token only: OS/SQLite exceptions may include source paths.
        raise SyntheticWorkspaceImportError("workspace_atomic_commit_refused") from exc

    return {
        "schema": "medorigin-synthetic-workspace-atomic-ingest/v1",
        "status": "synthetic_test_store_committed",
        "source_content_sha256": preflight["source_content_sha256"],
        "resource_count": len(identities),
        "provenance_records_written": len(identities),
        "audit_events_written": 1,
        "audit_head_digest": event.event_digest,
        "payload_included": False,
        "production_key_provider_used": False,
        "clinical_use_authorized": False,
        "full_fhir_r4_conformance_established": False,
        "release_authorized": False,
    }
