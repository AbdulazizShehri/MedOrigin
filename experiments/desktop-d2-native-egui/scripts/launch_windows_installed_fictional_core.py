#!/usr/bin/env python3
"""Private Windows installed-Wheel fictional Core -> interactive native D2 GUI.

No real records, EHR, clinical use, OS network confinement or release.
The pinned installed Core source is proven byte-exact to the two Wheel files
and the clean Git checkout before AND after running. Crypto native modules
are developer-system dependencies, not independently attested supply chain.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

from attest_installed_encrypted_core_readback import attest_installed
from launch_windows_encrypted_fictional_preview import (
    GUI_FLAG,
    QA_WINDOW_TIMEOUT_SECONDS,
    WINDOW_TIMEOUT_SECONDS,
    _qa_close_exact_owned_window,
)
from qualify_windows_encrypted_readback_native_gui import PROJECTION_SHA, sha
from supervise_windows_encrypted_core_job import execute_encrypted_source_under_job

# Built offline from the reviewed 8e5ed54 Git checkpoint on Windows WSL,
# verified all 290 installed Python files, Wheel members and original source.
# Windows Wheel ZIP bytes differ from the Mac-built pinned Wheel ZIPs in #931;
# these hashes pin THIS particular nonpublishing Windows QA build only.
WINDOWS_APPROVED_WHEELS = (
    (
        "medscale",
        "src/medscale",
        "medscale-0.3.0-py3-none-any.whl",
        "9aad845ecec6b09e27b38a29a2fb521b3958218aef5ae4b0415abb88ee5fc24b",
        256,
    ),
    (
        "medscale_workspace",
        "apps/workspace/src/medscale_workspace",
        "medscale_workspace-0.1.0.dev1-py3-none-any.whl",
        "86488f14f113ec2e56f0c5185b91fbd61e546dc73f06587730b6794436e8d465",
        34,
    ),
)
EXPORTER_SHA256 = "446db8a83c523dbb74f027dde196db466fb7a2127c6788ec7cd9e095d915dced"
SUCCESS = "WINDOWS_INSTALLED_290_SOURCE_VERIFIED_ENCRYPTED_CORE_INTERACTIVE_D2_PASS_NOT_CLINICAL"
REFUSED = "WINDOWS_INSTALLED_FICTIONAL_CORE_INTERACTIVE_D2_NO_GO"


def qualify_paths(args: argparse.Namespace) -> tuple[Path, ...]:
    if sys.platform != "win32":
        raise ValueError("windows_host_required")
    original = (
        args.core_source,
        args.wheels,
        args.installed_site,
        args.python,
        args.crypto_site,
        args.native_gui,
    )
    if any(path.is_symlink() for path in original):
        raise ValueError("unreviewed_reparse_point")
    core, wheels, installed, python, crypto, gui = (item.resolve(strict=True) for item in original)
    if (
        not core.is_dir()
        or not wheels.is_dir()
        or not installed.is_dir()
        or not crypto.is_dir()
        or not python.is_file()
        or not gui.is_file()
        or python.name.lower() != "python.exe"
        or gui.name != "medorigin-desktop-d2-native-egui.exe"
        or not re.fullmatch("[0-9a-fA-F]{64}", args.python_sha)
        or not re.fullmatch("[0-9a-fA-F]{64}", args.native_sha)
        or sha(python) != args.python_sha.lower()
        or sha(gui) != args.native_sha.lower()
    ):
        raise ValueError("reviewed_python_crypto_site_or_native_exe_changed")
    root = Path(__file__).resolve().parent.parent
    exporter = root / "scripts/synthetic_encrypted_readback_projection.py"
    fixture = root / "fixtures/core/encrypted-readback-projection.json"
    if (
        any(path.is_symlink() or not path.is_file() for path in (exporter, fixture))
        or sha(exporter) != EXPORTER_SHA256
        or sha(fixture) != PROJECTION_SHA
        or fixture.stat().st_size != 1164
    ):
        raise ValueError("source_reviewed_fictional_exporter_or_projection_changed")
    attest_installed(core, wheels, installed, approved_wheels=WINDOWS_APPROVED_WHEELS)
    return core, wheels, installed, python, crypto, gui, exporter, fixture


def _present_native_gui(gui: Path, raw: bytes, work: Path, *, qa_auto_close: bool) -> None:
    system = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    child_env = {
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
            [str(gui), GUI_FLAG],
            cwd=work,
            env=child_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        if qa_auto_close:
            threading.Thread(
                target=_qa_close_exact_owned_window,
                args=(process.pid, seen),
                name="installed-fictional-owned-D2-auto-close-QA",
                daemon=True,
            ).start()
        process.communicate(
            input=raw,
            timeout=QA_WINDOW_TIMEOUT_SECONDS if qa_auto_close else WINDOW_TIMEOUT_SECONDS,
        )
        if process.returncode != 0 or (qa_auto_close and not seen.is_set()):
            raise ValueError("native_source_qualified_d2_gui_not_closed_cleanly")
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate(timeout=5)


def _verify_installed_core_in_native_uia(
    gui: Path,
    raw: bytes,
    work: Path,
    native_sha: str,
) -> None:
    """Windows UIAutomation runs against the exact real installed-Core bytes."""
    observer = (
        Path(__file__).resolve().parent.parent / "tests/windows-encrypted-core-readback-uia.ps1"
    )
    if observer.is_symlink() or not observer.is_file():
        raise ValueError("installed_core_ui_observer_missing")
    receipt = work / "installed-fictional-readback-verified.json"
    if receipt.exists() or receipt.is_symlink():
        raise ValueError("installed_core_uia_receipt_preexisting")
    receipt.write_bytes(raw)
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
            native_sha,
            "-LiveReceiptPath",
            str(receipt),
        ],
        cwd=work,
        env={
            "SYSTEMROOT": str(system),
            "WINDIR": str(system),
            "PATH": str(system / "System32"),
            "TEMP": str(work),
            "TMP": str(work),
        },
        capture_output=True,
        timeout=85,
        check=False,
    )
    marker = (
        b"WINDOWS_REAL_ENCRYPTED_CORE_READBACK_THREE_RESOURCES_LINK_AND_BACK_UIA_PASS_NOT_CLINICAL"
    )
    if result.returncode != 0 or marker not in result.stdout:
        raise ValueError("installed_core_real_native_uia_refused")
    print("WINDOWS_INSTALLED_ENCRYPTED_CORE_TO_NATIVE_D2_GRAPH_UIA_PASS_NONCLINICAL")


def launch(args: argparse.Namespace) -> None:
    core, wheels, installed, python, crypto, gui, exporter, fixture = qualify_paths(args)
    with TemporaryDirectory(prefix="medorigin-windows-installed-fictional-core-") as tmp:
        work = Path(tmp).resolve()
        # This runs Windows Python3.14 -I -S -B from the installed Wheel
        # module tree, explicitly verifying both __file__ paths. The source
        # checkout is used only for the external preflight attestation.
        raw = execute_encrypted_source_under_job(
            python=python,
            core=core,
            site=crypto,
            exporter=exporter,
            work=work,
            installed_site=installed,
        )
        if (
            len(raw) != 1164
            or raw != fixture.read_bytes()
            or hashlib.sha256(raw).hexdigest() != PROJECTION_SHA
        ):
            raise ValueError("installed_core_encrypted_fictional_output_refused")
        if sha(python) != args.python_sha.lower() or sha(gui) != args.native_sha.lower():
            raise ValueError("reviewed_executable_changed_before_native_gui")
        if args.qa_uia:
            _verify_installed_core_in_native_uia(gui, raw, work, args.native_sha)
        else:
            _present_native_gui(gui, raw, work, qa_auto_close=args.qa_auto_close)
    # The native app never opens the source package; local installation is
    # only source-attested again after the GUI was closed and temps removed.
    attest_installed(core, wheels, installed, approved_wheels=WINDOWS_APPROVED_WHEELS)
    if sha(python) != args.python_sha.lower() or sha(gui) != args.native_sha.lower():
        raise ValueError("reviewed_executable_changed_after_native_gui")
    print(SUCCESS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in (
        "core-source",
        "wheels",
        "installed-site",
        "python",
        "crypto-site",
        "native-gui",
        "python-sha",
        "native-sha",
    ):
        parser.add_argument(
            "--" + key,
            required=True,
            type=str if key.endswith("-sha") else Path,
        )
    qa = parser.add_mutually_exclusive_group()
    qa.add_argument(
        "--qa-auto-close",
        action="store_true",
        help="Only close the owned native window in unattended QA.",
    )
    qa.add_argument(
        "--qa-uia",
        action="store_true",
        help="Check native filter/navigation UIA on installed Core output.",
    )
    try:
        launch(parser.parse_args())
    except (OSError, ValueError, subprocess.SubprocessError):
        print(REFUSED, file=sys.stderr)
        raise SystemExit(2) from None
