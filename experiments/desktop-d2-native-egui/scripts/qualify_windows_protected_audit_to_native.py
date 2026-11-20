"""Owner Windows: real Credential Manager fictional Core audit -> native UIA.

Task-owned random UUID, one imaginary event, AES-GCM SQLite cold reopen;
wrong external anchor refusal; *explicit* credential revocation/cleanup.
Never use real patient files, EHR, protected production key or publication.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import launch_windows_protected_audit_readonly as bridge

RUN = """
import sys
from pathlib import Path
source=Path(sys.argv[1])
sys.path[:0]=[str(source/'src'),str(source/'apps'/'workspace'/'src')]
from medscale.cli import main
raise SystemExit(main(sys.argv[2:]))
"""


def core_call(
    core: Path, operation: str, root: Path, identity: str, head: str | None = None
) -> subprocess.CompletedProcess[bytes]:
    tokens = [
        "fhir",
        "windows-audit-preview",
        operation,
        "--synthetic-only",
        "--developer-preview",
        "--store-root",
        str(root),
        "--workspace-id",
        identity,
    ]
    if operation != "create":
        tokens.extend(["--expected-head", head or ("0" * 64)])
    if operation == "forget":
        tokens.append("--acknowledge-irreversible-key-loss")
    return subprocess.run(
        [sys.executable, "-B", "-c", RUN, str(core), *tokens],
        cwd=root,
        capture_output=True,
        timeout=45,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def run(core: Path, exe: Path, sha: str) -> None:
    if sys.platform != "win32":
        raise ValueError("real_owner_windows_required")
    core = bridge._source(core)
    exe = bridge._safe_existing(exe, directory=False)
    if exe.name != bridge.EXE_NAME or bridge._sha(exe) != sha:
        raise ValueError("unreviewed_native_binary")
    checkout = Path(__file__).resolve().parents[3]
    with TemporaryDirectory(prefix="medorigin-audit-only-owner-qa-", dir=checkout) as directory:
        root = Path(directory) / "medorigin-fictional-workspace-preview"
        root.mkdir()
        identity = str(uuid4())
        head = None
        created = False
        destroyed = False
        try:
            first = core_call(core, "create", root, identity)
            if first.returncode != 0 or first.stderr:
                raise ValueError("actual_protected_audit_create_refused")
            # A successful Core CLI create ALREADY stores a task-only Windows
            # credential. Attempt cleanup even if parsing the report fails.
            created = True
            try:
                created_result = json.loads(first.stdout)
            except (UnicodeError, ValueError) as exc:
                raise ValueError("actual_protected_audit_create_json_refused") from exc
            if (
                type(created_result) is not dict
                or created_result.get("operation") != "create"
                or type(created_result.get("verified_audit_events")) is not int
                or created_result["verified_audit_events"] != 1
                or created_result.get("clinical_use_authorized") is not False
                or created_result.get("patient_data_admitted") is not False
                or not isinstance(created_result.get("audit_head_sha256"), str)
                or not bridge.SHA.fullmatch(created_result["audit_head_sha256"])
            ):
                raise ValueError("actual_protected_audit_create_claim_refused")
            head = created_result["audit_head_sha256"]
            # A DIFFERENT Core process gets the protected OS credential,
            # reopens the original encrypted database and verifies its
            # independently held head before native startup/HMAC admission.
            bridge.launch(core, root, identity, head, exe, sha, qa_auto_close=True)
            bridge.launch(core, root, identity, head, exe, sha, qa_auto_close=False, qa_uia=True)
            wrong = ("0" if head[0] != "0" else "1") + head[1:]
            try:
                bridge.launch(core, root, identity, wrong, exe, sha, qa_auto_close=True)
            except ValueError as exc:
                if str(exc) != "protected_audit_core_anchor_or_credential_refused":
                    raise
            else:
                raise ValueError("wrong_external_audit_head_accepted")
            revoked = core_call(core, "forget", root, identity, head)
            if revoked.returncode != 0 or revoked.stderr:
                raise ValueError("task_credential_revocation_failed")
            result = json.loads(revoked.stdout)
            if (
                result.get("operation") != "forget"
                or result.get("protected_credential_destroyed") is not True
                or result.get("encrypted_workspace_store_preserved") is not True
                or result.get("patient_data_admitted") is not False
            ):
                raise ValueError("task_credential_revocation_claim_refused")
            destroyed = True
            missing = core_call(core, "verify", root, identity, head)
            if missing.returncode != 2 or missing.stdout:
                raise ValueError("deleted_task_key_still_verified")
            print("REAL_CORE981_OS_PROTECTED_FICTIONAL_AUDIT_NATIVE_HMAC_AND_REVOCATION_PASS")
        finally:
            if created and not destroyed:
                # Strictly cleanup the specific task-only randomly generated
                # Credential Manager UUID. Never touch another user's secret.
                try:
                    attempt = core_call(core, "forget", root, identity, head)
                    if attempt.returncode != 0:
                        sys.path[:0] = [
                            str(core / "src"),
                            str(core / "apps" / "workspace" / "src"),
                        ]
                        from medscale.fhirkit.windows_protected_key_provider import (
                            WindowsProtectedSyntheticKeyProvider,
                        )

                        provider = WindowsProtectedSyntheticKeyProvider(
                            UUID(identity), synthetic_only=True, developer_preview=True
                        )
                        provider.open_existing()
                        provider.delete_preview_secret(explicit_delete=True)
                except Exception as exc:
                    raise ValueError("task_credential_cleanup_unverified") from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-source", type=Path, required=True)
    parser.add_argument("--native-exe", type=Path, required=True)
    parser.add_argument("--native-sha256", required=True)
    try:
        args = parser.parse_args()
        run(args.core_source, args.native_exe, args.native_sha256)
    except (OSError, ValueError):
        print("REAL_PROTECTED_FICTIONAL_AUDIT_NATIVE_OWNER_QA_NO_GO", file=sys.stderr)
        raise SystemExit(2) from None
