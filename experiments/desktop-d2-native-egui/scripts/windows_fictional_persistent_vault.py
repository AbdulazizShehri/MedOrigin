#!/usr/bin/env python3
"""Windows-only, synthetic-only persistent encrypted Workspace cold-reopen QA.

A real, *independent process* can reopen a locally AES-256-GCM encrypted
fictional Core Workspace using a test-only root key protected with Windows
user-scope DPAPI. This is NOT the production key-provider resolver and must
never admit real patient data or clinical use.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
from ctypes import wintypes
from pathlib import Path
from uuid import UUID

WORKSPACE_ID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
FIXED_TIME = "2026-11-04T04:00:00+03:00"
QA_DIR_NAME = "medorigin-d2-fixed-fictional-persistent-vault-qa"
KEY_FILE = "fictional-root-key.dpapi"
ANCHOR_FILE = "fictional-audit-anchor.dpapi"
STORE_FILE = f"{WORKSPACE_ID}.workspace.sqlite3"
SCHEMA = "medorigin-d2-windows-fictional-persistent-workspace-qa/v1"
PROJECTION_SCHEMA = "medorigin-d2-persistent-fhir-memory-readback-projection/v1"
PROJECTION_STATUS = "SYNTHETIC_PERSISTENT_ENCRYPTED_READBACK_VERIFIED"
ENTROPY = b"MedOrigin-D2-PRIVATE-SYNTHETIC-ONLY-DPAPI-QA-V1"
EXPECTED_OBJECTS = 8
EXPECTED_RESOURCES = 3


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(payload: bytes) -> tuple[_DataBlob, object]:
    if not isinstance(payload, bytes) or not payload or len(payload) > 4096:
        raise ValueError("fictional_dpapi_blob_size_refused")
    buffer = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
    return _DataBlob(len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def protect_user_local(payload: bytes) -> bytes:
    if os.name != "nt":
        raise ValueError("windows_user_dpapi_required")
    input_blob, input_buf = _blob(payload)
    entropy_blob, entropy_buf = _blob(ENTROPY)
    output_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "MedOrigin fictional developer QA",
        ctypes.byref(entropy_blob),
        None,
        None,
        0x1,
        ctypes.byref(output_blob),
    ):
        raise ValueError("fictional_user_dpapi_protect_refused")
    try:
        if not output_blob.pbData or not 16 <= output_blob.cbData <= 4096:
            raise ValueError("fictional_dpapi_output_size_refused")
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(output_blob.pbData, ctypes.c_void_p))
        del input_buf, entropy_buf


def unprotect_user_local(protected: bytes) -> bytes:
    if os.name != "nt":
        raise ValueError("windows_user_dpapi_required")
    input_blob, input_buf = _blob(protected)
    entropy_blob, entropy_buf = _blob(ENTROPY)
    output_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        ctypes.byref(entropy_blob),
        None,
        None,
        0x1,
        ctypes.byref(output_blob),
    ):
        raise ValueError("fictional_user_dpapi_unprotect_refused")
    try:
        if not output_blob.pbData or not 1 <= output_blob.cbData <= 4096:
            raise ValueError("fictional_dpapi_unwrapped_size_refused")
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(output_blob.pbData, ctypes.c_void_p))
        del input_buf, entropy_buf


def _safe_qa_root(path: Path, *, create: bool) -> Path:
    if os.name != "nt":
        raise ValueError("windows_only_fictional_persistent_qa")
    if path.name != QA_DIR_NAME or not path.is_absolute() or ".." in path.parts:
        raise ValueError("fictional_qa_vault_root_name_or_path_refused")
    if path.is_symlink() or path.parent.is_symlink() or not path.parent.is_dir():
        raise ValueError("fictional_qa_vault_parent_untrusted")
    if create:
        if path.exists():
            raise ValueError("fictional_qa_vault_exists_do_not_overwrite")
    elif not path.is_dir():
        raise ValueError("fictional_qa_vault_not_created")
    else:
        for name in (KEY_FILE, ANCHOR_FILE, STORE_FILE):
            f = path / name
            if f.is_symlink() or not f.is_file():
                raise ValueError("fictional_qa_vault_missing_verified_component")
    return path


def _write_new(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("fictional_qa_vault_existing_file_refused")
    # Exclusive create: never truncate prior QA, user or workspace content.
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _read_protected(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or not 16 <= path.stat().st_size <= 4096:
        raise ValueError("fictional_dpapi_component_missing_or_invalid")
    return unprotect_user_local(path.read_bytes())


def _dependencies() -> tuple:
    # This optional installed/source Core is available only to explicit QA;
    # no development helper alters the Core production key resolver.
    from medscale_workspace.audit import AuditTrail
    from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret
    from medscale_workspace.storage import WorkspaceStore

    from medscale.fhirkit.workspace_demo import _fictional_bundle
    from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic
    from medscale.fhirkit.workspace_readback import read_synthetic_bundle_in_memory

    return (
        _fictional_bundle,
        ingest_synthetic_bundle_atomic,
        read_synthetic_bundle_in_memory,
        AuditTrail,
        InMemoryTestKeyProvider,
        new_root_secret,
        WorkspaceStore,
    )


def _assert_fictional_reopen(
    store, provider, source_sha: str, audit_head: str, deps: tuple
) -> dict:
    fictional_bundle, _, reader, audit_cls, _, _, _ = deps
    if store.object_count() != EXPECTED_OBJECTS:
        raise ValueError("fictional_vault_encrypted_object_count_refused")
    if audit_cls(store).verify(expected_head_event_digest=audit_head).events_verified != 1:
        raise ValueError("fictional_vault_audit_head_refused")
    result = reader(
        store,
        test_key_provider=provider,
        source_content_sha256=source_sha,
        expected_audit_head_digest=audit_head,
        actor_id="fictional-core-demo",
        synthetic_only=True,
        allow_in_memory_readback=True,
    )
    if (
        result["bundle"] != fictional_bundle()
        or result["resource_count"] != EXPECTED_RESOURCES
        or result["source_content_sha256"] != source_sha
        or result["clinical_use_authorized"] is not False
        or result["release_authorized"] is not False
    ):
        raise ValueError("fictional_persistent_workspace_source_identity_refused")
    return result


def create_fixed_fictional_qa_vault(root: Path) -> None:
    root = _safe_qa_root(root, create=True)
    bundle, importer, _, audit_cls, provider_cls, new_root_secret, store_cls = _dependencies()
    secret = new_root_secret()
    if not isinstance(secret, bytes) or len(secret) != 32:
        raise ValueError("fictional_test_secret_size_refused")
    protected_secret = protect_user_local(secret)
    if secret in protected_secret:
        raise ValueError("fictional_test_secret_in_protected_blob_refused")
    root.mkdir(mode=0o700)
    _write_new(root / KEY_FILE, protected_secret)
    provider = provider_cls(secret)
    with store_cls.open(
        store_root=str(root),
        workspace_id=WORKSPACE_ID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    ) as store:
        receipt = importer(
            bundle(),
            store,
            test_key_provider=provider,
            actor_id="fictional-core-demo",
            occurred_at=FIXED_TIME,
            synthetic_only=True,
        )
        if (
            store.object_count() != EXPECTED_OBJECTS
            or audit_cls(store)
            .verify(expected_head_event_digest=receipt["audit_head_digest"])
            .events_verified
            != 1
        ):
            raise ValueError("fictional_persistent_first_write_verification_refused")
    anchor = {
        "schema": SCHEMA,
        "workspace_id": str(WORKSPACE_ID),
        "source_content_sha256": receipt["source_content_sha256"],
        "audit_head_digest": receipt["audit_head_digest"],
        "test_in_memory_provider_only": True,
        "clinical_use_authorized": False,
        "production_key_provider_used": False,
    }
    _write_new(
        root / ANCHOR_FILE,
        protect_user_local(
            json.dumps(anchor, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ),
    )
    if not (root / STORE_FILE).is_file():
        raise ValueError("fictional_persistent_real_sqlite_store_missing")
    print("WINDOWS_REAL_FICTIONAL_ENCRYPTED_WORKSPACE_PERSISTENT_CREATED_DPAPI_QA")


def reopen_fixed_fictional_qa_vault(root: Path, *, emit_marker: bool = True) -> dict:
    root = _safe_qa_root(root, create=False)
    deps = _dependencies()
    _, _, _, _, provider_cls, _, store_cls = deps
    secret = _read_protected(root / KEY_FILE)
    if len(secret) != 32:
        raise ValueError("fictional_dpapi_unsealed_test_secret_length_refused")
    payload = json.loads(_read_protected(root / ANCHOR_FILE))
    if (
        not isinstance(payload, dict)
        or set(payload)
        != {
            "schema",
            "workspace_id",
            "source_content_sha256",
            "audit_head_digest",
            "test_in_memory_provider_only",
            "clinical_use_authorized",
            "production_key_provider_used",
        }
        or payload["schema"] != SCHEMA
        or payload["workspace_id"] != str(WORKSPACE_ID)
        or payload["test_in_memory_provider_only"] is not True
        or payload["clinical_use_authorized"] is not False
        or payload["production_key_provider_used"] is not False
        or not isinstance(payload["audit_head_digest"], str)
        or len(payload["audit_head_digest"]) != 64
        or not isinstance(payload["source_content_sha256"], str)
        or len(payload["source_content_sha256"]) != 64
        or not all(c in "0123456789abcdef" for c in payload["audit_head_digest"])
        or not all(c in "0123456789abcdef" for c in payload["source_content_sha256"])
    ):
        raise ValueError("fictional_persistent_audit_anchor_contract_refused")
    provider = provider_cls(secret)
    with store_cls.open(
        store_root=str(root),
        workspace_id=WORKSPACE_ID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    ) as reopened:
        verified = _assert_fictional_reopen(
            reopened,
            provider,
            payload["source_content_sha256"],
            payload["audit_head_digest"],
            deps,
        )
    if emit_marker:
        print("WINDOWS_REAL_FICTIONAL_ENCRYPTED_WORKSPACE_COLD_REOPEN_DPAPI_QA_PASS")
    return verified


def exact_persistent_fictional_projection(root: Path) -> bytes:
    # A *cold-reopened persistent* source, not a new ephemeral demo. All
    # returned fields are redacted identities/links from the real decrypted
    # fixed fictional Core Bundle, never patient names, codes or values.
    readback = reopen_fixed_fictional_qa_vault(root, emit_marker=False)
    entries = readback["bundle"]["entry"]
    expected = (
        (
            "Observation",
            "fictional-observation-001",
            "urn:uuid:00000000-0000-4000-8000-000000000001",
        ),
        ("Patient", "fictional-patient-001", "urn:uuid:00000000-0000-4000-8000-000000000002"),
        ("Encounter", "fictional-encounter-001", "urn:uuid:00000000-0000-4000-8000-000000000003"),
    )
    if len(entries) != EXPECTED_RESOURCES:
        raise ValueError("fictional_persistent_projection_three_entries_required")
    projection = []
    for item, (kind, identity, full_url) in zip(entries, expected, strict=True):
        resource = item["resource"]
        if (
            resource["resourceType"] != kind
            or resource["id"] != identity
            or item["fullUrl"] != full_url
        ):
            raise ValueError("fictional_persistent_projection_identity_refused")
        links = [
            {"field": field, "target": resource[field]["reference"]}
            for field in ("subject", "encounter")
            if field in resource
        ]
        projection.append(
            {
                "resource_type": kind,
                "id": identity,
                "full_url": full_url,
                "links": links,
            }
        )
    summary = {
        "schema": PROJECTION_SCHEMA,
        "status": PROJECTION_STATUS,
        "source_content_sha256": readback["source_content_sha256"],
        "resource_count": EXPECTED_RESOURCES,
        "audit_chain_verified": True,
        "encrypted_reopen_verified": True,
        "persistent_test_vault_reopened": True,
        "ephemeral_store_removed": False,
        "resources": projection,
        "payload_included": False,
        "clinical_use_authorized": False,
        "production_key_provider_used": False,
        "full_fhir_r4_conformance_established": False,
        "transport_sender_authenticated": False,
        "release_authorized": False,
    }
    raw = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if not 1164 < len(raw) <= 2048:
        raise ValueError("fictional_persistent_projection_size_refused")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["create", "reopen", "report"], required=True)
    parser.add_argument("--qa-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.phase == "create":
            create_fixed_fictional_qa_vault(args.qa_root)
        elif args.phase == "reopen":
            reopen_fixed_fictional_qa_vault(args.qa_root)
        else:
            sys.stdout.buffer.write(exact_persistent_fictional_projection(args.qa_root))
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError):
        print("WINDOWS_FICTIONAL_PERSISTENT_VAULT_NO_GO", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
