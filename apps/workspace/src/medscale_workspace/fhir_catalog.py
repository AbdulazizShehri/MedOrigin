"""Verified metadata-only index of fictional encrypted FHIR Bundle imports.

This is an explicit synthetic/test Workspace boundary. It never returns FHIR
payloads and never exposes them to a CLI/file/network. An external audit-head
anchor and the exact in-memory test key-provider are mandatory.
"""

from __future__ import annotations

import re

from medscale_workspace import fhir_r4 as fhir
from medscale_workspace.audit import AuditEventType, verified_chain_from_objects
from medscale_workspace.fhir_readback import read_synthetic_fhir_bundle_in_memory
from medscale_workspace.identity import WorkspaceObjectType
from medscale_workspace.keyprovider import InMemoryTestKeyProvider
from medscale_workspace.storage import WorkspaceStore

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_IMPORTS = 16
_MAX_OBJECTS = 128
_MAX_ENVELOPES = 8 * 1024 * 1024
_MAX_PLAINTEXT = 6 * 1024 * 1024


class SyntheticFhirCatalogError(ValueError):
    """A stable redacted test-only failure code."""


def list_verified_synthetic_fhir_imports(
    *,
    store: object,
    test_key_provider: object,
    actor_id: str,
    expected_current_audit_head_digest: str,
    synthetic_only: bool = False,
    allow_in_memory_listing: bool = False,
    max_imports: int = 16,
) -> dict[str, object]:
    """Index bounded original imports by source digest and import-event anchor.

    The source SHA and event digest are deterministic selectors, NOT patient
    names, authorizations or a guarantee of full FHIR R4 conformance. Every
    entry is actually read back and verified in memory through the existing
    trusted narrow test gate before its redacted metadata enters the result.
    Do not silently truncate on a too-small max_imports: refuse the listing.
    """
    if synthetic_only is not True:
        raise SyntheticFhirCatalogError("explicit_synthetic_attestation_required")
    if allow_in_memory_listing is not True:
        raise SyntheticFhirCatalogError("explicit_in_memory_listing_required")
    if not isinstance(store, WorkspaceStore):
        raise SyntheticFhirCatalogError("workspace_store_required")
    if type(test_key_provider) is not InMemoryTestKeyProvider:
        raise SyntheticFhirCatalogError("in_memory_test_key_provider_required")
    if store._key_provider is not test_key_provider:
        raise SyntheticFhirCatalogError("workspace_key_provider_mismatch")
    if (
        not isinstance(expected_current_audit_head_digest, str)
        or _SHA256.fullmatch(expected_current_audit_head_digest) is None
    ):
        raise SyntheticFhirCatalogError("current_audit_anchor_refused")
    if type(max_imports) is not int or not 1 <= max_imports <= _MAX_IMPORTS:
        raise SyntheticFhirCatalogError("catalog_limit_refused")
    try:
        actor = fhir._admit_identifier(actor_id, "actor id")
    except (ValueError, TypeError) as exc:
        raise SyntheticFhirCatalogError("catalog_actor_refused") from exc

    try:
        if store.object_count() > _MAX_OBJECTS or store.stored_envelope_bytes() > _MAX_ENVELOPES:
            raise SyntheticFhirCatalogError("catalog_store_exceeds_bounds")
        snapshot = store.export_snapshot()
        if (
            len(snapshot.objects) > _MAX_OBJECTS
            or sum(len(obj.payload) for obj in snapshot.objects) > _MAX_PLAINTEXT
        ):
            raise SyntheticFhirCatalogError("catalog_snapshot_exceeds_bounds")
        events = verified_chain_from_objects(
            tuple(
                (item.binding, item.payload)
                for item in snapshot.objects
                if item.binding.object_type is WorkspaceObjectType.AUDIT_EVENT
            )
        )
        if not events or events[-1].event_digest != expected_current_audit_head_digest:
            raise SyntheticFhirCatalogError("catalog_audit_head_anchor_mismatch")

        # A source event is recognized by its action marker. The complete
        # metadata shape must be exact, not permissively copied from untrusted
        # events or exposed as a patient-facing label.
        candidates: list[tuple[str, str, int, int]] = []
        for event in events:
            if ("action", "synthetic_bundle_atomic_import") not in event.metadata:
                continue
            if event.actor_id != actor:
                continue
            if (
                event.event_type is not AuditEventType.OBJECT_CREATE
                or len(event.metadata) != 3
                or event.metadata[0] != ("action", "synthetic_bundle_atomic_import")
                or event.metadata[1][0] != "bundle_sha256"
                or event.metadata[2][0] != "resource_count"
            ):
                raise SyntheticFhirCatalogError("catalog_import_event_metadata_refused")
            source_sha = event.metadata[1][1]
            raw_count = event.metadata[2][1]
            if (
                _SHA256.fullmatch(source_sha) is None
                or not raw_count.isascii()
                or not raw_count.isdecimal()
                or str(int(raw_count)) != raw_count
                or not 1 <= int(raw_count) <= 16
            ):
                raise SyntheticFhirCatalogError("catalog_import_event_metadata_refused")
            if len(candidates) >= max_imports:
                raise SyntheticFhirCatalogError("catalog_limit_exceeded_no_partial_result")
            candidates.append((source_sha, event.event_digest, int(raw_count), event.sequence))

        items: list[dict[str, object]] = []
        for source_sha, import_sha, count, sequence in candidates:
            # The existing readback checks the complete audit chain, source
            # manifest, all resources and their immutable provenance. Its
            # in-memory Bundle is intentionally discarded: metadata ONLY.
            verified = read_synthetic_fhir_bundle_in_memory(
                store=store,
                test_key_provider=test_key_provider,
                source_content_sha256=source_sha,
                expected_audit_head_digest=import_sha,
                expected_current_audit_head_digest=expected_current_audit_head_digest,
                actor_id=actor,
                synthetic_only=True,
                allow_in_memory_readback=True,
            )
            if (
                verified["resource_count"] != count
                or verified["source_content_sha256"] != source_sha
                or verified["audit_head_digest"] != import_sha
                or verified["current_audit_head_digest"] != expected_current_audit_head_digest
            ):
                raise SyntheticFhirCatalogError("catalog_verified_entry_mismatch")
            items.append(
                {
                    "source_content_sha256": source_sha,
                    "import_audit_event_digest": import_sha,
                    "audit_sequence": sequence,
                    "resource_count": count,
                }
            )
    except SyntheticFhirCatalogError:
        raise
    except Exception as exc:
        # Never echo raw FHIR content, host paths, OS/storage/key exceptions.
        raise SyntheticFhirCatalogError("catalog_integrity_refused") from exc

    return {
        "schema": "medorigin-workspace-synthetic-import-catalog/v1",
        "status": "verified_synthetic_import_catalog",
        "current_audit_head_digest": expected_current_audit_head_digest,
        "import_count": len(items),
        "imports": items,
        "payload_included": False,
        "filesystem_export_performed": False,
        "clinical_use_authorized": False,
        "full_fhir_r4_conformance_established": False,
        "release_authorized": False,
    }
