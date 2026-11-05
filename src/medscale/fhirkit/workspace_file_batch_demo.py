"""Actual caller-file fictional FHIR Bundles -> encrypted ephemeral Workspace -> cold reopen.

This is an owner-local developer workflow, NOT production storage, PHI
admission, clinical readiness, full FHIR R4 conformance, or real user auth.
Only bounded invented and explicitly tagged synthetic fixtures are admitted.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import UUID

from medscale.fhirkit.bundle import BundlePreflightError, inspect_synthetic_bundle
from medscale.fhirkit.input import MAX_FHIR_INPUT_BYTES
from medscale.reproducibility import content_hash

_WORKSPACE = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
_ACTOR = "fictional-file-batch-import-operator"
_MAX_FILES = 4
_MAX_RESOURCES = 64
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class SyntheticFileImportDemoError(ValueError):
    """Fixed redacted refusal; never an unreviewed caller path or payload."""


def _freeze_and_preflight(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> tuple[list[dict[str, Any]], list[dict[str, object]]]:
    """Qualify ALL sources before allocating a Workspace or writing anything."""
    if type(payloads) not in (list, tuple) or not 2 <= len(payloads) <= _MAX_FILES:
        raise SyntheticFileImportDemoError("fictional_import_file_count_refused")

    snapshots: list[dict[str, Any]] = []
    proofs: list[dict[str, object]] = []
    hashes: set[str] = set()
    resource_total = 0
    for item in payloads:
        if type(item) is not dict:
            raise SyntheticFileImportDemoError("fictional_import_source_type_refused")
        try:
            raw = json.dumps(
                item,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            if len(raw) > MAX_FHIR_INPUT_BYTES:
                raise SyntheticFileImportDemoError("fictional_import_source_size_refused")
            snapshot = json.loads(raw)
            preflight = inspect_synthetic_bundle(snapshot)
        except SyntheticFileImportDemoError:
            raise
        except (BundlePreflightError, TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise SyntheticFileImportDemoError("fictional_import_source_preflight_refused") from exc
        digest = preflight.get("source_content_sha256")
        count = preflight.get("resource_count")
        counts = preflight.get("resource_counts")
        if (
            preflight.get("schema") != "medorigin-synthetic-fhir-bundle-preflight/v1"
            or preflight.get("status") != "local_relationship_preflight_only"
            or preflight.get("data_class") != "SYNTHETIC_ASSERTED_NOT_VERIFIED"
            or type(digest) is not str
            or _SHA.fullmatch(digest) is None
            or digest != content_hash(snapshot)
            or digest in hashes
            or type(count) is not int
            or not 1 <= count <= 16
            or type(counts) is not dict
            or set(counts) != {"Patient", "Encounter", "Observation"}
            or any(type(v) is not int or v < 0 for v in counts.values())
            or sum(counts.values()) != count
            or counts["Patient"] != 1
            or preflight.get("payload_content_included") is not False
            or preflight.get("input_persisted") is not False
            or preflight.get("network_access_performed") is not False
            or preflight.get("clinical_use_authorized") is not False
            or preflight.get("full_fhir_r4_conformance_established") is not False
        ):
            raise SyntheticFileImportDemoError("fictional_import_preflight_contract_refused")
        hashes.add(digest)
        resource_total += count
        if resource_total > _MAX_RESOURCES:
            raise SyntheticFileImportDemoError("fictional_import_resource_limit_refused")
        snapshots.append(snapshot)
        proofs.append(
            {
                "source_content_sha256": digest,
                "resource_count": count,
            }
        )
    return snapshots, proofs


def run_fictional_file_batch_encrypted_demo(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    synthetic_only: bool = False,
    ephemeral_demo: bool = False,
) -> dict[str, object]:
    """Commit provided fictional Bundles; independently verify cold-reopened data.

    Test-only in-memory ephemeral key: Workspace is removed on exit. No
    caller-supplied permanent storage paths or production keys. Any failure
    aborts with zero output and automatic temporary store cleanup.
    """
    if synthetic_only is not True or ephemeral_demo is not True:
        raise SyntheticFileImportDemoError("fictional_import_explicit_demo_flags_required")
    snapshots, preflights = _freeze_and_preflight(payloads)

    try:
        from medscale_workspace.audit import AuditTrail
        from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret
        from medscale_workspace.storage import WorkspaceStore

        from medscale.fhirkit.workspace_catalog import list_synthetic_bundle_imports
        from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic
        from medscale.fhirkit.workspace_multi_timeline import (
            list_verified_synthetic_import_timelines,
        )
    except ImportError as exc:
        raise SyntheticFileImportDemoError(
            "fictional_import_optional_workspace_runtime_missing"
        ) from exc

    # The fixture actor/time do not represent authenticated real humans.
    provider = InMemoryTestKeyProvider(new_root_secret())
    result: dict[str, object] | None = None
    with TemporaryDirectory(prefix="medorigin-fictional-file-import-") as directory:
        try:
            with WorkspaceStore.open(
                store_root=directory,
                workspace_id=_WORKSPACE,
                key_provider=provider,
                application_version="0.1.0.dev1",
            ) as store:
                imported: list[dict[str, object]] = []
                for index, bundle in enumerate(snapshots, 1):
                    receipt = ingest_synthetic_bundle_atomic(
                        bundle,
                        store,
                        test_key_provider=provider,
                        actor_id=_ACTOR,
                        occurred_at=f"2026-11-05T03:{index:02d}:00+03:00",
                        synthetic_only=True,
                    )
                    original = preflights[index - 1]
                    if (
                        receipt.get("schema") != "medorigin-synthetic-workspace-atomic-ingest/v1"
                        or receipt.get("status") != "synthetic_test_store_committed"
                        or receipt.get("source_content_sha256") != original["source_content_sha256"]
                        or receipt.get("resource_count") != original["resource_count"]
                        or type(receipt.get("audit_head_digest")) is not str
                        or _SHA.fullmatch(receipt["audit_head_digest"]) is None
                        or receipt.get("payload_included") is not False
                        or receipt.get("production_key_provider_used") is not False
                        or receipt.get("clinical_use_authorized") is not False
                        or receipt.get("full_fhir_r4_conformance_established") is not False
                        or receipt.get("release_authorized") is not False
                    ):
                        raise SyntheticFileImportDemoError(
                            "fictional_import_commit_contract_refused"
                        )
                    imported.append(
                        {
                            "source_content_sha256": receipt["source_content_sha256"],
                            "resource_count": receipt["resource_count"],
                            "import_audit_event_digest": receipt["audit_head_digest"],
                        }
                    )
                final_head = str(imported[-1]["import_audit_event_digest"])
                verified = AuditTrail(store).verify(expected_head_event_digest=final_head)
                if verified.events_verified != len(imported):
                    raise SyntheticFileImportDemoError("fictional_import_initial_audit_refused")
            # Real physical close / cold reopen with same in-memory test key.
            with WorkspaceStore.open(
                store_root=directory,
                workspace_id=_WORKSPACE,
                key_provider=provider,
                application_version="0.1.0.dev1",
            ) as reopened:
                verified = AuditTrail(reopened).verify(expected_head_event_digest=final_head)
                if verified.events_verified != len(imported):
                    raise SyntheticFileImportDemoError("fictional_import_reopened_audit_refused")
                catalog = list_synthetic_bundle_imports(
                    reopened,
                    test_key_provider=provider,
                    actor_id=_ACTOR,
                    expected_current_audit_head_digest=final_head,
                    synthetic_only=True,
                    allow_in_memory_listing=True,
                )
                timeline = list_verified_synthetic_import_timelines(
                    store=reopened,
                    test_key_provider=provider,
                    actor_id=_ACTOR,
                    expected_current_audit_head_digest=final_head,
                    synthetic_only=True,
                    allow_in_memory_listing=True,
                    allow_in_memory_timeline=True,
                )
                if (
                    catalog.get("schema") != "medorigin-core-synthetic-import-catalog/v1"
                    or catalog.get("status") != "verified_synthetic_import_catalog"
                    or catalog.get("import_count") != len(imported)
                    or catalog.get("current_audit_head_digest") != final_head
                    or type(catalog.get("imports")) is not list
                    or timeline.get("schema")
                    != "medorigin-core-verified-fictional-multiimport-timelines/v1"
                    or timeline.get("status") != "verified_independent_import_timelines"
                    or timeline.get("import_count") != len(imported)
                    or timeline.get("current_audit_head_digest") != final_head
                    or type(timeline.get("imports")) is not list
                    or timeline.get("cross_import_patient_identity_join_performed") is not False
                    or timeline.get("patient_identity_included") is not False
                    or timeline.get("resource_payload_included") is not False
                    or any(
                        catalog.get(flag) is not False
                        for flag in (
                            "payload_included",
                            "filesystem_export_performed",
                            "clinical_use_authorized",
                            "full_fhir_r4_conformance_established",
                            "release_authorized",
                        )
                    )
                ):
                    raise SyntheticFileImportDemoError(
                        "fictional_import_cold_reopen_contract_refused"
                    )
                source_total = sum(x["resource_count"] for x in imported)
                safe: list[dict[str, object]] = []
                total_events = 0
                for index, (original, record, view) in enumerate(
                    zip(imported, catalog["imports"], timeline["imports"], strict=True), 1
                ):
                    if (
                        type(record) is not dict
                        or type(view) is not dict
                        or record.get("source_content_sha256") != original["source_content_sha256"]
                        or record.get("import_audit_event_digest")
                        != original["import_audit_event_digest"]
                        or record.get("resource_count") != original["resource_count"]
                        or view.get("source_content_sha256") != original["source_content_sha256"]
                        or view.get("import_audit_event_digest")
                        != original["import_audit_event_digest"]
                        or view.get("source_resource_count") != original["resource_count"]
                        or view.get("patient_count_within_import") != 1
                        or view.get("patient_selection_mode") != "single_unique_patient"
                        or view.get("import_ordinal") != index
                        or type(view.get("event_count")) is not int
                        or not 0 <= view["event_count"] <= original["resource_count"]
                    ):
                        raise SyntheticFileImportDemoError(
                            "fictional_import_reopen_source_identity_refused"
                        )
                    total_events += view["event_count"]
                    # Return only locally reconstructed, reviewed scalars.
                    safe.append(
                        {
                            "import_ordinal": index,
                            "source_content_sha256": original["source_content_sha256"],
                            "import_audit_event_digest": original["import_audit_event_digest"],
                            "resource_count": original["resource_count"],
                            "verified_timeline_event_count": view["event_count"],
                            "patient_count_within_import": 1,
                        }
                    )
                if total_events != timeline.get("total_event_count") or source_total != sum(
                    x["resource_count"] for x in safe
                ):
                    raise SyntheticFileImportDemoError("fictional_import_reopen_totals_refused")
                result = {
                    "schema": "medorigin-core-fictional-file-encrypted-batch-reopen/v1",
                    "status": "FICTIONAL_FILE_BATCH_ENCRYPTED_REOPEN_VERIFIED",
                    "import_count": len(safe),
                    "resource_count": source_total,
                    "verified_timeline_event_count": total_events,
                    "verified_audit_events": verified.events_verified,
                    "current_audit_head_digest": final_head,
                    "imports": safe,
                    "physically_closed_and_reopened": True,
                    "source_filenames_included": False,
                    "patient_identity_included": False,
                    "resource_payload_included": False,
                    "permanent_workspace_created": False,
                    "production_key_provider_used": False,
                    "cross_import_patient_identity_join_performed": False,
                    "network_access_performed": False,
                    "fhir_r4_conformance_validated": False,
                    "clinical_use_authorized": False,
                    "release_authorized": False,
                }
        except SyntheticFileImportDemoError:
            raise
        except Exception as exc:
            # No source payload, path, raw exception, key material in errors.
            raise SyntheticFileImportDemoError(
                "fictional_import_encrypted_workspace_verification_refused"
            ) from exc
    if Path(directory).exists():
        raise SyntheticFileImportDemoError("fictional_import_ephemeral_cleanup_refused")
    if result is None:
        raise SyntheticFileImportDemoError("fictional_import_no_verified_result")
    return {
        **result,
        "ephemeral_store_removed": True,
    }


def fictional_file_batch_receipt_json(
    payloads: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    synthetic_only: bool = False,
    ephemeral_demo: bool = False,
) -> str:
    return (
        json.dumps(
            run_fictional_file_batch_encrypted_demo(
                payloads,
                synthetic_only=synthetic_only,
                ephemeral_demo=ephemeral_demo,
            ),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    )
