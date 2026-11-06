"""Real owner Windows synthetic audit-only protected Workspace lifecycle CLI.

Zero PHI/EHR. Real Windows Credential Manager, AES-GCM SQLite, audit-chain
anchor and fresh-process reopening. Every generated task credential is
destroyed in a finally block, while a task-only temp dir holds the store.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from medscale_workspace.keyprovider import resolve_platform_key_provider

from medscale.cli import main as public_cli
from medscale.fhirkit.windows_protected_audit_preview import (
    WindowsAuditPreviewError,
    run_windows_audit_preview,
)
from medscale.fhirkit.windows_protected_key_provider import (
    WindowsCredentialPreviewError,
    WindowsProtectedSyntheticKeyProvider,
)

_PRIVATE = "SECRET_SHOULD_NOT_LEAK_IN_CLI"


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "medorigin-fictional-workspace-preview"
    root.mkdir()
    return root


def _tokens(op: str, root: Path, wid, sha: str | None = None) -> list[str]:
    tokens = [
        "fhir",
        "windows-audit-preview",
        op,
        "--synthetic-only",
        "--developer-preview",
        "--store-root",
        str(root),
        "--workspace-id",
        str(wid),
    ]
    if op != "create":
        tokens.extend(["--expected-head", sha or "0" * 64])
    if op == "forget":
        tokens.append("--acknowledge-irreversible-key-loss")
    return tokens


def _cleanup_key(wid) -> None:
    """Delete only this random test UUID target if still present."""
    try:
        provider = WindowsProtectedSyntheticKeyProvider(
            wid, synthetic_only=True, developer_preview=True
        )
        provider.open_existing()
    except WindowsCredentialPreviewError as exc:
        if str(exc) != "fictional_credential_not_found":
            raise
    else:
        provider.delete_preview_secret(explicit_delete=True)


def _subprocess_cli(tokens: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    repo = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(repo / "src"), str(repo / "apps" / "workspace" / "src")]
    )
    env["PYTHONNOUSERSITE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys;from medscale.cli import main;raise SystemExit(main(sys.argv[1:]))",
            *tokens,
        ],
        capture_output=True,
        text=True,
        timeout=35,
        env=env,
        cwd=root,
        check=False,
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Owner Windows vault required")
def test_public_cli_real_user_workflow_cross_process_independently_anchored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _root(tmp_path)
    wid = uuid4()
    created = False
    try:
        assert public_cli(_tokens("create", root, wid)) == 0
        created = True
        output = capsys.readouterr()
        assert output.err == ""
        receipt = json.loads(output.out)
        assert receipt["schema"] == "medorigin-core-windows-synthetic-protected-audit-preview/v1"
        assert receipt["verified_audit_events"] == 1
        assert receipt["operation"] == "create"
        assert receipt["patient_data_admitted"] is False
        assert receipt["clinical_use_authorized"] is False
        assert receipt["production_key_provider_selected"] is False
        head = receipt["audit_head_sha256"]
        assert len(head) == 64 and head.isascii()

        # New process with fresh module imports. No secret in args, env, disk
        # or report, only the independent non-secret audit SHA anchor.
        verified = _subprocess_cli(_tokens("verify", root, wid, head), root)
        assert verified.returncode == 0, verified.stderr[:250]
        assert verified.stderr == ""
        vr = json.loads(verified.stdout)
        assert vr["operation"] == "verify"
        assert vr["audit_head_sha256"] is None
        assert vr["anchor_matched"] is True
        assert vr["verified_audit_events"] == 1

        altered = ("0" if head[0] != "0" else "1") + head[1:]
        wrong = _subprocess_cli(_tokens("verify", root, wid, altered), root)
        assert wrong.returncode == 2 and wrong.stdout == ""
        assert "encrypted_fictional_protected_workspace_unavailable" in wrong.stderr
        assert _PRIVATE not in wrong.stderr

        # Existing protected credential and store must NOT be overwritten by
        # an accidental second create. No partial stdout on refusal.
        assert public_cli(_tokens("create", root, wid)) == 2
        assert capsys.readouterr().out == ""

        # No implicit destruction without the explicit exact acknowledgment.
        nonack = _tokens("forget", root, wid, head)[:-1]
        assert public_cli(nonack) == 2
        assert capsys.readouterr().out == ""

        deleted = _subprocess_cli(_tokens("forget", root, wid, head), root)
        assert deleted.returncode == 0, deleted.stderr[:250]
        lost = json.loads(deleted.stdout)
        assert lost["protected_credential_destroyed"] is True
        assert lost["encrypted_workspace_store_preserved"] is True
        created = False
        assert (root / f"{wid}.workspace.sqlite3").is_file()

        missing = _subprocess_cli(_tokens("verify", root, wid, head), root)
        assert missing.returncode == 2 and missing.stdout == ""
        with pytest.raises(WindowsCredentialPreviewError, match="not_found"):
            WindowsProtectedSyntheticKeyProvider(
                wid, synthetic_only=True, developer_preview=True
            ).open_existing()
        assert resolve_platform_key_provider().capabilities.available is False
        combined = (
            verified.stdout
            + verified.stderr
            + wrong.stdout
            + wrong.stderr
            + deleted.stdout
            + deleted.stderr
            + missing.stdout
            + missing.stderr
        )
        for forbidden in (_PRIVATE, str(root), str(wid), "MedOrigin/FictionalDeveloperPreview"):
            assert forbidden not in combined
    finally:
        if created:
            _cleanup_key(wid)


@pytest.mark.parametrize(
    "tokens",
    [
        [],
        ["create"],
        ["--synthetic-only", "--developer-preview"],
        ["forget", "--synthetic-only"],
        ["create", "--developer-preview", "--synthetic-only"],
        ["verify", "--synthetic-only", "--developer-preview", "--store-root", _PRIVATE],
    ],
)
def test_bad_public_flags_never_echo_user_supplied_data(
    tokens: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert public_cli(["fhir", "windows-audit-preview", *tokens]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "exact_fictional_protected_flags_required" in result.err
    assert _PRIVATE not in result.err


def test_public_help_is_explicitly_not_clinical(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert public_cli(["fhir", "windows-audit-preview", "--help"]) == 0
    output = capsys.readouterr().out
    assert "forget" in output
    assert "NO patient" in output or "No patient" in output
    assert "production" in output


def test_bad_action_and_root_rejected_prior_to_open(tmp_path: Path) -> None:
    root = _root(tmp_path)
    wid = uuid4()
    bad_root = tmp_path / "other-user-folder"
    bad_root.mkdir()
    with pytest.raises(WindowsAuditPreviewError, match="store_root_refused"):
        run_windows_audit_preview(
            "create", bad_root, wid, synthetic_only=True, developer_preview=True
        )
    with pytest.raises(WindowsAuditPreviewError, match="action_refused"):
        run_windows_audit_preview(
            "diagnose", root, wid, synthetic_only=True, developer_preview=True
        )
    with pytest.raises(WindowsAuditPreviewError, match="opt_in_required"):
        run_windows_audit_preview("create", root, wid, synthetic_only=False, developer_preview=True)
    assert list(root.iterdir()) == []


@pytest.mark.skipif(sys.platform != "win32", reason="Windows protected OS key required")
def test_verify_missing_does_not_create_credential_or_workspace(tmp_path: Path) -> None:
    root = _root(tmp_path)
    wid = uuid4()
    with pytest.raises(WindowsAuditPreviewError, match="store_missing"):
        run_windows_audit_preview(
            "verify", root, wid, "0" * 64, synthetic_only=True, developer_preview=True
        )
    assert list(root.iterdir()) == []
    with pytest.raises(WindowsCredentialPreviewError, match="not_found"):
        WindowsProtectedSyntheticKeyProvider(
            wid, synthetic_only=True, developer_preview=True
        ).open_existing()
