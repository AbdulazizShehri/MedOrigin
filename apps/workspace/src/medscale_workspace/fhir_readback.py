"""Synthetic-only, bounded, in-memory readback of one encrypted FHIR Bundle.

The Workspace owns the cryptographic storage/provenance/audit validation. No
patient-like payload is written to disk, printed, networked, or exposed through
a CLI. A snapshot gives a coherent encrypted-store read. This is NOT FHIR R4
validation, PHI admission, or a production authorization interface.
"""

from __future__ import annotations

import hashlib
import json
import re

from medscale_workspace import fhir_r4 as fhir
from medscale_workspace.audit import (
    AuditEventType,
    verified_chain_from_objects,
)
from medscale_workspace.binding import ObjectBinding
from medscale_workspace.identity import WorkspaceObjectType, synthetic_identity
from medscale_workspace.keyprovider import InMemoryTestKeyProvider
from medscale_workspace.provenance import (
    ProducerKind,
    ReviewState,
    SourceKind,
    _record_from_document,
    content_digest_of,
    provenance_binding_for,
)
from medscale_workspace.storage import WorkspaceStore

_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_MAX_RESOURCES = 16
_MAX_MANIFEST_BYTES = 2 * 1024 * 1024
_MAX_SNAPSHOT_OBJECTS = 128
_MAX_SNAPSHOT_BYTES = 6 * 1024 * 1024


class SyntheticFhirReadbackError(ValueError):
    """Stable redacted failure token, never copied from source FHIR content."""


def read_synthetic_fhir_bundle_in_memory(
    *,
    store: object,
    test_key_provider: object,
    source_content_sha256: str,
    expected_audit_head_digest: str,
    actor_id: str,
    synthetic_only: bool = False,
    allow_in_memory_readback: bool = False,
) -> dict[str, object]:
    """Reconstruct one original fictional collection Bundle, in RAM only.

    The exact in-memory key-provider instance and the original import actor
    must be supplied. The caller supplies an audit-head anchor from outside
    the encrypted database so a truncated/replaced chain cannot self-attest.
    If ANY of the admitted resource versions, source payload, provenance,
    source-member references or audit refs disagrees, return nothing.
    """
    if synthetic_only is not True:
        raise SyntheticFhirReadbackError("synthetic_attestation_required")
    if allow_in_memory_readback is not True:
        raise SyntheticFhirReadbackError("explicit_in_memory_readback_authorization_required")
    if not isinstance(store, WorkspaceStore):
        raise SyntheticFhirReadbackError("workspace_store_required")
    if type(test_key_provider) is not InMemoryTestKeyProvider:
        raise SyntheticFhirReadbackError("in_memory_test_key_provider_required")
    if store._key_provider is not test_key_provider:
        raise SyntheticFhirReadbackError("workspace_key_provider_mismatch")
    if (
        not isinstance(source_content_sha256, str)
        or _DIGEST_RE.fullmatch(source_content_sha256) is None
        or not isinstance(expected_audit_head_digest, str)
        or _DIGEST_RE.fullmatch(expected_audit_head_digest) is None
    ):
        raise SyntheticFhirReadbackError("source_or_audit_anchor_refused")
    try:
        actor = fhir._admit_identifier(actor_id, "actor id")
    except (TypeError, ValueError) as exc:
        raise SyntheticFhirReadbackError("actor_identity_refused") from exc

    # Store.export_snapshot verifies the integrity seal and reads one
    # transaction-consistent set of objects in memory. Never export a file.
    # The precheck protects a small demo from accidentally scanning a large
    # test workspace; the post-check bounds decrypted payloads.
    try:
        if (
            store.object_count() > _MAX_SNAPSHOT_OBJECTS
            or store.stored_envelope_bytes() > 8 * 1024 * 1024
        ):
            raise SyntheticFhirReadbackError("readback_store_too_large")
        snapshot = store.export_snapshot()
        if (
            len(snapshot.objects) > _MAX_SNAPSHOT_OBJECTS
            or sum(len(obj.payload) for obj in snapshot.objects) > _MAX_SNAPSHOT_BYTES
        ):
            raise SyntheticFhirReadbackError("readback_snapshot_exceeds_bounds")
        stored = {item.binding: item.payload for item in snapshot.objects}
        if len(stored) != len(snapshot.objects):
            raise SyntheticFhirReadbackError("readback_duplicate_object_binding")

        manifest_id = synthetic_identity(
            store.workspace_id,
            WorkspaceObjectType.FHIR_IMPORT_MANIFEST,
            source_content_sha256,
        )
        manifest_binding = ObjectBinding(
            workspace_id=store.workspace_id,
            object_id=manifest_id.object_id,
            object_type=WorkspaceObjectType.FHIR_IMPORT_MANIFEST,
            object_revision="1",
        )
        if manifest_binding not in stored:
            raise SyntheticFhirReadbackError("source_manifest_missing")
        original = stored[manifest_binding]
        if len(original) > _MAX_MANIFEST_BYTES:
            raise SyntheticFhirReadbackError("source_manifest_exceeds_bounds")
        if hashlib.sha256(original).hexdigest() != source_content_sha256:
            raise SyntheticFhirReadbackError("source_manifest_digest_mismatch")
        document = json.loads(original.decode("utf-8"))
        if (
            not isinstance(document, dict)
            or document.get("resourceType") != "Bundle"
            or document.get("type") != "collection"
            or json.dumps(
                document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
            != original
        ):
            raise SyntheticFhirReadbackError("source_manifest_not_canonical_collection")
        entries = document.get("entry")
        if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_RESOURCES:
            raise SyntheticFhirReadbackError("source_manifest_membership_refused")

        events = verified_chain_from_objects(
            tuple(
                (item.binding, item.payload)
                for item in snapshot.objects
                if item.binding.object_type is WorkspaceObjectType.AUDIT_EVENT
            )
        )
        if not events or events[-1].event_digest != expected_audit_head_digest:
            raise SyntheticFhirReadbackError("audit_head_anchor_mismatch")
        exact_metadata = (
            ("action", "synthetic_bundle_atomic_import"),
            ("bundle_sha256", source_content_sha256),
            ("resource_count", str(len(entries))),
        )
        matches = tuple(
            event
            for event in events
            if event.actor_id == actor
            and event.event_type is AuditEventType.OBJECT_CREATE
            and event.metadata == exact_metadata
        )
        if len(matches) != 1 or matches[0] is not events[-1]:
            raise SyntheticFhirReadbackError("source_import_event_not_current")
        import_event = matches[0]
        if len(import_event.object_refs) != len(entries):
            raise SyntheticFhirReadbackError("import_event_resource_count_mismatch")

        full_urls: dict[str, tuple[str, str]] = {}
        identities: set[tuple[str, str]] = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"fullUrl", "resource"}:
                raise SyntheticFhirReadbackError("source_manifest_entry_refused")
            url = entry["fullUrl"]
            resource = entry["resource"]
            if not isinstance(url, str) or not isinstance(resource, dict):
                raise SyntheticFhirReadbackError("source_manifest_entry_refused")
            kind = resource["resourceType"]
            fhir_id = resource["id"]
            if (
                url in full_urls
                or (kind, fhir_id) in identities
                or kind not in ("Patient", "Encounter", "Observation")
                or not isinstance(fhir_id, str)
            ):
                raise SyntheticFhirReadbackError("source_manifest_duplicate_or_unknown_resource")
            full_urls[url] = (kind, fhir_id)
            identities.add((kind, fhir_id))

        expected_bindings: set[ObjectBinding] = set()
        for entry, audit_ref in zip(entries, import_event.object_refs, strict=True):
            raw_resource = entry["resource"]
            converted = dict(raw_resource)
            for field in ("subject", "encounter"):
                if field in converted:
                    raw_reference = converted[field]["reference"]
                    kind, fhir_id = full_urls[raw_reference]
                    converted[field] = {"reference": kind + "/" + fhir_id}

            kind = fhir.FhirResourceType(converted["resourceType"])
            version = fhir._resource_version(converted)
            resource_id = fhir.resource_id_for(store.workspace_id, kind, converted["id"], version)
            binding = fhir.resource_binding(store.workspace_id, resource_id)
            if binding in expected_bindings:
                raise SyntheticFhirReadbackError("source_manifest_duplicate_resource_binding")
            expected_bindings.add(binding)
            payload = stored[binding]
            if (
                audit_ref.object_id != resource_id
                or audit_ref.object_type is not WorkspaceObjectType.FHIR_RESOURCE
                or audit_ref.object_revision != binding.object_revision
                or audit_ref.content_digest != content_digest_of(payload)
            ):
                raise SyntheticFhirReadbackError("source_resource_audit_binding_mismatch")

            resource = fhir.FhirResource.from_document(json.loads(payload.decode("ascii")))
            if (
                resource.workspace_id != store.workspace_id
                or resource.resource_id != resource_id
                or resource.resource_type is not kind
                or resource.fhir_id != converted["id"]
                or resource.resource_version != version
                or fhir._canonical_bytes(resource.to_document()) != payload
            ):
                raise SyntheticFhirReadbackError("stored_resource_identity_refused")
            restored = {name: fhir._thaw_value(value) for name, value in resource.content}
            if restored != converted:
                raise SyntheticFhirReadbackError("stored_resource_no_longer_matches_manifest")

            provenance_binding = provenance_binding_for(binding)
            provenance_payload = stored[provenance_binding]
            provenance = _record_from_document(json.loads(provenance_payload.decode("ascii")))
            if (
                provenance.binding != binding
                or provenance.canonical_bytes() != provenance_payload
                or provenance.review_state is not ReviewState.IMPORTED
                or provenance.producer.kind is not ProducerKind.IMPORT
                or provenance.producer.identifier != actor
                or len(provenance.source_refs) != 1
                or provenance.source_refs[0].kind is not SourceKind.FHIR_RESOURCE
                or provenance.source_refs[0].source_id != str(resource_id)
                or provenance.source_refs[0].source_revision != version
                or provenance.source_refs[0].locator != kind.value + "/" + converted["id"]
            ):
                raise SyntheticFhirReadbackError("stored_source_provenance_refused")
            provenance.verify_payload(payload)
        # Disallow additional revisions for any resource belonging to this
        # returned Bundle; they would create ambiguity in a naive exporter.
        for binding in stored:
            if (
                binding.object_type is WorkspaceObjectType.FHIR_RESOURCE
                and any(binding.object_id == expected.object_id for expected in expected_bindings)
                and binding not in expected_bindings
            ):
                raise SyntheticFhirReadbackError("unapproved_resource_revision_present")
    except SyntheticFhirReadbackError:
        raise
    except Exception as exc:
        # Crypto, SQLite, JSON, provenance, FHIR, audit, and key errors must
        # not expose caller-supplied paths or patient-like fields.
        raise SyntheticFhirReadbackError("synthetic_readback_integrity_refused") from exc

    # A fresh, bounded JSON object in memory; there are deliberately no
    # destination or network arguments. Re-encoding is a true snapshot copy.
    return {
        "schema": "medorigin-synthetic-fhir-in-memory-readback/v1",
        "bundle": document,
        "source_content_sha256": source_content_sha256,
        "audit_head_digest": expected_audit_head_digest,
        "resource_count": len(entries),
        "filesystem_export_performed": False,
        "clinical_use_authorized": False,
        "full_fhir_r4_conformance_established": False,
        "release_authorized": False,
    }
