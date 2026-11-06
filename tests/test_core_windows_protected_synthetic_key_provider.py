"""Real owner Windows Credential Manager --> persistent encrypted fictional Workspace.

Never real PHI/EHR. Credential target random UUID and deleted in finally.
Production resolver remains unavailable, Windows preview is opt-in only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from medscale_workspace.audit import AuditEventType, AuditTrail
from medscale_workspace.errors import (
    KeyMaterialUnavailableError,
    KeyProviderUnavailableError,
)
from medscale_workspace.keyprovider import resolve_platform_key_provider
from medscale_workspace.storage import WorkspaceStore

from medscale.fhirkit.windows_protected_key_provider import (
    WindowsCredentialPreviewError,
    WindowsProtectedSyntheticKeyProvider,
)

_FAKE_ACTOR = "fictional-developer-preview-actor"
_FAKE_TIMESTAMP = "2026-11-05T05:00:00+03:00"


def _provider(wid: UUID) -> WindowsProtectedSyntheticKeyProvider:
    return WindowsProtectedSyntheticKeyProvider(wid, synthetic_only=True, developer_preview=True)


def test_default_production_provider_remains_unavailable() -> None:
    selected = resolve_platform_key_provider()
    assert selected.capabilities.available is False
    assert selected.capabilities.protected_secret_storage is False
    with pytest.raises(KeyProviderUnavailableError):
        selected.require_available()


def test_preview_requires_explicit_flags_and_platform() -> None:
    wid = uuid4()
    with pytest.raises(WindowsCredentialPreviewError, match="explicit_fictional"):
        WindowsProtectedSyntheticKeyProvider(wid, synthetic_only=False, developer_preview=True)
    with pytest.raises(WindowsCredentialPreviewError, match="explicit_fictional"):
        WindowsProtectedSyntheticKeyProvider(wid, synthetic_only=True, developer_preview=False)
    if sys.platform != "win32":
        with pytest.raises(WindowsCredentialPreviewError, match="unavailable"):
            _provider(wid)


@pytest.mark.skipif(sys.platform != "win32", reason="Real Windows Credential Manager required")
def test_real_local_credential_reopened_across_subprocess_for_encrypted_workspace(
    tmp_path: Path,
) -> None:
    wid = uuid4()
    key = _provider(wid)
    # Remove only our own newly created credential; never touch preexisting
    # user credentials. UUID is freshly generated per test.
    created = False
    try:
        key.create_new()
        created = True
        assert key.capabilities.protected_secret_storage is True
        assert key.capabilities.persistent is True
        assert key.capabilities.production_selectable is False
        key.require_available()
        with pytest.raises(WindowsCredentialPreviewError, match="already_exists"):
            _provider(wid).create_new()
        with pytest.raises(WindowsCredentialPreviewError, match="explicit_fictional"):
            key.delete_preview_secret()

        with WorkspaceStore.open(
            store_root=str(tmp_path),
            workspace_id=wid,
            key_provider=key,
            application_version="0.1.0.dev1",
        ) as store:
            AuditTrail(store).append(
                event_type=AuditEventType.WORKSPACE_OPEN,
                actor_id=_FAKE_ACTOR,
                occurred_at=_FAKE_TIMESTAMP,
            )
            expected = AuditTrail(store).verify()
            assert expected.events_verified == 1
            assert store.object_count() > 0

        # A separate Python process must reload the user-local protected
        # credential with NO secret supplied by argv, environment or file.
        script = r"""
import json
import os
import sys
from pathlib import Path
from uuid import UUID
from medscale.fhirkit.windows_protected_key_provider import WindowsProtectedSyntheticKeyProvider
from medscale_workspace.audit import AuditTrail
from medscale_workspace.storage import WorkspaceStore
wid=UUID(sys.argv[1])
key=WindowsProtectedSyntheticKeyProvider(wid,synthetic_only=True,developer_preview=True)
key.open_existing()
key.require_available()
with WorkspaceStore.open(
    store_root=sys.argv[2],workspace_id=wid,key_provider=key,
    application_version="0.1.0.dev1",
) as store:
    verified=AuditTrail(store).verify(expected_head_event_digest=sys.argv[3])
    assert verified.events_verified==1
    assert store.object_count()>0
print(json.dumps({
    "audit_events":verified.events_verified,
    "reopened_from_windows_credential_store":True,
    "production_key_resolver_unchanged":True,
    "clinical_use_authorized":False,
}))
"""
        env = os.environ.copy()
        root = Path(__file__).resolve().parents[1]
        env["PYTHONPATH"] = os.pathsep.join(
            [str(root / "src"), str(root / "apps" / "workspace" / "src")]
        )
        env["PYTHONNOUSERSITE"] = "1"
        result = subprocess.run(
            [sys.executable, "-c", script, str(wid), str(tmp_path), expected.head_event_digest],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            check=False,
        )
        assert result.returncode == 0, result.stderr[:250]
        parsed = json.loads(result.stdout)
        assert parsed["reopened_from_windows_credential_store"] is True
        assert parsed["audit_events"] == 1
        assert parsed["clinical_use_authorized"] is False

        with pytest.raises(KeyMaterialUnavailableError):
            key.key_for_version(workspace_id=uuid4(), key_version=1, salt=b"Z" * 16)
        second = _provider(wid)
        second.open_existing()
        assert second.key_for_version(
            workspace_id=wid, key_version=1, salt=b"x" * 16
        ) == key.key_for_version(workspace_id=wid, key_version=1, salt=b"x" * 16)
        assert second.key_for_version(
            workspace_id=wid, key_version=2, salt=b"x" * 16
        ) != key.key_for_version(workspace_id=wid, key_version=1, salt=b"x" * 16)
        assert (tmp_path / f"{wid}.workspace.sqlite3").is_file()
        # No key material must exist in any task workspace file.
        raw_database = (tmp_path / f"{wid}.workspace.sqlite3").read_bytes()
        assert _FAKE_ACTOR.encode("ascii") not in raw_database
        assert b"FICTIONAL_KEY" not in raw_database
    finally:
        if created:
            key.delete_preview_secret(explicit_delete=True)
    with pytest.raises(WindowsCredentialPreviewError, match="not_found"):
        _provider(wid).open_existing()
    assert (tmp_path / f"{wid}.workspace.sqlite3").is_file()
    # The encrypted store remains, but its OS-kept root key is gone.
    with pytest.raises(KeyProviderUnavailableError):
        key.require_available()
    with (
        pytest.raises((KeyProviderUnavailableError, KeyMaterialUnavailableError)),
        WorkspaceStore.open(
            store_root=str(tmp_path),
            workspace_id=wid,
            key_provider=key,
            application_version="0.1.0.dev1",
        ),
    ):
        pass


@pytest.mark.skipif(sys.platform != "win32", reason="Real Windows Credential Manager required")
def test_missing_credential_cannot_be_implicitly_bootstrapped() -> None:
    wid = uuid4()
    provider = _provider(wid)
    with pytest.raises(WindowsCredentialPreviewError, match="not_found"):
        provider.open_existing()
    with pytest.raises(KeyProviderUnavailableError, match="not_open"):
        provider.require_available()
    with pytest.raises(WindowsCredentialPreviewError, match="not_found"):
        provider.delete_preview_secret(explicit_delete=True)


@pytest.mark.skipif(sys.platform != "win32", reason="Real Windows Credential Manager required")
def test_changed_root_is_not_silently_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even if an external same-user process changes a credential, a bound
    provider refuses to use an unexpected root secret in the same session.
    """
    from medscale.fhirkit import windows_protected_key_provider as module

    wid = uuid4()
    provider = _provider(wid)
    created = False
    try:
        provider.create_new()
        created = True
        provider.require_available()
        original_key = provider.key_for_version(workspace_id=wid, key_version=1, salt=b"w" * 16)
        assert len(original_key) == 32
        with monkeypatch.context() as patch:
            patch.setattr(module, "_read_root", lambda _target, _api: b"F" * 32)
            with pytest.raises(KeyMaterialUnavailableError, match="changed_or_unavailable"):
                provider.require_available()
            with pytest.raises(KeyMaterialUnavailableError, match="changed_or_unavailable"):
                provider.key_for_version(workspace_id=wid, key_version=1, salt=b"w" * 16)
            with pytest.raises(KeyMaterialUnavailableError, match="changed_or_unavailable"):
                provider.backup_key(workspace_id=wid, backup_id=uuid4(), salt=b"w" * 16)
            with pytest.raises(KeyMaterialUnavailableError, match="changed_or_unavailable"):
                provider.seal_key(workspace_id=wid, salt=b"w" * 16)
        provider.require_available()
        assert (
            provider.key_for_version(workspace_id=wid, key_version=1, salt=b"w" * 16)
            == original_key
        )
    finally:
        if created:
            provider.delete_preview_secret(explicit_delete=True)
    with pytest.raises(WindowsCredentialPreviewError, match="not_found"):
        _provider(wid).open_existing()


def test_invalid_workspace_identity_is_fixed_redacted_refusal() -> None:
    from medscale.fhirkit.windows_protected_key_provider import _target

    with pytest.raises(WindowsCredentialPreviewError, match="fictional_workspace_uuid_required"):
        _target("invalid-user-supplied-identity")  # type: ignore[arg-type]
