#!/usr/bin/env python3
"""Owner Windows private *task-owned* install/verify/GUI/uninstall qualification.

Only a synthetic SHA-pinned, unsigned setup. Always redirect LocalAppData and
Roaming Start Menu to disposable task-owned folders. Never touch real profile.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{64}")
BINARY = "medorigin-desktop-d2-native-egui.exe"
APP = "MedOrigin-D2-Private-Developer-QA"
INSTALL_SCRIPT = "Install-MedOrigin-Private.ps1"


def sha(path: Path) -> str:
    dig = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            dig.update(chunk)
    return dig.hexdigest()


def qualify(
    setup: Path,
    source: Path,
    scratch: Path,
    expected_binary_sha: str,
    *,
    real_gui: bool,
    runner=subprocess.run,
) -> None:
    if sys.platform != "win32":
        raise ValueError("windows_only_private_installer_qa")
    if not SHA.fullmatch(expected_binary_sha):
        raise ValueError("private_installer_qa_expected_binary_sha_refused")
    if not setup.is_file() or setup.is_symlink() or not scratch.is_dir():
        raise ValueError("installer_or_task_scratch_not_regular")
    if any(
        p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
        for p in (scratch, *scratch.parents)
    ):
        raise ValueError("installer_qa_reparse_scratch_refused")
    if not scratch.name.startswith("private-installer-qa-"):
        raise ValueError("installer_qa_requires_explicit_disposable_scratch")
    if not source.is_dir() or source.is_symlink():
        raise ValueError("installer_qa_source_missing")
    local = scratch / "profile" / "AppData" / "Local"
    roaming = scratch / "profile" / "AppData" / "Roaming"
    programs = roaming / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    programs.mkdir(parents=True, exist_ok=False)
    local.mkdir(parents=True, exist_ok=False)
    profile_env = {
        **os.environ,
        "LOCALAPPDATA": str(local),
        "APPDATA": str(roaming),
        "TEMP": str(scratch),
        "TMP": str(scratch),
    }
    sentinel = scratch / "unrelated-user-file.txt"
    sentinel.write_text("Must survive private test uninstall.\n", encoding="utf-8")
    installed = local / APP / "InstalledPreview"
    native = installed / BINARY
    install_script = installed / INSTALL_SCRIPT
    shortcut = programs / "MedOrigin Synthetic Preview.lnk"
    uninstall_shortcut = programs / "Uninstall MedOrigin Synthetic Preview.lnk"

    result = runner(
        [str(setup)], env=profile_env, capture_output=True, text=True, timeout=120, check=False
    )
    if result.returncode != 0 or not native.is_file() or not install_script.is_file():
        raise ValueError("installer_qa_setup_failed_or_not_installed")
    if sha(native) != expected_binary_sha:
        raise ValueError("installer_qa_binary_did_not_match_source")
    if not shortcut.is_file() or not uninstall_shortcut.is_file():
        raise ValueError("installer_qa_user_start_menu_missing")
    print("PRIVATE_OWNER_WINDOWS_SETUP_EXE_INSTALLED_USER_SCOPE_PASS")

    def ps(action: str):
        return runner(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(install_script),
                "-Action",
                action,
            ],
            env=profile_env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    verify = ps("Verify")
    if (
        verify.returncode != 0
        or "MEDORIGIN_PRIVATE_WINDOWS_USER_INSTALL_VERIFY_PASS_SYNTHETIC" not in verify.stdout
    ):
        raise ValueError("installer_qa_installed_integrity_or_shortcut_failure")
    print("PRIVATE_OWNER_WINDOWS_INSTALL_VERIFY_AND_START_MENU_PASS")

    if real_gui:
        if sha(native) != expected_binary_sha:
            raise ValueError("installer_qa_gui_binary_changed")
        scripts = source / "experiments" / "desktop-d2-native-egui" / "tests"
        tasks = (
            (
                "windows-native-fhir-uia-qualification.ps1",
                "-ExpectedSha256",
                "D2_NATIVE_FHIR_UIA_8_OF_8_PASS_NONPUBLISHING",
            ),
            (
                "windows-real-core963-file-batch-receipt-uia.ps1",
                "-ExpectedExeSha256",
                "D2_CORE_BATCH_REDACTED_SIDE_BY_SIDE_ACTUAL_WINDOWS_UIA_PASS_NONCLINICAL",
            ),
        )
        for name, flag, marker in tasks:
            test = scripts / name
            if not test.is_file():
                raise ValueError("installer_qa_native_uia_script_absent")
            completed = runner(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(test),
                    "-ExePath",
                    str(native),
                    flag,
                    expected_binary_sha,
                ],
                env=profile_env,
                capture_output=True,
                text=True,
                timeout=100,
                check=False,
            )
            if completed.returncode != 0 or marker not in completed.stdout.splitlines():
                raise ValueError("installer_qa_real_installed_native_gui_uia_failure:" + name)
            if sha(native) != expected_binary_sha:
                raise ValueError("installer_qa_gui_mutated_installed_binary")
            print("PRIVATE_OWNER_WINDOWS_INSTALLED_NATIVE_UIA_PASS=" + name)

    # Prove a pinned non-executable payload bit flip is refused. Do not
    # rewrite a recently executed Windows PE: the OS/AV may still hold it.
    tamper_file = installed / "README-SYNTHETIC.txt"
    before = tamper_file.read_bytes()
    try:
        with tamper_file.open("r+b") as handle:
            handle.seek(-1, os.SEEK_END)
            last = handle.read(1)
            handle.seek(-1, os.SEEK_END)
            handle.write(bytes([last[0] ^ 1]))
        invalid = ps("Verify")
        if invalid.returncode == 0:
            raise ValueError("installer_qa_tampered_binary_incorrectly_verified")
        if not shortcut.exists() or not uninstall_shortcut.exists():
            raise ValueError("installer_qa_refusal_removed_start_menu")
        print("PRIVATE_OWNER_WINDOWS_TAMPERED_PINNED_PAYLOAD_VERIFY_REFUSED")
    finally:
        tamper_file.write_bytes(before)
    if sha(native) != expected_binary_sha or ps("Verify").returncode != 0:
        raise ValueError("installer_qa_source_restoration_not_accepted")

    removal = ps("Uninstall")
    if removal.returncode != 0 or (
        "MEDORIGIN_PRIVATE_WINDOWS_USER_UNINSTALL_PASS_SYNTHETIC" not in removal.stdout
    ):
        raise ValueError("installer_qa_uninstall_failed:" + removal.stderr[-600:])
    if installed.exists() or shortcut.exists() or uninstall_shortcut.exists():
        raise ValueError("installer_qa_uninstall_left_install_or_shortcuts")
    if sentinel.read_text(encoding="utf-8") != "Must survive private test uninstall.\n":
        raise ValueError("installer_qa_touched_unrelated_user_file")
    print("MEDORIGIN_PRIVATE_OWNER_WINDOWS_SETUP_INSTALL_GUI_UNINSTALL_PASS_SYNTHETIC_NOT_RELEASED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--real-gui", action="store_true")
    args = parser.parse_args()
    try:
        qualify(args.setup, args.source, args.scratch, args.binary_sha256, real_gui=args.real_gui)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print("MEDORIGIN_PRIVATE_OWNER_WINDOWS_SETUP_QA_NO_GO:" + str(error), file=sys.stderr)
        sys.exit(2)
