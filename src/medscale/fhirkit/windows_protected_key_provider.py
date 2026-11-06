"""Owner-local Windows Credential Manager adapter for synthetic encrypted Workspaces.

This explicit, unpublished developer-preview adapter lives OUTSIDE the
guarded Clinical Workspace. ADR-0039 still forbids OS/ctypes imports inside
the Workspace package; its production key resolver remains unavailable.

No plaintext key files, registry storage, network, alternate key provider
fallback, cloud or real-patient/EHR admission. No secret/target in errors.
This is NOT an approved production key-custody implementation.
"""

from __future__ import annotations

import ctypes
import hashlib
import sys
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from medscale_workspace.errors import (  # type: ignore[import-untyped]
    KeyMaterialUnavailableError,
    KeyProviderUnavailableError,
)
from medscale_workspace.keyderive import (  # type: ignore[import-untyped]
    derive_backup_key,
    derive_seal_key,
    derive_workspace_key,
)
from medscale_workspace.keyprovider import (  # type: ignore[import-untyped]
    KeyProvider,
    KeyProviderCapabilities,
    new_root_secret,
)

_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_CRED_MISSING = 1168
_WAIT_OBJECT_0 = 0
_WAIT_ABANDONED = 0x80
_MUTEX_TIMEOUT_MS = 10000
_BYTES = 32
_TARGET_PREFIX = "MedOrigin/FictionalDeveloperPreview/v1/"
_USER = "MedOrigin-Fictional-Developer-Only"


class WindowsCredentialPreviewError(ValueError):
    """No external Windows string, user account or secret in the error."""


class _FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


class _CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", _FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _require_win_owner_preview(*, synthetic_only: bool, developer_preview: bool) -> None:
    if synthetic_only is not True or developer_preview is not True:
        raise WindowsCredentialPreviewError("explicit_fictional_windows_preview_flags_required")
    if sys.platform != "win32" or not hasattr(ctypes, "WinDLL"):
        raise WindowsCredentialPreviewError("windows_protected_credential_store_unavailable")


def _target(workspace_id: UUID) -> str:
    if type(workspace_id) is not UUID:
        raise WindowsCredentialPreviewError("fictional_workspace_uuid_required")
    return _TARGET_PREFIX + str(workspace_id)


@dataclass(frozen=True)
class _WinApis:
    read: Callable[..., Any]
    write: Callable[..., Any]
    delete: Callable[..., Any]
    free: Callable[..., Any]
    mutex_create: Callable[..., Any]
    mutex_wait: Callable[..., Any]
    mutex_release: Callable[..., Any]
    handle_close: Callable[..., Any]


def _win_apis() -> _WinApis:
    try:
        advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel = ctypes.WinDLL("Kernel32.dll", use_last_error=True)

        read = advapi.CredReadW
        read.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(_CREDENTIAL)),
        ]
        read.restype = wintypes.BOOL

        write = advapi.CredWriteW
        write.argtypes = [ctypes.POINTER(_CREDENTIAL), wintypes.DWORD]
        write.restype = wintypes.BOOL

        delete = advapi.CredDeleteW
        delete.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        delete.restype = wintypes.BOOL

        free = advapi.CredFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = None

        mutex_create = kernel.CreateMutexW
        mutex_create.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        mutex_create.restype = wintypes.HANDLE

        mutex_wait = kernel.WaitForSingleObject
        mutex_wait.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        mutex_wait.restype = wintypes.DWORD

        mutex_release = kernel.ReleaseMutex
        mutex_release.argtypes = [wintypes.HANDLE]
        mutex_release.restype = wintypes.BOOL

        handle_close = kernel.CloseHandle
        handle_close.argtypes = [wintypes.HANDLE]
        handle_close.restype = wintypes.BOOL
        return _WinApis(
            read,
            write,
            delete,
            free,
            mutex_create,
            mutex_wait,
            mutex_release,
            handle_close,
        )
    except (AttributeError, OSError) as exc:
        raise WindowsCredentialPreviewError(
            "windows_protected_credential_store_unavailable"
        ) from exc


def _read_root(target: str, api: _WinApis) -> bytes | None:
    pointer = ctypes.POINTER(_CREDENTIAL)()
    if not api.read(target, _CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
        if ctypes.get_last_error() == _CRED_MISSING:
            return None
        raise WindowsCredentialPreviewError("windows_protected_credential_read_refused")
    try:
        if not bool(pointer):
            raise WindowsCredentialPreviewError("windows_protected_credential_contract_refused")
        record = pointer.contents
        if (
            record.Type != _CRED_TYPE_GENERIC
            or record.Persist != _CRED_PERSIST_LOCAL_MACHINE
            or record.CredentialBlobSize != _BYTES
            or not bool(record.CredentialBlob)
            or record.TargetName != target
            or record.UserName != _USER
        ):
            raise WindowsCredentialPreviewError("windows_protected_credential_contract_refused")
        return ctypes.string_at(record.CredentialBlob, _BYTES)
    finally:
        if bool(pointer):
            api.free(ctypes.cast(pointer, ctypes.c_void_p))


class _CreateMutex:
    def __init__(self, workspace_id: UUID, api: _WinApis) -> None:
        self.api = api
        self.handle = None
        self.id = workspace_id

    def __enter__(self) -> None:
        name = "Local\\MedOrigin_Fictional_Credential_" + self.id.hex
        self.handle = self.api.mutex_create(None, False, name)
        if not self.handle:
            raise WindowsCredentialPreviewError("windows_protected_credential_mutex_unavailable")
        status = self.api.mutex_wait(self.handle, _MUTEX_TIMEOUT_MS)
        if status != _WAIT_OBJECT_0:
            self.api.handle_close(self.handle)
            self.handle = None
            raise WindowsCredentialPreviewError("windows_protected_credential_mutex_refused")
        return None

    def __exit__(self, _type: object, _value: object, _trace: object) -> None:
        if self.handle:
            self.api.mutex_release(self.handle)
            self.api.handle_close(self.handle)
            self.handle = None


class WindowsProtectedSyntheticKeyProvider(KeyProvider):  # type: ignore[misc]
    """Explicit synthetic-preview Windows protected-key provider.

    The production resolver NEVER selects this adapter; it is not a
    substitute for the governed clinical production key-provider review.
    """

    capabilities = KeyProviderCapabilities(
        identifier="medorigin-windows-credential-synthetic-preview-v1",
        protected_secret_storage=True,
        available=True,
        derivable_key_material=True,
        persistent=True,
        production_selectable=False,
        notes="Per-user Windows Credential Manager local persistence; synthetic-only",
    )

    def __init__(self, workspace_id: UUID, *, synthetic_only: bool, developer_preview: bool):
        _require_win_owner_preview(
            synthetic_only=synthetic_only, developer_preview=developer_preview
        )
        self._workspace_id = workspace_id
        self._target = _target(workspace_id)
        self._api = _win_apis()
        self._fingerprint: bytes | None = None

    def create_new(self) -> None:
        """Create once; refuse if a credential already exists, never replace it."""
        with _CreateMutex(self._workspace_id, self._api):
            if _read_root(self._target, self._api) is not None:
                raise WindowsCredentialPreviewError("fictional_credential_already_exists")
            secret = bytearray(new_root_secret())
            if len(secret) != _BYTES:
                raise WindowsCredentialPreviewError("fictional_credential_root_size_refused")
            try:
                blob = (ctypes.c_ubyte * _BYTES).from_buffer(secret)
                record = _CREDENTIAL()
                record.Type = _CRED_TYPE_GENERIC
                record.TargetName = self._target
                record.UserName = _USER
                record.Comment = "MedOrigin FICTIONAL developer preview only; not for patients"
                record.CredentialBlobSize = _BYTES
                record.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
                record.Persist = _CRED_PERSIST_LOCAL_MACHINE
                if not self._api.write(ctypes.byref(record), 0):
                    raise WindowsCredentialPreviewError(
                        "windows_protected_credential_create_refused"
                    )
                self._fingerprint = hashlib.sha256(secret).digest()
            finally:
                ctypes.memset(ctypes.addressof(blob), 0, _BYTES) if "blob" in locals() else None
                for i in range(len(secret)):
                    secret[i] = 0

    def open_existing(self) -> None:
        """Bind to one preexisting local key, never silently bootstrap on open."""
        secret = _read_root(self._target, self._api)
        if secret is None:
            raise WindowsCredentialPreviewError("fictional_credential_not_found")
        self._fingerprint = hashlib.sha256(secret).digest()

    def require_available(self) -> None:
        if self._fingerprint is None:
            raise KeyProviderUnavailableError("fictional_credential_not_open")
        secret = _read_root(self._target, self._api)
        if secret is None or hashlib.sha256(secret).digest() != self._fingerprint:
            raise KeyMaterialUnavailableError("fictional_credential_changed_or_unavailable")

    def _key(self, workspace_id: UUID) -> bytes:
        if workspace_id != self._workspace_id or self._fingerprint is None:
            raise KeyMaterialUnavailableError("fictional_credential_workspace_or_state_refused")
        secret = _read_root(self._target, self._api)
        if secret is None or hashlib.sha256(secret).digest() != self._fingerprint:
            raise KeyMaterialUnavailableError("fictional_credential_changed_or_unavailable")
        return secret

    @staticmethod
    def _checked_derived(value: object) -> bytes:
        if type(value) is not bytes or len(value) != _BYTES:
            raise KeyMaterialUnavailableError("fictional_derived_key_shape_refused")
        return value

    def key_for_version(self, *, workspace_id: UUID, key_version: int, salt: bytes) -> bytes:
        return self._checked_derived(
            derive_workspace_key(
                root_secret=self._key(workspace_id),
                workspace_id=workspace_id,
                key_version=key_version,
                salt=salt,
            )
        )

    def backup_key(self, *, workspace_id: UUID, backup_id: UUID, salt: bytes) -> bytes:
        return self._checked_derived(
            derive_backup_key(
                root_secret=self._key(workspace_id),
                workspace_id=workspace_id,
                backup_id=backup_id,
                salt=salt,
            )
        )

    def seal_key(self, *, workspace_id: UUID, salt: bytes) -> bytes:
        return self._checked_derived(
            derive_seal_key(
                root_secret=self._key(workspace_id),
                workspace_id=workspace_id,
                salt=salt,
            )
        )

    def delete_preview_secret(self, *, explicit_delete: bool = False) -> None:
        """Developer preview only; deletes credential, NEVER deletes workspace store."""
        if explicit_delete is not True:
            raise WindowsCredentialPreviewError("explicit_fictional_credential_delete_required")
        with _CreateMutex(self._workspace_id, self._api):
            present = _read_root(self._target, self._api)
            if present is None:
                raise WindowsCredentialPreviewError("fictional_credential_not_found")
            if self._fingerprint is None or hashlib.sha256(present).digest() != self._fingerprint:
                raise WindowsCredentialPreviewError("fictional_credential_delete_owner_refused")
            if not self._api.delete(self._target, _CRED_TYPE_GENERIC, 0):
                raise WindowsCredentialPreviewError("fictional_credential_delete_refused")
            self._fingerprint = None
