#!/usr/bin/env python3
"""Explicit Windows developer launcher: genuine encrypted fictional Core -> native D2.

Not a clinical application, authenticated transport, OS egress sandbox or release.
Only the reviewed fixed three-resource imaginary Bundle and exact native GUI are
permitted. This companion launcher is separate from the network/process-free GUI.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import os
import re
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from tempfile import TemporaryDirectory

from qualify_windows_encrypted_readback_native_gui import (
    PROJECTION_SHA,
    sha,
    source_bound_core,
)
from supervise_windows_encrypted_core_job import execute_encrypted_source_under_job

WINDOW_TITLE = "MedOrigin Native Rust"
WINDOW_TIMEOUT_SECONDS = 1800
QA_WINDOW_TIMEOUT_SECONDS = 45
SUCCESS = "WINDOWS_INTERACTIVE_REAL_ENCRYPTED_FICTIONAL_CORE_TO_D2_PASS_NOT_CLINICAL"
REFUSAL = "WINDOWS_INTERACTIVE_FICTIONAL_CORE_D2_NO_GO"
READBACK_SOURCE_MAX_BYTES = 2048
GUI_FLAG = "--synthetic-encrypted-readback-stdin"


def _attest_input_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    if sys.platform != "win32":
        raise ValueError("windows_only")
    # Refuse both direct reparse points and unexpected reviewed basename.
    for item in (args.core_source, args.python, args.site, args.native_gui):
        if item.is_symlink():
            raise ValueError("input_reparse_point")
    core = args.core_source.resolve(strict=True)
    python = args.python.resolve(strict=True)
    site = args.site.resolve(strict=True)
    gui = args.native_gui.resolve(strict=True)
    if (
        not core.is_dir()
        or not site.is_dir()
        or not python.is_file()
        or python.name.lower() != "python.exe"
        or not gui.is_file()
        or gui.name != "medorigin-desktop-d2-native-egui.exe"
        or not re.fullmatch(r"[0-9a-fA-F]{64}", args.python_sha)
        or not re.fullmatch(r"[0-9a-fA-F]{64}", args.native_sha)
        or sha(python) != args.python_sha.lower()
        or sha(gui) != args.native_sha.lower()
    ):
        raise ValueError("unreviewed_python_site_or_gui")
    source_bound_core(core)
    root = Path(__file__).resolve().parent.parent
    fixture = root / "fixtures/core/encrypted-readback-projection.json"
    exporter = root / "scripts/synthetic_encrypted_readback_projection.py"
    if (
        any(path.is_symlink() or not path.is_file() for path in (fixture, exporter))
        or fixture.stat().st_size > READBACK_SOURCE_MAX_BYTES
        or sha(fixture) != PROJECTION_SHA
    ):
        raise ValueError("unreviewed_core_projection_source")
    return core, python, site, gui, fixture


def _qa_close_exact_owned_window(pid: int, seen: threading.Event) -> None:
    """Only for unattended dev QA: WM_CLOSE the exact spawned D2 process."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    for _ in range(100):

        def inspect(hwnd: int, _lparam: int) -> bool:
            owner = wintypes.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value != pid or not user32.IsWindowVisible(hwnd):
                return True
            title = ctypes.create_unicode_buffer(160)
            user32.GetWindowTextW(hwnd, title, len(title))
            if title.value.startswith(WINDOW_TITLE) and user32.PostMessageW(
                hwnd, 0x0010, 0, 0
            ):  # WM_CLOSE
                seen.set()
            return True

        func = callback_type(inspect)
        user32.EnumWindows(func, 0)
        if seen.is_set():
            return
        time.sleep(0.15)


def launch(args: argparse.Namespace) -> None:
    core, python, site, gui, fixture = _attest_input_paths(args)
    root = Path(__file__).resolve().parent.parent
    exporter = root / "scripts/synthetic_encrypted_readback_projection.py"
    with TemporaryDirectory(prefix="medorigin-private-core-fictional-live-") as temp:
        work = Path(temp).resolve()
        raw = execute_encrypted_source_under_job(
            python=python, core=core, site=site, exporter=exporter, work=work
        )
        if (
            len(raw) != 1164
            or raw != fixture.read_bytes()
            or hashlib.sha256(raw).hexdigest() != PROJECTION_SHA
        ):
            raise ValueError("fresh_core_output_not_exact_synthetic_projection")
        if sha(python) != args.python_sha.lower() or sha(gui) != args.native_sha.lower():
            raise ValueError("binary_changed_before_native_start")
        system = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
        # No inherited PYTHONPATH, cloud credentials or user-selected FHIR content.
        child_env = {
            "SYSTEMROOT": str(system),
            "WINDIR": str(system),
            "PATH": os.pathsep.join((str(gui.parent), str(system / "System32"))),
            "TEMP": str(work),
            "TMP": str(work),
        }
        process = None
        seen = threading.Event()
        try:
            process = subprocess.Popen(
                [str(gui), GUI_FLAG],
                cwd=work,
                env=child_env,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            if args.qa_auto_close:
                closer = threading.Thread(
                    target=_qa_close_exact_owned_window,
                    args=(process.pid, seen),
                    name="fictional-native-owned-window-close-QA",
                    daemon=True,
                )
                closer.start()
            _output, _errors = process.communicate(
                input=raw,
                timeout=(
                    QA_WINDOW_TIMEOUT_SECONDS if args.qa_auto_close else WINDOW_TIMEOUT_SECONDS
                ),
            )
            if process.returncode != 0 or (args.qa_auto_close and not seen.is_set()):
                raise ValueError("reviewed_native_gui_did_not_close_cleanly")
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate(timeout=5)
    source_bound_core(core)
    if sha(python) != args.python_sha.lower() or sha(gui) != args.native_sha.lower():
        raise ValueError("binary_changed_after_native_close")
    print(SUCCESS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("core-source", "python", "site", "native-gui", "python-sha", "native-sha"):
        parser.add_argument(
            "--" + key,
            required=True,
            type=str if key.endswith("-sha") else Path,
        )
    parser.add_argument(
        "--qa-auto-close",
        action="store_true",
        help="Close only the owned fictional GUI window in QA.",
    )
    try:
        launch(parser.parse_args())
    except (OSError, ValueError, subprocess.SubprocessError):
        print(REFUSAL, file=sys.stderr)
        raise SystemExit(2) from None
