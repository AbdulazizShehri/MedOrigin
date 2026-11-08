"""Run the committed fictional Bundle through an ephemeral encrypted Workspace.

This is NOT a production EHR importer, patient-data workflow, key provider or
public release candidate. No caller-specified input or persistent store path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

WORKSPACE_ID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
ACTOR = "synthetic-ephemeral-demo"
OCCURRED_AT = "2026-11-04T04:00:00+03:00"


def run_demo() -> dict[str, object]:
    # Imports deliberately happen only after two explicit CLI opt-ins.
    from medscale_workspace.audit import AuditTrail
    from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret
    from medscale_workspace.storage import WorkspaceStore

    from medscale.fhirkit.input import read_fhir_json_document
    from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic
    from medscale.fhirkit.workspace_readback import read_synthetic_bundle_in_memory

    fixture = Path(__file__).with_name("fictional_bundle.json")
    payload = read_fhir_json_document(fixture)
    provider = InMemoryTestKeyProvider(new_root_secret())
    with TemporaryDirectory(prefix="medorigin-fictional-bundle-") as root:
        with WorkspaceStore.open(
            store_root=root,
            workspace_id=WORKSPACE_ID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as store:
            receipt = ingest_synthetic_bundle_atomic(
                payload,
                store,
                test_key_provider=provider,
                actor_id=ACTOR,
                occurred_at=OCCURRED_AT,
                synthetic_only=True,
            )
            if store.object_count() != 8 or AuditTrail(store).verify().events_verified != 1:
                raise ValueError("synthetic demo integrity check refused")
        with WorkspaceStore.open(
            store_root=root,
            workspace_id=WORKSPACE_ID,
            key_provider=provider,
            application_version="0.1.0.dev1",
        ) as reopened:
            chain = AuditTrail(reopened).verify(
                expected_head_event_digest=str(receipt["audit_head_digest"])
            )
            if reopened.object_count() != 8 or chain.events_verified != 1:
                raise ValueError("synthetic demo reopen refused")
            readback = read_synthetic_bundle_in_memory(
                reopened,
                test_key_provider=provider,
                source_content_sha256=str(receipt["source_content_sha256"]),
                expected_audit_head_digest=str(receipt["audit_head_digest"]),
                actor_id=ACTOR,
                synthetic_only=True,
                allow_in_memory_readback=True,
            )
            if readback["bundle"] != payload or readback["resource_count"] != 3:
                raise ValueError("synthetic demo in-memory readback refused")
    if Path(root).exists():
        raise ValueError("ephemeral synthetic store was not cleaned")
    return {
        "status": "SYNTHETIC_ENCRYPTED_ATOMIC_DEMO_PASS",
        "bundle_sha256": receipt["source_content_sha256"],
        "resource_count": receipt["resource_count"],
        "provenance_records": receipt["provenance_records_written"],
        "audit_events": receipt["audit_events_written"],
        "verified_reopen": True,
        "ephemeral_store_removed": True,
        "clinical_use_authorized": False,
        "production_key_provider_used": False,
        "full_fhir_r4_conformance_established": False,
        "publication_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--ephemeral-demo", action="store_true")
    args = parser.parse_args(argv)
    if not args.synthetic_only or not args.ephemeral_demo:
        print("SYNTHETIC_ENCRYPTED_ATOMIC_DEMO_REFUSED: explicit flags required", file=sys.stderr)
        return 2
    try:
        result = run_demo()
    except Exception:
        # Do not echo untrusted filenames, JSON, patients or secret material.
        print("SYNTHETIC_ENCRYPTED_ATOMIC_DEMO_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
