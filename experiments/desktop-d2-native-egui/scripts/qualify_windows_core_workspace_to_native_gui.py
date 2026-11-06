#!/usr/bin/env python3
"""Real fixed-source Core encrypted synthetic Workspace -> native Windows D2 QA.

Private nonclinical only. Uses a source-pinned checkout, fixed CLI flags,
and temporary output with no resource payload. Windows network egress is NOT
OS-blocked here, and this is NOT an authenticated in-GUI Core worker.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

CORE_SHA = "0351b667ec910480fd61c30f18cf3bb0dd0ae842"
RECEIPT_SHA = "25acdb57db8ca3f11d353cf311167973760caaa95bb64de7339fe21e3b05cc2e"
SUCCESS = "WINDOWS_LIVE_CORE_ENCRYPTED_WORKSPACE_TO_REAL_D2_NATIVE_GUI_PASS_NOT_CLINICAL"
SOURCE_SECTIONS = (
    ("src/medscale", 120, 450),
    ("apps/workspace/src/medscale_workspace", 25, 100),
)

FIXED_CLI = (
    "import sys,importlib.metadata as md;"
    "sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]];"
    "assert md.version('cryptography')=='50.0.1';"
    "assert md.version('cffi')=='2.1.1';"
    "from medscale.cli.fhir import main;"
    "raise SystemExit(main(['workspace-demo','--synthetic-only','--ephemeral-demo']))"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(core: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(core), *args],
        capture_output=True,
        check=True,
        timeout=12,
    )
    if len(result.stdout) > 1_000_000:
        raise ValueError("core_git_evidence_too_large")
    return result.stdout


def verify_pinned_core(core: Path) -> None:
    if core.is_symlink() or not core.is_dir():
        raise ValueError("reviewed_core_source_checkout_missing")
    if git(core, "rev-parse", "HEAD").decode("ascii").strip() != CORE_SHA:
        raise ValueError("reviewed_core_source_revision_not_matched")
    if git(core, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("reviewed_core_checkout_not_clean")
    for section, minimum, maximum in SOURCE_SECTIONS:
        inventory = git(core, "ls-files", "-z", "--", section)
        tracked = {name.decode("utf-8") for name in inventory.split(b"\x00") if name}
        if not minimum <= len(tracked) <= maximum:
            raise ValueError("core_workspace_tracked_source_inventory_refused")
        relative = Path(section)
        package_dir = core / relative
        seen = set()
        for item in package_dir.rglob("*"):
            if item.is_symlink():
                raise ValueError("core_workspace_source_symlink_refused")
            # Git ignores __pycache__ by default. Python -B suppresses writes
            # but DOES NOT refuse existing compiled bytecode at import time.
            if item.is_dir() and item.name.lower() == "__pycache__":
                raise ValueError("unreviewed_ignored_python_bytecode_refused")
            if item.is_file():
                path = item.relative_to(core).as_posix()
                if item.suffix.lower() in (
                    ".py",
                    ".pyc",
                    ".pyo",
                    ".pyd",
                    ".pth",
                    ".dll",
                    ".so",
                    ".dylib",
                ):
                    if path not in tracked or item.suffix.lower() != ".py":
                        raise ValueError("unreviewed_python_startup_or_native_source")
                    seen.add(path)
        expected_python = {p for p in tracked if p.endswith(".py")}
        if seen != expected_python:
            raise ValueError("core_workspace_python_source_files_missing")
    print("WINDOWS_SOURCE_FIXED_CORE_WORKSPACE_GIT_INVENTORY_ATTESTED")


def strip_platform_one_newline(payload: bytes) -> bytes:
    """Remove exactly one Python print newline (Windows CRLF or POSIX LF).

    Do not strip other whitespace, JSON suffixes or arbitrary extra newlines.
    The caller must still demand byte-for-byte canonical source equality.
    """
    if payload.endswith(b"\r\n"):
        return payload[:-2]
    if payload.endswith(b"\n"):
        return payload[:-1]
    raise ValueError("windows_core_cli_single_terminal_newline_missing")


def qualify(args: argparse.Namespace) -> None:
    if sys.platform != "win32":
        raise ValueError("real_windows_desktop_required")
    core = args.core_source
    python = args.python
    binary = args.native_gui
    if (
        core.is_symlink()
        or python.is_symlink()
        or binary.is_symlink()
        or not python.is_file()
        or python.name.lower() != "python.exe"
        or not binary.is_file()
        or binary.name != "medorigin-desktop-d2-native-egui.exe"
    ):
        raise ValueError("python_or_d2_binary_identity_refused")
    core = core.resolve(strict=True)
    python = python.resolve(strict=True)
    binary = binary.resolve(strict=True)
    if digest(python) != args.python_sha256.lower() or digest(binary) != args.native_sha256.lower():
        raise ValueError("python_or_native_d2_executable_sha_refused")
    if not args.site.is_dir() or args.site.is_symlink():
        raise ValueError("system_installed_crypto_site_directory_refused")
    verify_pinned_core(core)
    source_receipt = (
        Path(__file__).resolve().parent.parent / "fixtures/core/workspace-ephemeral-demo.json"
    )
    if source_receipt.is_symlink() or digest(source_receipt) != RECEIPT_SHA:
        raise ValueError("source_compiled_encrypted_workspace_receipt_modified")
    observer = (
        Path(__file__).resolve().parent.parent / "tests/windows-encrypted-workspace-native-uia.ps1"
    )
    if observer.is_symlink() or not observer.is_file():
        raise ValueError("reviewed_windows_native_uia_observer_missing")
    with TemporaryDirectory(prefix="medorigin-windows-encrypted-core-qa-") as tmp:
        work = Path(tmp).resolve()
        # User-profile and system installs are not sandboxed by this test.
        # Never process any input file, patient data, URL or external key.
        env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"),
            "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
            "TEMP": str(work),
            "TMP": str(work),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        command = [
            str(python),
            "-I",
            "-S",
            "-B",
            "-c",
            FIXED_CLI,
            str(core / "src"),
            str(core / "apps/workspace/src"),
            str(args.site),
        ]
        result = subprocess.run(
            command,
            cwd=work,
            env=env,
            capture_output=True,
            timeout=25,
            check=False,
        )
        if result.returncode != 0 or len(result.stdout) > 1024 or len(result.stderr) > 2048:
            raise ValueError("windows_source_core_ephemeral_workspace_demo_no_go")
        raw = strip_platform_one_newline(result.stdout)
        if raw != source_receipt.read_bytes() or hashlib.sha256(raw).hexdigest() != RECEIPT_SHA:
            raise ValueError("windows_source_core_encrypted_receipt_source_mismatch")
        receipt_file = work / "only-fictional-aggregate.json"
        receipt_file.write_bytes(raw)
        observed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(observer),
                "-ExePath",
                str(binary),
                "-ExpectedSha256",
                args.native_sha256,
                "-LiveReceiptPath",
                str(receipt_file),
            ],
            capture_output=True,
            timeout=45,
            check=False,
        )
        marker = b"D2_WINDOWS_ENCRYPTED_WORKSPACE_NATIVE_UIA_PASS_NONCLINICAL"
        if (
            observed.returncode != 0
            or marker not in observed.stdout
            or b"WINDOWS_FORGED_CLINICAL_WORKSPACE_APPROVAL_REFUSED" not in observed.stdout
        ):
            raise ValueError("windows_actual_native_gui_core_live_receipt_uia_no_go")
        print("WINDOWS_SOURCE_CORE_AES_GCM_FICTIONAL_REOPEN_CLEANUP_VERIFIED")
        print("WINDOWS_LIVE_SYNTHETIC_CORE_GUI_UIA_COUNTS_SHA_AND_FORGERY_PASS")
    if digest(python) != args.python_sha256.lower() or digest(binary) != args.native_sha256.lower():
        raise ValueError("reviewed_binary_changed_after_windows_ui_test")
    verify_pinned_core(core)
    print(SUCCESS)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("core-source", "python", "site", "native-gui", "python-sha256", "native-sha256"):
        p.add_argument("--" + key, required=True, type=str if key.endswith("sha256") else Path)
    try:
        qualify(p.parse_args())
    except (OSError, ValueError, subprocess.SubprocessError, UnicodeError) as error:
        print("WINDOWS_CORE_WORKSPACE_TO_NATIVE_GUI_NO_GO:" + str(error), file=sys.stderr)
        sys.exit(2)
