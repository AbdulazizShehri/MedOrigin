"""Owner Windows: actual Core #981 fictional protected audit VERIFY -> native D2.

Developer-only. A pre-existing invented audit record and externally retained
head are required. No create/forget action, patient data, EHR, network,
unreviewed sources, clinical release or production key selection.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from uuid import UUID

CORE981_SHA = "835dfca52858fb0dafa013b90185b47c758f11bb"
EXE_NAME = "medorigin-desktop-d2-native-egui.exe"
FLAG = "--synthetic-protected-audit-session-stdin"
DOMAIN = b"MedOrigin-D2-FICTIONAL-PROTECTED-AUDIT-V1\x00"
ENV_NONCE = "MEDORIGIN_D2_FICTIONAL_SESSION_NONCE"
ENV_KEY = "MEDORIGIN_D2_FICTIONAL_SESSION_KEY"
MAX_BYTES = 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "status", "operation", "verified_audit_events",
    "audit_head_sha256", "anchor_matched", "protected_credential_destroyed",
    "encrypted_workspace_store_preserved", "patient_data_admitted",
    "fhir_r4_conformance_validated", "clinical_use_authorized",
    "production_key_provider_selected", "publication_authorized",
})
FALSE_FIELDS = (
    "protected_credential_destroyed", "encrypted_workspace_store_preserved",
    "patient_data_admitted", "fhir_r4_conformance_validated",
    "clinical_use_authorized", "production_key_provider_selected",
    "publication_authorized",
)
CHILD = """
import sys
from pathlib import Path
root=Path(sys.argv[1])
sys.path[:0]=[str(root/'src'),str(root/'apps'/'workspace'/'src')]
from medscale.cli import main
raise SystemExit(main([
    'fhir','windows-audit-preview','verify',
    '--synthetic-only','--developer-preview',
    '--store-root',sys.argv[2],
    '--workspace-id',sys.argv[3],
    '--expected-head',sys.argv[4],
]))
"""


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_existing(path: Path, *, directory: bool) -> Path:
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("protected_audit_reparse_path_refused")
    for parent in path.parents:
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise ValueError("protected_audit_reparse_parent_refused")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError("protected_audit_path_missing") from exc
    if str(path.absolute()).casefold() != str(resolved).casefold():
        raise ValueError("protected_audit_path_alias_refused")
    if (resolved.is_dir() if directory else resolved.is_file()) is not True:
        raise ValueError("protected_audit_path_type_refused")
    return resolved


def _source(core: Path) -> Path:
    core = _safe_existing(core, directory=True)
    for rel in (
        "src/medscale/fhirkit/windows_protected_audit_preview.py",
        "src/medscale/fhirkit/windows_protected_key_provider.py",
        "apps/workspace/src/medscale_workspace/audit.py",
    ):
        _safe_existing(core / rel, directory=False)
    try:
        head = subprocess.run(
            ["git", "-C", str(core), "rev-parse", "HEAD"],
            capture_output=True, timeout=8, check=False,
        )
        dirty = subprocess.run(
            ["git", "-C", str(core), "status", "--porcelain=v1"],
            capture_output=True, timeout=8, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("protected_audit_core_git_unavailable") from exc
    if (
        head.returncode or dirty.returncode
        or head.stdout.strip() != CORE981_SHA.encode("ascii")
        or dirty.stdout.strip()
    ):
        raise ValueError("protected_audit_unreviewed_core_source")
    return core


def _canonical(raw: bytes) -> bytes:
    if not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("protected_audit_core_output_bounds")

    def no_duplicates(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise ValueError("protected_audit_duplicate_key")
            data[key] = value
        return data

    try:
        data = json.loads(raw, object_pairs_hook=no_duplicates)
        canonical = (
            json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("ascii")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ValueError("protected_audit_noncanonical_json") from exc
    if raw.endswith(b"\r\n") and raw.count(b"\r") == 1:
        raw = raw[:-2] + b"\n"
    if canonical != raw or type(data) is not dict or set(data) != FIELDS:
        raise ValueError("protected_audit_unreviewed_receipt_shape")
    if (
        data.get("schema") != "medorigin-core-windows-synthetic-protected-audit-preview/v1"
        or data.get("status") != "FICTIONAL_WINDOWS_PROTECTED_AUDIT_PREVIEW_ONLY"
        or data.get("operation") != "verify"
        or type(data.get("verified_audit_events")) is not int
        or data["verified_audit_events"] != 1
        or data.get("audit_head_sha256") is not None
        or data.get("anchor_matched") is not True
        or any(data.get(field) is not False for field in FALSE_FIELDS)
    ):
        raise ValueError("protected_audit_unapproved_operation_or_claim")
    return canonical


def _frame(raw: bytes, nonce: bytes, key: bytes) -> bytes:
    if not 0 < len(raw) <= MAX_BYTES or len(nonce) != 16 or len(key) != 32:
        raise ValueError("protected_audit_hmac_frame_bounds")
    signed = DOMAIN + nonce + len(raw).to_bytes(4, "big") + raw
    return DOMAIN + nonce + hmac.new(key, signed, hashlib.sha256).digest() + raw


def launch(core: Path, store: Path, workspace_id: str, anchor: str,
           exe: Path, exe_sha: str, *, qa_auto_close: bool,
           qa_uia: bool = False) -> None:
    if sys.platform != "win32":
        raise ValueError("protected_audit_windows_only")
    if qa_auto_close and qa_uia:
        raise ValueError("protected_audit_mutually_exclusive_qa_modes")
    if not SHA.fullmatch(anchor) or not SHA.fullmatch(exe_sha):
        raise ValueError("protected_audit_hash_format_refused")
    try:
        identity = UUID(workspace_id)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("protected_audit_identity_format_refused") from exc
    if identity.version != 4 or str(identity) != workspace_id:
        raise ValueError("protected_audit_identity_not_canonical_v4")
    store = _safe_existing(store, directory=True)
    if store.name != "medorigin-fictional-workspace-preview":
        raise ValueError("protected_audit_only_explicit_fictional_folder")
    core = _source(core)
    if exe.name != EXE_NAME:
        raise ValueError("protected_audit_unreviewed_native_exe_name")
    exe = _safe_existing(exe, directory=False)
    if _sha(exe) != exe_sha:
        raise ValueError("protected_audit_native_exe_changed")
    try:
        verified = subprocess.run(
            [sys.executable, "-B", "-c", CHILD, str(core), str(store),
             workspace_id, anchor],
            cwd=exe.parent, capture_output=True, timeout=50, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("protected_audit_core_verify_subprocess_refused") from exc
    if verified.returncode != 0 or verified.stderr:
        raise ValueError("protected_audit_core_anchor_or_credential_refused")
    receipt = _canonical(verified.stdout)
    nonce = secrets.token_bytes(16)
    key = secrets.token_bytes(32)
    framed = _frame(receipt, nonce, key)
    if _sha(exe) != exe_sha or _source(core) != core:
        raise ValueError("protected_audit_source_or_gui_changed")
    env = {**os.environ, ENV_NONCE: nonce.hex(), ENV_KEY: key.hex()}
    if qa_uia:
        uia = _safe_existing(
            Path(__file__).resolve().parent.parent
            / "tests/windows-protected-audit-readonly-uia.ps1",
            directory=False,
        )
        with TemporaryDirectory(prefix="medorigin-protected-audit-uia-", dir=exe.parent) as temp:
            live = Path(temp) / "redacted-fictional-audit-status.json"
            frame = Path(temp) / "fictional-audit-session-frame.bin"
            live.write_bytes(receipt)
            frame.write_bytes(framed)
            try:
                checked = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive",
                     "-File", str(uia), "-ExePath", str(exe),
                     "-ExpectedExeSha256", exe_sha,
                     "-LiveReceiptPath", str(live),
                     "-ExpectedReceiptSha256", hashlib.sha256(receipt).hexdigest(),
                     "-SessionFramePath", str(frame)],
                    cwd=exe.parent, env=env,
                    capture_output=True, timeout=75, check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValueError("protected_audit_real_native_uia_unavailable") from exc
            if (
                checked.returncode != 0
                or b"WINDOWS_REAL_CORE981_PROTECTED_AUDIT_STATUS_UIA_PASS_NONCLINICAL"
                not in checked.stdout
            ):
                raise ValueError("protected_audit_real_native_uia_refused")
        print("CORE981_PROTECTED_AUDIT_SOURCE_TO_REAL_NATIVE_UIA_PASS_NONCLINICAL")
        return
    try:
        child = subprocess.Popen(
            [str(exe), FLAG], cwd=exe.parent, env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if child.stdin is None:
            raise ValueError("protected_audit_native_stdin_missing")
        child.stdin.write(framed)
        child.stdin.close()
    except (OSError, BrokenPipeError) as exc:
        raise ValueError("protected_audit_native_handoff_refused") from exc
    time.sleep(1.1)
    if child.poll() is not None:
        raise ValueError("protected_audit_native_gui_stopped")
    if qa_auto_close:
        child.terminate()
        try:
            child.wait(timeout=6)
        except subprocess.TimeoutExpired as exc:
            child.kill()
            raise ValueError("protected_audit_native_cleanup_failed") from exc
    print("PROTECTED_FICTIONAL_AUDIT_COLD_REOPEN_TO_NATIVE_HMAC_STATUS_PASS_NONCLINICAL")
    print("REDACTED_AUDIT_VERIFY_RECEIPT_SHA256=" + hashlib.sha256(receipt).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-source", type=Path, required=True)
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--native-exe", type=Path, required=True)
    parser.add_argument("--native-sha256", required=True)
    parser.add_argument("--qa-auto-close", action="store_true")
    parser.add_argument("--qa-uia", action="store_true")
    try:
        args = parser.parse_args()
        launch(args.core_source, args.store_root, args.workspace_id,
               args.expected_head, args.native_exe, args.native_sha256,
               qa_auto_close=args.qa_auto_close, qa_uia=args.qa_uia)
    except (ValueError, OSError):
        print("PROTECTED_FICTIONAL_AUDIT_NATIVE_NO_GO", file=sys.stderr)
        raise SystemExit(2) from None
