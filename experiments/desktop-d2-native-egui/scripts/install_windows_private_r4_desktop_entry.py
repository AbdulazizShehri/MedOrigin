#!/usr/bin/env python3
"""Opt-in single-click Windows PRIVATE fictional R4 Core-to-native worklist entry.

Install only into current user's LocalAppData. No Start Menu, elevation, task,
registry, network, EHR, patient input, real PHI, key persistence or publisher.
Existing entries are never overwritten. This is NOT a production installer.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import os
from pathlib import Path
import re
import sys

import launch_windows_real_core971_official_r4_fictional_batch as r4
import launch_windows_real_core963_fictional_batch as legacy

PARENT_NAME = "MedOrigin-D2-Private-Developer-QA"
NAMES = {
    "interactive": "Open-MedOrigin-R4-Fictional-Worklist.cmd",
    "uia": "QA-MedOrigin-R4-Fictional-Worklist-UIA.cmd",
    "auto-close": "QA-MedOrigin-R4-Fictional-Worklist-AutoClose.cmd",
}
SUCCESS = "PRIVATE_R4_FICTIONAL_WORKLIST_CLICKABLE_ENTRY_INSTALLED_NO_CLINICAL_RELEASE"
REFUSAL = "PRIVATE_R4_FICTIONAL_WORKLIST_CLICKABLE_ENTRY_NO_GO"
# No CMD metacharacters, percent/delayed expansion, UNC aliases, non-ASCII
# argument injection, path traversal or quote/newline syntax.
PATH_RE = re.compile(r"^[A-Za-z]:\\[A-Za-z0-9 _.\-\\]+$")
HEX_RE = re.compile(r"^[a-f0-9]{64}$")


def _safe_windows_path(path: Path, *, directory: bool) -> Path:
    original = str(path)
    if len(original) > 225 or not PATH_RE.fullmatch(original):
        raise ValueError("r4_clickable_unreviewed_windows_shell_path")
    if not path.is_absolute() or path.drive == "":
        raise ValueError("r4_clickable_nonabsolute_path")
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("r4_clickable_reparse_path_refused")
    for ancestor in path.parents:
        if ancestor.is_symlink() or (
            hasattr(ancestor, "is_junction") and ancestor.is_junction()
        ):
            raise ValueError("r4_clickable_reparse_ancestor_refused")
    resolved = path.resolve(strict=True)
    if str(resolved).casefold() != original.casefold():
        raise ValueError("r4_clickable_path_alias_refused")
    if directory and not path.is_dir():
        raise ValueError("r4_clickable_directory_expected")
    if not directory and not path.is_file():
        raise ValueError("r4_clickable_file_expected")
    return path


def _parent() -> Path:
    if sys.platform != "win32" or os.name != "nt":
        raise ValueError("r4_clickable_windows_only")
    local = os.environ.get("LOCALAPPDATA", "")
    if not local:
        raise ValueError("r4_clickable_localappdata_unavailable")
    base = _safe_windows_path(Path(local), directory=True)
    return base / PARENT_NAME


def _render(
    python: Path, script: Path, core: Path, exe: Path, sha: str,
    archive: Path, mode: str,
) -> str:
    if mode not in NAMES or not HEX_RE.fullmatch(sha):
        raise ValueError("r4_clickable_unreviewed_mode_or_hash")
    suffix = {
        "interactive": "",
        "uia": " --qa-uia",
        "auto-close": " --qa-auto-close",
    }[mode]
    cmd = (
        f'"{python}" -B "{script}"'
        f' --core-source "{core}"'
        f' --native-exe "{exe}"'
        f' --native-sha256 {sha}'
        f' --offline-r4-schema "{archive}"'
        f'{suffix}'
    )
    # Hide nothing: console displays the synthetic/release warning on every click.
    output = (
        "@echo off\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        "echo MedOrigin R4 fictional local Developer QA ONLY. NEVER patient data.\r\n"
        + cmd + "\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    if len(output) > 1450 or any(ord(c) > 127 for c in output):
        raise ValueError("r4_clickable_generated_cmd_not_ascii_or_bounded")
    return output


def create_entry(args: argparse.Namespace) -> Path:
    # All checks BEFORE any user-home write. No unreviewed path is launched.
    parent = _parent()
    if args.mode not in NAMES:
        raise ValueError("r4_clickable_mode_not_allowlisted")
    python = _safe_windows_path(args.python, directory=False)
    if python.name.casefold() != "python.exe" or (
        str(python).casefold() != str(Path(sys.executable).resolve(strict=True)).casefold()
    ):
        raise ValueError("r4_clickable_wrong_python_runtime")
    python_hash = getattr(args, "python_sha256", "")
    if not isinstance(python_hash, str) or not HEX_RE.fullmatch(python_hash):
        raise ValueError("r4_clickable_python_hash_invalid")
    if legacy._file_sha(python) != python_hash:
        raise ValueError("r4_clickable_python_changed")
    if importlib.metadata.version("jsonschema") != "4.25.1":
        raise ValueError("r4_clickable_jsonschema_version_unpinned")
    core = _safe_windows_path(args.core_source, directory=True)
    r4._attest_core(core)  # Exact clean Core971 commit, not latest/main.
    archive = _safe_windows_path(args.offline_r4_schema, directory=False)
    r4._attest_offline_r4_schema(archive)  # Exact genuine official HL7 archive.
    exe = _safe_windows_path(args.native_exe, directory=False)
    if exe.name != legacy.EXE_NAME:
        raise ValueError("r4_clickable_wrong_native_executable")
    native_sha = getattr(args, "native_sha256", "")
    if not isinstance(native_sha, str) or not HEX_RE.fullmatch(native_sha):
        raise ValueError("r4_clickable_native_sha_invalid")
    if legacy._file_sha(exe) != native_sha:
        raise ValueError("r4_clickable_native_executable_modified")
    # Source and file contents will be verified AGAIN by launcher on each click.
    script = _safe_windows_path(
        Path(__file__).resolve().parent / "launch_windows_real_core971_official_r4_fictional_batch.py",
        directory=False,
    )
    if parent.exists():
        _safe_windows_path(parent, directory=True)
    elif not PATH_RE.fullmatch(str(parent)) or len(str(parent)) > 225:
        raise ValueError("r4_clickable_output_parent_unreviewed")
    output = parent / NAMES[args.mode]
    if not PATH_RE.fullmatch(str(output)) or len(str(output)) > 240:
        raise ValueError("r4_clickable_output_filename_unreviewed")
    if output.exists() or output.is_symlink():
        raise ValueError("r4_clickable_existing_entry_not_overwritten")
    contents = _render(python, script, core, exe, native_sha, archive, args.mode)
    # Create exclusively in current-user local area; no startup, Start Menu,
    # OS associations or global shell modifications.
    if not parent.exists():
        parent.mkdir(mode=0o700)
    with output.open("x", encoding="ascii", newline="") as stream:
        stream.write(contents)
        stream.flush()
        os.fsync(stream.fileno())
    print(SUCCESS)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--python-sha256", required=True)
    parser.add_argument("--core-source", required=True, type=Path)
    parser.add_argument("--offline-r4-schema", required=True, type=Path)
    parser.add_argument("--native-exe", required=True, type=Path)
    parser.add_argument("--native-sha256", required=True)
    parser.add_argument("--mode", choices=tuple(NAMES), default="interactive")
    try:
        create_entry(parser.parse_args())
    except (OSError, ValueError, importlib.metadata.PackageNotFoundError):
        print(REFUSAL, file=sys.stderr)
        raise SystemExit(2) from None
