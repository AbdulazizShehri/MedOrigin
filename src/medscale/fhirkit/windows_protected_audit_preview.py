"""An explicit Windows protected-credential, fictional audit-only Workspace lifecycle.

This host-side Core *developer preview* is NOT Clinical Workspace production,
an FHIR importer, a patient-data path, or an authorization system. It leaves
CW-002 guarded Workspace sources and the unavailable production resolver alone.
"""

from __future__ import annotations

# mypy: disable-error-code="import-not-found"
# The Workspace package under apps/workspace is deliberately outside strict mypy's
# file set while Issue #464 item 1 is open; it is imported at runtime. Declaring
# the missing import here keeps that deferral explicit.
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from medscale_workspace.audit import AuditEventType, AuditTrail
from medscale_workspace.storage import WorkspaceStore
from medscale_workspace.store_path import resolve_workspace_store_path

from medscale.fhirkit.windows_protected_key_provider import WindowsProtectedSyntheticKeyProvider

_FOLDER = "medorigin-fictional-workspace-preview"
_ANCHOR = re.compile(r"[0-9a-f]{64}\Z")
_APP_VERSION = "0.1.0.dev1"
_ACTOR = "fictional-windows-protected-preview"
_SCHEMA = "medorigin-core-windows-synthetic-protected-audit-preview/v1"


class WindowsAuditPreviewError(ValueError):
    """Fixed, non-PHI error only; never include paths, UUIDs or OS messages."""


def _admit(
    action: object,
    root: object,
    identity: object,
    anchor: object,
    *,
    synthetic_only: bool,
    developer_preview: bool,
    irreversible_delete_acknowledged: bool,
) -> tuple[Path, UUID, str | None, Path]:
    if synthetic_only is not True or developer_preview is not True:
        raise WindowsAuditPreviewError("fictional_windows_preview_opt_in_required")
    if type(action) is not str or action not in ("create", "verify", "forget"):
        raise WindowsAuditPreviewError("fictional_windows_preview_action_refused")
    if (
        type(identity) is not UUID
        or identity.version != 4
        or not isinstance(root, Path)
        or not root.is_absolute()
        or ".." in root.parts
        or root.name != _FOLDER
        or not root.is_dir()
        or root.is_symlink()
        or root.absolute() != root.resolve(strict=True)
    ):
        raise WindowsAuditPreviewError("fictional_windows_preview_store_root_refused")

    # The reviewed Workspace path resolver is single-sourced. The preview
    # never permits caller-controlled filenames or arbitrary existing DBs.
    try:
        path = Path(resolve_workspace_store_path(str(root), identity))
    except Exception as exc:
        raise WindowsAuditPreviewError("fictional_windows_preview_store_root_refused") from exc
    if path.parent != root or path.is_symlink():
        raise WindowsAuditPreviewError("fictional_windows_preview_store_root_refused")
    if action == "create":
        if anchor is not None or irreversible_delete_acknowledged is not False:
            raise WindowsAuditPreviewError("fictional_windows_preview_flags_refused")
        if path.exists():
            raise WindowsAuditPreviewError("fictional_windows_preview_existing_store_refused")
        return root, identity, None, path

    if (
        type(anchor) is not str
        or _ANCHOR.fullmatch(anchor) is None
        or irreversible_delete_acknowledged is not (action == "forget")
    ):
        raise WindowsAuditPreviewError("fictional_windows_preview_flags_refused")
    if not path.is_file() or path.is_symlink():
        raise WindowsAuditPreviewError("fictional_windows_preview_store_missing")
    return root, identity, anchor, path


def _safe_report(
    action: str, *, head: str | None, count: int, key_deleted: bool
) -> dict[str, object]:
    """Metadata only, not a medical validation or an export of stored data."""
    return {
        "schema": _SCHEMA,
        "status": "FICTIONAL_WINDOWS_PROTECTED_AUDIT_PREVIEW_ONLY",
        "operation": action,
        "verified_audit_events": count,
        "audit_head_sha256": head if action == "create" else None,
        "anchor_matched": action != "create",
        "protected_credential_destroyed": key_deleted,
        "encrypted_workspace_store_preserved": action == "forget",
        "patient_data_admitted": False,
        "fhir_r4_conformance_validated": False,
        "clinical_use_authorized": False,
        "production_key_provider_selected": False,
        "publication_authorized": False,
    }


def run_windows_audit_preview(
    action: str,
    store_root: Path,
    workspace_id: UUID,
    expected_head: str | None = None,
    *,
    synthetic_only: bool = False,
    developer_preview: bool = False,
    irreversible_delete_acknowledged: bool = False,
) -> dict[str, object]:
    """Real, single-event, synthetic-only encrypted OS-key Workspace workflow.

    Create requires an existing explicitly named dedicated empty workspace
    directory. Verify/forget require the independent anchor returned at create.
    Nothing in this function ingests user-supplied FHIR, documents or patient
    data. All exceptions are reduced to reviewed fixed refusal tokens.
    """
    root, wid, anchor, _ = _admit(
        action,
        store_root,
        workspace_id,
        expected_head,
        synthetic_only=synthetic_only,
        developer_preview=developer_preview,
        irreversible_delete_acknowledged=irreversible_delete_acknowledged,
    )
    provider = WindowsProtectedSyntheticKeyProvider(
        wid, synthetic_only=True, developer_preview=True
    )
    if action == "create":
        created = False
        try:
            provider.create_new()
            created = True
            with WorkspaceStore.open(
                store_root=str(root),
                workspace_id=wid,
                key_provider=provider,
                application_version=_APP_VERSION,
            ) as store:
                if store.object_count() != 0:
                    raise WindowsAuditPreviewError(
                        "fictional_windows_preview_nonempty_store_refused"
                    )
                AuditTrail(store).append(
                    event_type=AuditEventType.WORKSPACE_OPEN,
                    actor_id=_ACTOR,
                    occurred_at=datetime.now(UTC).isoformat(timespec="seconds"),
                )
                report = AuditTrail(store).verify()
                if (
                    report.events_verified != 1
                    or type(report.head_event_digest) is not str
                    or _ANCHOR.fullmatch(report.head_event_digest) is None
                    or store.object_count() != 1
                ):
                    raise WindowsAuditPreviewError(
                        "fictional_windows_preview_audit_contract_refused"
                    )
                return _safe_report(
                    action, head=report.head_event_digest, count=1, key_deleted=False
                )
        except Exception as exc:
            if created:
                # No orphan root key on incomplete setup. This may leave a
                # task-owned encrypted file requiring explicit filesystem
                # cleanup; never delete arbitrary caller paths automatically.
                try:
                    provider.delete_preview_secret(explicit_delete=True)
                except Exception as cleanup:
                    raise WindowsAuditPreviewError(
                        "fictional_windows_preview_setup_cleanup_refused"
                    ) from cleanup
            raise WindowsAuditPreviewError("fictional_windows_preview_create_refused") from exc

    try:
        provider.open_existing()  # MUST NOT implicitly generate a missing key.
        with WorkspaceStore.open(
            store_root=str(root),
            workspace_id=wid,
            key_provider=provider,
            application_version=_APP_VERSION,
        ) as store:
            verified = AuditTrail(store).verify(expected_head_event_digest=anchor)
            if verified.events_verified != 1 or store.object_count() != 1:
                raise WindowsAuditPreviewError("fictional_windows_preview_audit_contract_refused")
        if action == "forget":
            provider.delete_preview_secret(explicit_delete=True)
        return _safe_report(action, head=None, count=1, key_deleted=action == "forget")
    except Exception as exc:
        raise WindowsAuditPreviewError(
            "fictional_windows_preview_verify_or_forget_refused"
        ) from exc
