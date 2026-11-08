"""Synthetic-only Core encrypted FHIR readback => redacted D2 native worklist.

Run with EXACT pinned source or two independently attested installed Wheels,
outside the GUI under independent OS confinement. NO patient input/paths,
file export, network or production key. This source is QA-only, not an
approved supervisor or clinical worker.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

_SCHEMA = "medorigin-d2-encrypted-fhir-memory-readback-projection/v1"
_WORKSPACE_ID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
_TIME = "2026-11-04T04:00:00+03:00"
_EXPECTED_TYPES = ("Observation", "Patient", "Encounter")
_EXPECTED_IDS = (
    "fictional-observation-001",
    "fictional-patient-001",
    "fictional-encounter-001",
)
_EXPECTED_FULL_URLS = tuple(
    f"urn:uuid:00000000-0000-4000-8000-00000000000{idx}" for idx in (1, 2, 3)
)
_EXPECTED_LINKS = (
    (("subject", _EXPECTED_FULL_URLS[1]), ("encounter", _EXPECTED_FULL_URLS[2])),
    (),
    (("subject", _EXPECTED_FULL_URLS[1]),),
)


def exact_synthetic_encrypted_readback_projection() -> bytes:
    from medscale_workspace.audit import AuditTrail
    from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret
    from medscale_workspace.storage import WorkspaceStore

    from medscale.fhirkit.workspace_demo import _fictional_bundle
    from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic
    from medscale.fhirkit.workspace_readback import read_synthetic_bundle_in_memory

    fictional = _fictional_bundle()
    provider = InMemoryTestKeyProvider(new_root_secret())
    with TemporaryDirectory(prefix="medorigin-fictional-d2-readback-") as directory:
        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WORKSPACE_ID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as store:
            source_receipt = ingest_synthetic_bundle_atomic(
                fictional,
                store,
                test_key_provider=provider,
                actor_id="fictional-core-demo",
                occurred_at=_TIME,
                synthetic_only=True,
            )
            if store.object_count() != 8:
                raise ValueError("synthetic_core_encrypted_resource_store_count_refused")
            if (
                AuditTrail(store)
                .verify(expected_head_event_digest=source_receipt["audit_head_digest"])
                .events_verified
                != 1
            ):
                raise ValueError("synthetic_core_encrypted_audit_invalid")

        with WorkspaceStore.open(
            store_root=directory,
            workspace_id=_WORKSPACE_ID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as reopened:
            if (
                AuditTrail(reopened)
                .verify(expected_head_event_digest=source_receipt["audit_head_digest"])
                .events_verified
                != 1
            ):
                raise ValueError("synthetic_core_audit_anchor_refused")
            readback = read_synthetic_bundle_in_memory(
                reopened,
                test_key_provider=provider,
                source_content_sha256=source_receipt["source_content_sha256"],
                expected_audit_head_digest=source_receipt["audit_head_digest"],
                actor_id="fictional-core-demo",
                synthetic_only=True,
                allow_in_memory_readback=True,
            )
            if (
                readback["bundle"] != fictional
                or readback["resource_count"] != 3
                or readback["source_content_sha256"] != source_receipt["source_content_sha256"]
                or readback["clinical_use_authorized"] is not False
                or readback["release_authorized"] is not False
            ):
                raise ValueError("synthetic_core_memory_readback_refused")

            # EXTRACT FROM RECOVERED ENCRYPTED SOURCE, never the original fixture.
            entries = readback["bundle"]["entry"]
            if len(entries) != 3:
                raise ValueError("synthetic_core_memory_readback_count_refused")
            projection = []
            for index, entry in enumerate(entries):
                resource = entry["resource"]
                if (
                    resource["resourceType"] != _EXPECTED_TYPES[index]
                    or resource["id"] != _EXPECTED_IDS[index]
                    or entry["fullUrl"] != _EXPECTED_FULL_URLS[index]
                ):
                    raise ValueError("synthetic_core_memory_readback_identity_refused")
                links = tuple(
                    (field, resource[field]["reference"])
                    for field in ("subject", "encounter")
                    if field in resource
                )
                if links != _EXPECTED_LINKS[index]:
                    raise ValueError("synthetic_core_memory_readback_links_refused")
                # Avoid name, coded clinical data, value, and entire raw FHIR.
                projection.append(
                    {
                        "resource_type": resource["resourceType"],
                        "id": resource["id"],
                        "full_url": entry["fullUrl"],
                        "links": [{"field": field, "target": target} for field, target in links],
                    }
                )
            summary = {
                "schema": _SCHEMA,
                "status": "SYNTHETIC_ENCRYPTED_READBACK_VERIFIED",
                "source_content_sha256": str(readback["source_content_sha256"]),
                "resource_count": 3,
                "audit_chain_verified": True,
                "encrypted_reopen_verified": True,
                "resources": projection,
                "payload_included": False,
                "clinical_use_authorized": False,
                "production_key_provider_used": False,
                "full_fhir_r4_conformance_established": False,
                "transport_sender_authenticated": False,
                "release_authorized": False,
            }
    if Path(directory).exists():
        raise ValueError("synthetic_core_encrypted_readback_temp_store_not_removed")
    summary["ephemeral_store_removed"] = True
    raw = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > 2048:
        raise ValueError("synthetic_core_encrypted_readback_projection_oversized")
    return raw


if __name__ == "__main__":
    # Only fictional source-built constants; no CLI args/files or JSON input.
    import sys

    if sys.argv[1:]:
        sys.stderr.write("SYNTHETIC_CORE_READBACK_PROJECTION_NO_GO:arguments_refused\n")
        raise SystemExit(2)
    try:
        payload = exact_synthetic_encrypted_readback_projection()
    except Exception:
        sys.stderr.write("SYNTHETIC_CORE_READBACK_PROJECTION_NO_GO:encrypted_source_refused\n")
        raise SystemExit(2) from None
    sys.stdout.buffer.write(payload)
