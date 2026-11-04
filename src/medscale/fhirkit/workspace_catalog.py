"""Core facade for a source-verified metadata-only synthetic import catalog.

This is not a patient list, user authorization, production FHIR discovery,
or clinical readiness proof. No FHIR source content leaves the facade.
"""

from __future__ import annotations

import re

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_RESULT_KEYS = frozenset(
    {
        "schema",
        "status",
        "current_audit_head_digest",
        "import_count",
        "imports",
        "payload_included",
        "filesystem_export_performed",
        "clinical_use_authorized",
        "full_fhir_r4_conformance_established",
        "release_authorized",
    }
)
_ENTRY_KEYS = frozenset(
    {"source_content_sha256", "import_audit_event_digest", "audit_sequence", "resource_count"}
)


class SyntheticWorkspaceCatalogError(ValueError):
    """Fixed redacted error, never a FHIR payload or host path."""


def list_synthetic_bundle_imports(
    store: object,
    *,
    test_key_provider: object,
    actor_id: str,
    expected_current_audit_head_digest: str,
    synthetic_only: bool = False,
    allow_in_memory_listing: bool = False,
    max_imports: int = 16,
) -> dict[str, object]:
    """List only source and audit anchors of fully verified fictional imports.

    Caller must retain and supply the current audit head outside the store,
    plus the exact in-memory test key bound to that Workspace. Results can be
    used to select a source SHA + import audit SHA for the existing Core
    in-memory readback method. An actor string is NOT login authentication.
    """
    if synthetic_only is not True:
        raise SyntheticWorkspaceCatalogError("explicit_synthetic_attestation_required")
    if allow_in_memory_listing is not True:
        raise SyntheticWorkspaceCatalogError("explicit_in_memory_listing_required")
    try:
        from medscale_workspace.fhir_catalog import (
            SyntheticFhirCatalogError,
            list_verified_synthetic_fhir_imports,
        )
    except ImportError as exc:
        raise SyntheticWorkspaceCatalogError("optional_workspace_runtime_missing") from exc
    try:
        proof = list_verified_synthetic_fhir_imports(
            store=store,
            test_key_provider=test_key_provider,
            actor_id=actor_id,
            expected_current_audit_head_digest=expected_current_audit_head_digest,
            synthetic_only=True,
            allow_in_memory_listing=True,
            max_imports=max_imports,
        )
    except SyntheticFhirCatalogError as exc:
        # Workspace emits only fixed reviewed tokens, not caller data.
        raise SyntheticWorkspaceCatalogError(str(exc)) from None

    # Second boundary: refuse unexpected members or phantom "valid" status.
    # It must not relay any unreviewed FHIR content even if a downstream
    # adapter is accidentally changed in a later version.
    if not isinstance(proof, dict) or set(proof) != _RESULT_KEYS:
        raise SyntheticWorkspaceCatalogError("catalog_contract_refused")
    if (
        proof["schema"] != "medorigin-workspace-synthetic-import-catalog/v1"
        or proof["status"] != "verified_synthetic_import_catalog"
        or proof["current_audit_head_digest"] != expected_current_audit_head_digest
        or type(proof["import_count"]) is not int
        or not isinstance(proof["imports"], list)
        or len(proof["imports"]) != proof["import_count"]
        or type(max_imports) is not int
        or not 1 <= max_imports <= 16
        or not 0 <= proof["import_count"] <= max_imports
        or any(
            proof[name] is not False
            for name in (
                "payload_included",
                "filesystem_export_performed",
                "clinical_use_authorized",
                "full_fhir_r4_conformance_established",
                "release_authorized",
            )
        )
    ):
        raise SyntheticWorkspaceCatalogError("catalog_contract_refused")
    safe: list[dict[str, object]] = []
    prior_sequence = 0
    for item in proof["imports"]:
        if not isinstance(item, dict) or set(item) != _ENTRY_KEYS:
            raise SyntheticWorkspaceCatalogError("catalog_entry_contract_refused")
        source = item["source_content_sha256"]
        event = item["import_audit_event_digest"]
        sequence = item["audit_sequence"]
        count = item["resource_count"]
        if (
            not isinstance(source, str)
            or _SHA.fullmatch(source) is None
            or not isinstance(event, str)
            or _SHA.fullmatch(event) is None
            or type(sequence) is not int
            or sequence <= prior_sequence
            or type(count) is not int
            or not 1 <= count <= 16
        ):
            raise SyntheticWorkspaceCatalogError("catalog_entry_contract_refused")
        safe.append(
            {
                "source_content_sha256": source,
                "import_audit_event_digest": event,
                "audit_sequence": sequence,
                "resource_count": count,
            }
        )
        prior_sequence = sequence
    return {
        "schema": "medorigin-core-synthetic-import-catalog/v1",
        "status": "verified_synthetic_import_catalog",
        "current_audit_head_digest": expected_current_audit_head_digest,
        "import_count": len(safe),
        "imports": safe,
        "payload_included": False,
        "filesystem_export_performed": False,
        "clinical_use_authorized": False,
        "full_fhir_r4_conformance_established": False,
        "release_authorized": False,
    }
