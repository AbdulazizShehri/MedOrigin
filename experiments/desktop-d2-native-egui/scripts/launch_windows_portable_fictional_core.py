#!/usr/bin/env python3
"""Run private fictional-only MedOrigin D2 kit without Git or Wheel directories.

The prepared kit contains exactly 290 original reviewed Core+Workspace pure
Python files. The existing Windows Python/crypto runtime remains external and
NOT supply-chain attested. This is NOT a clinical application or OS sandbox.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

from fictional_session_frame import (
    KEY_ENV,
    NONCE_ENV,
    SESSION_FLAG,
    frame_one_time_fictional_core,
    fresh_ephemeral_session,
)
from launch_windows_encrypted_fictional_preview import (
    QA_WINDOW_TIMEOUT_SECONDS,
    WINDOW_TIMEOUT_SECONDS,
    _qa_close_exact_owned_window,
)
from portable_core_tree import APPROVED_TREE_SHA256, attest_portable_core_tree
from qualify_windows_encrypted_readback_native_gui import PROJECTION_SHA, sha
from supervise_windows_encrypted_core_job import (
    PERSISTENT_CREATE_MARKER,
    execute_encrypted_source_under_job,
)

SCHEMA = "medorigin-d2-private-portable-fictional-core-windows/v1"
PINNED_COMMIT = "8e5ed5430f4ab2ebc8981c52c67234023382954b"
EXPORTER_SHA256 = "12e9cdd5def9c794aafa975d232062a456eec6c558728ac119868fb876505a7c"
PERSISTENT_PROJECTION_SHA256 = "3673eb77b2dbef25fd6cb33d9c345d2f37d38a86bcf1652ed9defae4da139243"
GUI_NAME = "medorigin-desktop-d2-native-egui.exe"
RUNTIME_FILES = (
    "scripts/launch_windows_portable_fictional_core.py",
    "scripts/fictional_session_frame.py",
    "scripts/windows_fictional_persistent_vault.py",
    "scripts/portable_core_tree.py",
    "scripts/supervise_windows_encrypted_core_job.py",
    "scripts/qualify_windows_job_subtree.py",
    "scripts/synthetic_encrypted_readback_projection.py",
    "scripts/launch_windows_encrypted_fictional_preview.py",
    "scripts/qualify_windows_encrypted_readback_native_gui.py",
    "tests/windows-encrypted-core-readback-uia.ps1",
    "fixtures/core/encrypted-readback-projection.json",
    "fixtures/core/encrypted-persistent-readback-projection.json",
    f"native/{GUI_NAME}",
)
SUCCESS = "WINDOWS_PORTABLE_INSTALLED_FICTIONAL_CORE_NO_GIT_NATIVE_D2_PASS_NOT_CLINICAL"
REFUSAL = "WINDOWS_PORTABLE_FICTIONAL_CORE_NATIVE_D2_NO_GO"


def attest_kit(root: Path) -> tuple[Path, Path, Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("portable_private_bundle_root_refused")
    expected_root = {"manifest.json", "core", "scripts", "tests", "fixtures", "native"}
    if {x.name for x in root.iterdir()} != expected_root:
        raise ValueError("portable_private_bundle_extra_root_path")
    document_path = root / "manifest.json"
    if (
        document_path.is_symlink()
        or not document_path.is_file()
        or document_path.stat().st_size > 4000
    ):
        raise ValueError("private_bundle_manifest_missing_or_oversized")
    manifest = json.loads(document_path.read_bytes())
    if (
        not isinstance(manifest, dict)
        or set(manifest)
        != {
            "schema",
            "source_commit",
            "core_sha256",
            "source_file_count",
            "generated_by",
            "production_or_clinical_use_authorized",
            "sender_or_session_authenticated",
            "os_network_egress_confined",
            "files_sha256",
        }
        or manifest["schema"] != SCHEMA
        or manifest["source_commit"] != PINNED_COMMIT
        or manifest["core_sha256"] != APPROVED_TREE_SHA256
        or manifest["source_file_count"] != 290
        or manifest["generated_by"] != "offline_source_attested_developer_tool"
        or manifest["production_or_clinical_use_authorized"] is not False
        or manifest["sender_or_session_authenticated"] is not False
        or manifest["os_network_egress_confined"] is not False
        or not isinstance(manifest["files_sha256"], dict)
        or set(manifest["files_sha256"]) != set(RUNTIME_FILES)
    ):
        raise ValueError("portable_fictional_manifest_contract_refused")
    # No unexpected executable, additional payload or symlink is allowed.
    for folder_name in ("scripts", "tests", "fixtures", "native"):
        folder = root / folder_name
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError("portable_fictional_runtime_directory_refused")
    all_files = set()
    for folder_name in ("scripts", "tests", "fixtures", "native"):
        for entry in (root / folder_name).rglob("*"):
            if entry.is_symlink():
                raise ValueError("portable_fictional_runtime_symlink_refused")
            if entry.is_file():
                all_files.add(entry.relative_to(root).as_posix())
            elif not entry.is_dir():
                raise ValueError("portable_fictional_runtime_special_file_refused")
    if all_files != set(RUNTIME_FILES):
        raise ValueError("portable_fictional_runtime_unapproved_files")
    for name in RUNTIME_FILES:
        path = root / name
        claimed = manifest["files_sha256"][name]
        if (
            not isinstance(claimed, str)
            or not re.fullmatch(r"[0-9a-f]{64}", claimed)
            or sha(path) != claimed
        ):
            raise ValueError("portable_runtime_or_gui_checksum_refused")
    exporter = root / "scripts/synthetic_encrypted_readback_projection.py"
    fixture = root / "fixtures/core/encrypted-readback-projection.json"
    if sha(exporter) != EXPORTER_SHA256 or sha(fixture) != PROJECTION_SHA:
        raise ValueError("portable_core_exporter_or_projection_changed")
    persistent_fixture = root / "fixtures/core/encrypted-persistent-readback-projection.json"
    if sha(persistent_fixture) != PERSISTENT_PROJECTION_SHA256:
        raise ValueError("portable_persistent_fictional_projection_changed")
    attest_portable_core_tree(root / "core")
    return root / "native" / GUI_NAME, exporter, fixture


def _launch_gui(
    gui: Path,
    raw: bytes,
    work: Path,
    *,
    qa_auto_close: bool,
    nonce: bytes,
    key: bytes,
) -> None:
    system = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    env = {
        KEY_ENV: key.hex(),
        NONCE_ENV: nonce.hex(),
        "SYSTEMROOT": str(system),
        "WINDIR": str(system),
        "PATH": os.pathsep.join((str(gui.parent), str(system / "System32"))),
        "TEMP": str(work),
        "TMP": str(work),
    }
    seen = threading.Event()
    process = None
    try:
        process = subprocess.Popen(
            [str(gui), SESSION_FLAG],
            cwd=work,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        if qa_auto_close:
            threading.Thread(
                target=_qa_close_exact_owned_window,
                args=(process.pid, seen),
                daemon=True,
                name="private-portable-fictional-native-window-close-QA",
            ).start()
        process.communicate(
            input=raw,
            timeout=(QA_WINDOW_TIMEOUT_SECONDS if qa_auto_close else WINDOW_TIMEOUT_SECONDS),
        )
        if process.returncode != 0 or (qa_auto_close and not seen.is_set()):
            raise ValueError("portable_fictional_native_gui_close_refused")
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate(timeout=5)


def _qa_native_clicks(
    root: Path,
    gui: Path,
    work: Path,
    raw: bytes,
    framed: bytes,
    nonce: bytes,
    key: bytes,
    *,
    persistent: bool = False,
) -> None:
    receipt = work / "reviewed-portable-core-projection.json"
    if receipt.exists() or receipt.is_symlink():
        raise ValueError("portable_core_stale_receipt_refused")
    receipt.write_bytes(raw)
    session_path = work / "fictional-qa-one-time-session-frame.bin"
    if session_path.exists() or session_path.is_symlink():
        raise ValueError("session_frame_path_preexisting")
    session_path.write_bytes(framed)
    observer = root / "tests/windows-encrypted-core-readback-uia.ps1"
    system = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(observer),
            "-ExePath",
            str(gui),
            "-ExpectedSha256",
            sha(gui),
            ("-PersistentQaReceiptPath" if persistent else "-LiveReceiptPath"),
            str(receipt),
            "-SessionFramePath",
            str(session_path),
        ],
        cwd=work,
        capture_output=True,
        timeout=85,
        check=False,
        env={
            KEY_ENV: key.hex(),
            NONCE_ENV: nonce.hex(),
            "SYSTEMROOT": str(system),
            "WINDIR": str(system),
            "PATH": str(system / "System32"),
            "TEMP": str(work),
            "TMP": str(work),
        },
    )
    marker = (
        b"WINDOWS_REAL_ENCRYPTED_CORE_READBACK_THREE_RESOURCES_LINK_AND_BACK_UIA_PASS_NOT_CLINICAL"
    )
    if result.returncode != 0 or marker not in result.stdout:
        raise ValueError("portable_fictional_installed_core_gui_uia_refused")
    print("WINDOWS_PORTABLE_FICTIONAL_CORE_TO_NATIVE_D2_GRAPH_UIA_PASS_NONCLINICAL")


def launch(args: argparse.Namespace) -> None:
    if sys.platform != "win32":
        raise ValueError("windows_host_required")
    if args.python.is_symlink() or args.crypto_site.is_symlink():
        raise ValueError("unreviewed_runtime_reparse_point")
    python = args.python.resolve(strict=True)
    site = args.crypto_site.resolve(strict=True)
    if (
        not python.is_file()
        or not site.is_dir()
        or python.name.lower() != "python.exe"
        or not re.fullmatch(r"[0-9a-fA-F]{64}", args.python_sha)
        or sha(python) != args.python_sha.lower()
        or python != Path(sys.executable).resolve(strict=True)
    ):
        raise ValueError("portable_fictional_runtime_python_refused")
    root = Path(__file__).resolve().parent.parent
    gui, exporter, fixture = attest_kit(root)
    persistent_qa_root = getattr(args, "fictional_persistent_qa_root", None)
    ensure_demo = getattr(args, "ensure_fictional_demo", False)
    if ensure_demo and persistent_qa_root is None:
        raise ValueError("fictional_demo_requires_explicit_fixed_vault_path")
    if persistent_qa_root is not None:
        exporter = root / "scripts/windows_fictional_persistent_vault.py"
        fixture = root / "fixtures/core/encrypted-persistent-readback-projection.json"
    expected_sha = (
        PERSISTENT_PROJECTION_SHA256 if persistent_qa_root is not None else PROJECTION_SHA
    )
    with TemporaryDirectory(prefix="medorigin-portable-fictional-dev-") as temp:
        work = Path(temp).resolve()
        if ensure_demo and persistent_qa_root is not None and not persistent_qa_root.exists():
            created = execute_encrypted_source_under_job(
                python=python,
                core=None,
                site=site,
                exporter=exporter,
                work=work,
                installed_site=root / "core",
                persistent_create_root=persistent_qa_root,
            )
            if created != PERSISTENT_CREATE_MARKER:
                raise ValueError("first_run_fictional_vault_initialization_refused")
            print("WINDOWS_PRIVATE_FICTIONAL_FIRST_RUN_VAULT_CREATED_NOT_CLINICAL")
            # A new independent Core process reopens the actual encrypted
            # persistent test vault; no fallback to overwrite on error.
            first_output = work / "synthetic-core-readback-job-only.json"
            if first_output.is_symlink() or not first_output.is_file():
                raise ValueError("first_run_fictional_job_marker_disappeared")
            first_output.unlink()
        raw = execute_encrypted_source_under_job(
            python=python,
            core=None,
            site=site,
            exporter=exporter,
            work=work,
            installed_site=root / "core",
            persistent_qa_root=persistent_qa_root,
        )
        if (
            len(raw) != (1215 if persistent_qa_root is not None else 1164)
            or raw != fixture.read_bytes()
            or hashlib.sha256(raw).hexdigest() != expected_sha
        ):
            raise ValueError("portable_source_installed_encrypted_readback_refused")
        # Per-launch, source-bound MAC with independent 128-bit nonce and
        # 256-bit key from the OS CSPRNG; never persisted to the kit or logs.
        # The shared environment secret is a QA owner-bound control, NOT
        # production sender authentication, key custody or OS secrecy.
        nonce, key = fresh_ephemeral_session()
        framed = frame_one_time_fictional_core(raw, nonce, key)
        if args.qa_uia:
            _qa_native_clicks(
                root,
                gui,
                work,
                raw,
                framed,
                nonce,
                key,
                persistent=persistent_qa_root is not None,
            )
        else:
            _launch_gui(
                gui,
                framed,
                work,
                qa_auto_close=args.qa_auto_close,
                nonce=nonce,
                key=key,
            )
    attest_kit(root)
    if sha(python) != args.python_sha.lower():
        raise ValueError("portable_runtime_python_changed_after_close")
    print(SUCCESS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--crypto-site", type=Path, required=True)
    parser.add_argument("--python-sha", type=str, required=True)
    parser.add_argument(
        "--fictional-persistent-qa-root",
        type=Path,
        help="EXPLICIT fixed-name, DPAPI-protected fictional QA vault only; never PHI",
    )
    parser.add_argument(
        "--ensure-fictional-demo",
        action="store_true",
        help=(
            "Opt in: create only if absent, then independently cold-reopen the "
            "same fixed fictional test vault; never replace an existing vault"
        ),
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--qa-auto-close",
        action="store_true",
        help="Close only the owned fictional native window in QA",
    )
    modes.add_argument(
        "--qa-uia",
        action="store_true",
        help="Click exact recovered fictional Core using real Windows UIA",
    )
    try:
        launch(parser.parse_args())
    except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError):
        print(REFUSAL, file=sys.stderr)
        raise SystemExit(2) from None
