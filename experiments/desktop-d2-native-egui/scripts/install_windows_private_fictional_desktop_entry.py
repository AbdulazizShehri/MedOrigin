#!/usr/bin/env python3
"""Install one private, opt-in, nonclinical Windows D2 fictional GUI shortcut.

Creates a fail-closed, exact-path Windows .cmd shortcut for an ALREADY attested
portable kit. No elevation, registry, Start Menu, startup task, symlink, cloud
fetch, real patient data, key provider or overwrite. A console stays visible.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from launch_windows_portable_fictional_core import attest_kit
from qualify_windows_encrypted_readback_native_gui import sha
from windows_fictional_persistent_vault import QA_DIR_NAME

ENTRY_NAME = "Start-MedOrigin-Fictional-Desktop.cmd"
QA_ENTRY_NAME = "QA-MedOrigin-Fictional-Desktop-UIA.cmd"
CLOSE_ENTRY_NAME = "QA-MedOrigin-Fictional-Desktop-AutoClose.cmd"
PRIVATE_PARENT_NAME = "MedOrigin-D2-Private-Developer-QA"
SUCCESS = "WINDOWS_PRIVATE_FICTIONAL_DESKTOP_ONE_CLICK_ENTRY_CREATED_NOT_CLINICAL"
REFUSAL = "WINDOWS_PRIVATE_FICTIONAL_DESKTOP_ENTRY_NO_GO"

# No CMD metacharacters, environment expansion, shell substitution, reparse
# target, UNC/network path, drive-relative path, newline, emoji or quotes.
_REVIEWED_PATH = re.compile(r"^[A-Za-z]:\\[A-Za-z0-9 _\\.\\-]+$")


def _path(path: Path, *, directory: bool) -> Path:
    raw = str(path)
    if not _REVIEWED_PATH.fullmatch(raw) or len(raw) > 245:
        raise ValueError("private_one_click_unreviewed_shell_path")
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("private_one_click_reparse_path_refused")
    current = path.parent
    while current != current.parent:
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError("private_one_click_reparse_ancestor_refused")
        current = current.parent
    resolved = path.resolve(strict=True)
    if str(resolved).casefold() != raw.casefold():
        raise ValueError("private_one_click_alias_or_unc_refused")
    if directory and not path.is_dir():
        raise ValueError("private_one_click_expected_directory")
    if not directory and not path.is_file():
        raise ValueError("private_one_click_expected_file")
    return path


def _installed_parent() -> Path:
    if sys.platform != "win32" or os.name != "nt":
        raise ValueError("windows_native_private_entry_only")
    raw = os.environ.get("LOCALAPPDATA", "")
    if not raw:
        raise ValueError("private_one_click_local_appdata_missing")
    local = _path(Path(raw), directory=True)
    return local / PRIVATE_PARENT_NAME


def make_entry(args: argparse.Namespace) -> Path:
    parent = _installed_parent()
    python = _path(args.python, directory=False)
    site = _path(args.crypto_site, directory=True)
    kit = _path(args.kit, directory=True)
    if python.name.casefold() != "python.exe":
        raise ValueError("private_one_click_not_python_executable")
    if python != Path(sys.executable).resolve(strict=True):
        raise ValueError("private_one_click_python_not_current_reviewed_interpreter")
    if (
        not isinstance(args.python_sha, str)
        or not re.fullmatch(r"[a-fA-F0-9]{64}", args.python_sha)
        or sha(python) != args.python_sha.lower()
    ):
        raise ValueError("private_one_click_python_digest_refused")
    if kit == parent or kit.is_relative_to(parent):
        raise ValueError("private_one_click_kit_inside_persistent_private_root")
    # Read the strict signed? NO: byte-hash-attested, UNSIGNED original kit.
    # Every runtime file and all 290 reviewed source files are rechecked
    # by the actual portable launcher on every use, not just at installation.
    gui, exporter, fixture = attest_kit(kit)
    if not (gui.is_file() and exporter.is_file() and fixture.is_file()):
        raise ValueError("private_one_click_attested_kit_missing")
    mode = getattr(args, "qa_mode", "interactive")
    name_by_mode = {
        "interactive": ENTRY_NAME,
        "uia": QA_ENTRY_NAME,
        "auto-close": CLOSE_ENTRY_NAME,
    }
    if mode not in name_by_mode:
        raise ValueError("private_one_click_unreviewed_mode")
    if parent.exists():
        _path(parent, directory=True)
    else:
        # Only this exact current-user LocalAppData child may be created.
        parent.mkdir(mode=0o700)
    out = parent / name_by_mode[mode]
    if out.exists() or out.is_symlink() or (hasattr(out, "is_junction") and out.is_junction()):
        raise ValueError("private_one_click_shortcut_exists_do_not_overwrite")
    vault = parent / QA_DIR_NAME
    if vault.is_symlink() or (hasattr(vault, "is_junction") and vault.is_junction()):
        raise ValueError("private_one_click_vault_reparse_refused")
    for new_path in (out, vault):
        if not _REVIEWED_PATH.fullmatch(str(new_path)):
            raise ValueError("private_one_click_generated_shell_path_refused")
    launcher = kit / "scripts/launch_windows_portable_fictional_core.py"
    _path(launcher, directory=False)
    # The CMD file has NO interpolation of user-controlled shell content.
    # It must not accept arguments from the user, even in QA mode; the pinned
    # reviewed Python helper will independently attest the whole kit again.
    line = (
        f'"{python}" -B "{launcher}"'
        f' --python "{python}"'
        f' --crypto-site "{site}"'
        f" --python-sha {args.python_sha.lower()}"
        f' --fictional-persistent-qa-root "{vault}"'
        " --ensure-fictional-demo"
        + (
            " --qa-uia"
            if mode == "uia"
            else " --qa-auto-close"
            if mode == "auto-close"
            else " --start-focused"
        )
    )
    script = (
        "@echo off\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        "echo MedOrigin private imaginary-records demo ONLY. NEVER real patient data.\r\n"
        + line
        + "\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    if len(script) > 1350 or any(ord(c) > 127 for c in script):
        raise ValueError("private_one_click_generated_script_refused")
    # Exclusive owner-output: never rewrite an existing shortcut or vault.
    with out.open("x", encoding="ascii", newline="") as stream:
        stream.write(script)
        stream.flush()
        os.fsync(stream.fileno())
    print(SUCCESS)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--crypto-site", type=Path, required=True)
    parser.add_argument("--python-sha", required=True)
    parser.add_argument(
        "--qa-mode", choices=["interactive", "uia", "auto-close"], default="interactive"
    )
    try:
        make_entry(parser.parse_args())
    except (OSError, ValueError):
        print(REFUSAL, file=sys.stderr)
        raise SystemExit(2) from None
