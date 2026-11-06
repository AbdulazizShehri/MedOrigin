"""A bounded, atomic, synthetic-only FHIR batch boundary for Clinical Workspace.

Public narrow developer/test adapter for Core. Production key custody is not
implemented. This module owns Workspace internals, so Core does not import
private fhir_r4 functions, audit constructors, or store provider attributes.
"""

from __future__ import annotations

import hashlib
import json

from medscale_workspace import fhir_r4 as fhir_mod
from medscale_workspace.audit import (
    AuditEventType,
    AuditObjectRef,
    AuditTrail,
    prepare_next_event,
)
from medscale_workspace.binding import ObjectBinding
from medscale_workspace.identity import WorkspaceObjectType, synthetic_identity
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

_MAXIMUM_BATCH_ENTRIES = 16


def _is_lower_sha256(value: object) -> bool:
    """Match exactly 64 ASCII lowercase hexadecimal characters, without regex imports."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all("0" <= char <= "9" or "a" <= char <= "f" for char in value)
    )


class SyntheticFhirBatchError(ValueError):
    """Public fail-closed, redacted contract error with a fixed reason token."""


def commit_synthetic_fhir_batch_atomic(
    *,
    store: object,
    test_key_provider: object,
    resources: tuple[dict[str, object], ...],
    source_content_sha256: str,
    actor_id: str,
    occurred_at: str,
    synthetic_only: bool = False,
    source_bundle: dict[str, object] | None = None,
) -> dict[str, object]:
    """Commit the complete synthetic test batch with provenance and audit.

    Input resources have already been preflighted by Core; this Workspace
    boundary independently admits every object and verifies all references
    point at members of THIS batch (not arbitrary previous store contents).
    A single encrypted SQLite transaction commits 2*N+1 objects or none.

    Explicitly requires exactly InMemoryTestKeyProvider, the SAME instance
    previously used to open the store. Production key providers fail closed.
    Neither raw content, original IDs, paths nor key material are returned.
    """
    if synthetic_only is not True:
        raise SyntheticFhirBatchError("explicit_synthetic_attestation_required")
    if not isinstance(store, WorkspaceStore):
        raise SyntheticFhirBatchError("workspace_store_required")
    if type(test_key_provider) is not InMemoryTestKeyProvider:
        raise SyntheticFhirBatchError("in_memory_test_key_provider_required")
    if store._key_provider is not test_key_provider:
        raise SyntheticFhirBatchError("workspace_test_key_provider_mismatch")
    if not isinstance(resources, tuple) or not 1 <= len(resources) <= _MAXIMUM_BATCH_ENTRIES:
        raise SyntheticFhirBatchError("atomic_test_batch_out_of_range")
    if not isinstance(source_content_sha256, str) or not _is_lower_sha256(source_content_sha256):
        raise SyntheticFhirBatchError("invalid_synthetic_source_digest")

    try:
        actor = fhir_mod._admit_identifier(actor_id, "actor id")
        moment = fhir_mod._admit_occurred_at(occurred_at)
    except (ValueError, TypeError) as exc:
        raise SyntheticFhirBatchError("import_audit_identity_refused") from exc

    manifest_write: ObjectWrite | None = None
    if source_bundle is not None:
        try:
            if not isinstance(source_bundle, dict):
                raise ValueError("not a bundle")
            if (
                source_bundle.get("resourceType") != "Bundle"
                or source_bundle.get("type") != "collection"
            ):
                raise ValueError("not a collection")
            entries = source_bundle.get("entry")
            if not isinstance(entries, list) or len(entries) != len(resources):
                raise ValueError("manifest membership mismatch")
            original_ids = [
                (entry["resource"]["resourceType"], entry["resource"]["id"]) for entry in entries
            ]
            imported_ids = [(resource["resourceType"], resource["id"]) for resource in resources]
            if len(set(original_ids)) != len(original_ids) or set(original_ids) != set(
                imported_ids
            ):
                raise ValueError("manifest resource identity mismatch")
            original = json.dumps(
                source_bundle,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            if len(original) > 2 * 1024 * 1024:
                raise ValueError("oversized bundle")
            if hashlib.sha256(original).hexdigest() != source_content_sha256:
                raise ValueError("digest mismatch")
            identity = synthetic_identity(
                store.workspace_id,
                WorkspaceObjectType.FHIR_IMPORT_MANIFEST,
                source_content_sha256,
            )
            manifest_write = ObjectWrite(
                binding=ObjectBinding(
                    workspace_id=store.workspace_id,
                    object_id=identity.object_id,
                    object_type=WorkspaceObjectType.FHIR_IMPORT_MANIFEST,
                    object_revision="1",
                ),
                payload=original,
            )
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            UnicodeError,
            RecursionError,
            OverflowError,
        ) as exc:
            raise SyntheticFhirBatchError("synthetic_source_manifest_refused") from exc

    writes: list[ObjectWrite] = []
    audit_refs: list[AuditObjectRef] = []
    identities: set[tuple[fhir_mod.FhirResourceType, str]] = set()
    parsed_resources: list[fhir_mod.FhirResource] = []
    try:
        for input_resource in resources:
            # The Core wrapper snapshots the Bundle, and this separate
            # boundary defensively freezes each record against direct callers.
            if not isinstance(input_resource, dict):
                raise SyntheticFhirBatchError("workspace_atomic_prepare_refused")
            payload = json.loads(
                json.dumps(
                    input_resource,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                )
            )
            kind = fhir_mod.FhirResourceType(payload["resourceType"])
            fhir_id = payload["id"]
            report = fhir_mod.validate_payload(
                kind,
                fhir_id,
                json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False),
            )
            if not all(report.stage(stage).passed for stage in ("parse", "structure", "profile")):
                raise SyntheticFhirBatchError("workspace_atomic_prepare_refused")
            key = (kind, fhir_id)
            if key in identities:
                raise SyntheticFhirBatchError("duplicate_workspace_batch_resource_identity")
            identities.add(key)

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
            parsed_resources.append(resource)

        # Complete membership check before generating any encrypted writes.
        # A dangling reference may NEVER be satisfied by an unrelated object
        # already in the store; imported batches are self-contained.
        for resource in parsed_resources:
            for ref in resource.references:
                if (ref.resource_type, ref.resource_id) not in identities:
                    raise SyntheticFhirBatchError("batch_reference_target_missing")
            if (
                resource.patient_id is not None
                and (
                    fhir_mod.FhirResourceType.PATIENT,
                    resource.patient_id,
                )
                not in identities
            ):
                raise SyntheticFhirBatchError("batch_patient_target_missing")

        for resource in parsed_resources:
            binding = fhir_mod.resource_binding(store.workspace_id, resource.resource_id)
            payload_bytes = fhir_mod._canonical_bytes(resource.to_document())
            provenance = describe_revision(
                binding=binding,
                payload=payload_bytes,
                producer=ProducerIdentity(
                    kind=ProducerKind.IMPORT,
                    identifier=actor,
                    version=fhir_mod.PRODUCER_VERSION,
                ),
                source_refs=(
                    SourceRef(
                        kind=SourceKind.FHIR_RESOURCE,
                        source_id=str(resource.resource_id),
                        source_revision=resource.resource_version,
                        locator=resource.resource_type.value + "/" + resource.fhir_id,
                    ),
                ),
                review_state=ReviewState.IMPORTED,
            )
            writes.extend(
                (
                    ObjectWrite(binding=binding, payload=payload_bytes),
                    ObjectWrite(
                        binding=provenance_binding_for(binding),
                        payload=provenance.canonical_bytes(),
                    ),
                )
            )
            audit_refs.append(
                AuditObjectRef(
                    object_id=resource.resource_id,
                    object_type=binding.object_type,
                    object_revision=binding.object_revision,
                    content_digest=content_digest_of(payload_bytes),
                )
            )
        event = prepare_next_event(
            AuditTrail(store),
            event_type=AuditEventType.OBJECT_CREATE,
            actor_id=actor,
            occurred_at=moment,
            object_refs=tuple(audit_refs),
            metadata=(
                ("action", "synthetic_bundle_atomic_import"),
                ("bundle_sha256", source_content_sha256),
                ("resource_count", str(len(parsed_resources))),
            ),
        )
        writes.append(ObjectWrite(binding=event.binding(), payload=event.canonical_bytes()))
        if manifest_write is not None:
            writes.append(manifest_write)
    except SyntheticFhirBatchError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError) as exc:
        raise SyntheticFhirBatchError("workspace_atomic_prepare_refused") from exc

    try:
        store.put_objects_atomic(tuple(writes))
    except Exception as exc:
        # SQLite/storage errors may include sensitive host paths.
        raise SyntheticFhirBatchError("workspace_atomic_commit_refused") from exc

    return {
        "resource_count": len(parsed_resources),
        "provenance_records_written": len(parsed_resources),
        "audit_events_written": 1,
        "encrypted_import_manifests_written": int(manifest_write is not None),
        "audit_head_digest": event.event_digest,
    }
