#!/usr/bin/env python3
"""Actual Windows Core encrypted fictional history -> native UIA (QA only).

One fixed OS Job-supervised Core worker, two historical fictional imports,
redacted 799-byte source-approved metadata, and real native D2 GUI buttons.
No user-provided patient record, auth key, URLs, EHR or clinical release.
Job lifetime confinement is NOT packet/network confinement.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from supervise_windows_encrypted_catalog_job import real_catalog_under_windows_job

PINNED_CORE_SHA = "35290b7c0f6f47995b52a10bb0ade9f7b27a67a8"
PINNED_CATALOG_SHA = "cfa5c71cd07763b6a1b32f7e6de8c51c565c4b6caf09224c51fcba095263b623"
PASS = "WINDOWS_JOB_SUPERVISED_REAL_ENCRYPTED_CORE_HISTORY_NATIVE_D2_GUI_PASS_NOT_CLINICAL"
UIA_MARKER = b"WINDOWS_REAL_ENCRYPTED_CORE_TWO_HISTORICAL_IMPORTS_NATIVE_UIA_PASS_NOT_CLINICAL"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, check=True, timeout=15,
    ).stdout


def approved_core_source(core: Path) -> None:
    if core.is_symlink() or not core.is_dir():
        raise ValueError("reviewed_core_catalog_source_missing")
    if git(core, "rev-parse", "HEAD").decode("ascii").strip() != PINNED_CORE_SHA:
        raise ValueError("core_catalog_source_exact_sha_not_reviewed")
    if git(core, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("core_catalog_source_checkout_dirty")
    for package in ("src/medscale", "apps/workspace/src/medscale_workspace"):
        tracked = {x.decode() for x in
                   git(core, "ls-files", "-z", "--", package).split(b"\x00") if x}
        if not 30 <= len(tracked) <= 500:
            raise ValueError("reviewed_core_catalog_source_inventory_count")
        seen = set()
        for item in (core / package).rglob("*"):
            if item.is_symlink() or (item.is_dir() and item.name.lower() == "__pycache__"):
                raise ValueError("unreviewed_catalog_core_symlink_or_python_bytecode")
            if item.is_file():
                name = item.relative_to(core).as_posix()
                if item.suffix.lower() in (".pyc", ".pyo", ".pth", ".pyd",
                                           ".dll", ".so", ".dylib"):
                    raise ValueError("unreviewed_catalog_core_native_loader")
                seen.add(name)
        if seen != tracked:
            raise ValueError("unreviewed_catalog_core_file_or_missing_source")


def qualify(args: argparse.Namespace) -> None:
    if sys.platform != "win32":
        raise ValueError("genuine_windows_desktop_required")
    if any(path.is_symlink() for path in
           (args.core_source, args.python, args.native_gui, args.site)):
        raise ValueError("reviewed_windows_core_and_GUI_symlink_refused")
    core = args.core_source.resolve(strict=True)
    python = args.python.resolve(strict=True)
    gui = args.native_gui.resolve(strict=True)
    site = args.site.resolve(strict=True)
    if (
        python.name.lower() != "python.exe"
        or gui.name != "medorigin-desktop-d2-native-egui.exe"
        or digest(python) != args.python_sha.lower()
        or digest(gui) != args.native_sha.lower()
        or not site.is_dir()
    ):
        raise ValueError("reviewed_windows_python_or_native_executable_not_matched")
    approved_core_source(core)
    root = Path(__file__).resolve().parent.parent
    fixture = root / "fixtures/core/encrypted-import-catalog-demo.json"
    observer = root / "tests/windows-encrypted-import-catalog-uia.ps1"
    if (
        any(path.is_symlink() or not path.is_file() for path in (fixture, observer))
        or fixture.stat().st_size != 799 or digest(fixture) != PINNED_CATALOG_SHA
    ):
        raise ValueError("fixed_fictional_import_catalog_source_not_approved")
    with TemporaryDirectory(prefix="medorigin-windows-real-encrypted-import-history-") as tmp:
        work = Path(tmp).resolve()
        # Verify membership BEFORE first instruction; this does not block
        # network/DNS/UDP/TCP and is not a clinical worker sandbox.
        raw = real_catalog_under_windows_job(
            python=python, core=core, site=site, work=work,
        )
        if (
            len(raw) != 799 or raw != fixture.read_bytes()
            or hashlib.sha256(raw).hexdigest() != PINNED_CATALOG_SHA
        ):
            raise ValueError("real_encrypted_core_import_history_mismatched_source_fixture")
        print("WINDOWS_REAL_CORE_TWO_ENCRYPTED_HISTORICAL_IMPORTS_VERIFIED")
        report = work / "fictional-import-history-only.json"
        report.write_bytes(raw)
        result = subprocess.run(
            ["powershell.exe","-NoProfile","-NonInteractive","-ExecutionPolicy",
             "Bypass","-File",str(observer),
             "-ExePath",str(gui),"-ExpectedSha256",args.native_sha,
             "-LiveReceiptPath",str(report)],
            cwd=work, capture_output=True, timeout=75, check=False,
        )
        if result.returncode != 0 or UIA_MARKER not in result.stdout:
            raise ValueError("genuine_windows_historical_import_GUI_UIA_refused")
        print(UIA_MARKER.decode())
    approved_core_source(core)
    if digest(gui) != args.native_sha.lower() or digest(python) != args.python_sha.lower():
        raise ValueError("reviewed_native_core_executable_changed_after_test")
    print(PASS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("core-source","python","native-gui","native-sha","python-sha","site"):
        parser.add_argument("--"+key,required=True,
                            type=str if key.endswith("-sha") else Path)
    try:
        qualify(parser.parse_args())
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print("WINDOWS_ENCRYPTED_CORE_HISTORY_NATIVE_UIA_NO_GO:"+str(error),file=sys.stderr)
        raise SystemExit(2)
