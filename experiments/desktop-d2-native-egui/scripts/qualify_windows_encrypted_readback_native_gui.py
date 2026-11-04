#!/usr/bin/env python3
"""Windows real encrypted fictional Core readback => native D2 GUI QA.

Source-pinned, no external records/paths/keys. Does NOT confine Core
network access or attest third-party system crypto. Never clinical.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

CORE_SHA = "8e5ed5430f4ab2ebc8981c52c67234023382954b"
PROJECTION_SHA = "c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49"
SUCCESS = "WINDOWS_LIVE_ENCRYPTED_CORE_READBACK_TO_NATIVE_D2_GUI_PASS_NOT_CLINICAL"
PACKAGES = (
    ("src/medscale", 120, 450),
    ("apps/workspace/src/medscale_workspace", 30, 120),
)
FIXED_CODE = (
    "import sys,runpy,importlib.metadata as m;"
    "sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]];"
    "assert m.version('cryptography')=='50.0.1';"
    "assert m.version('cffi')=='2.1.1';"
    "script=sys.argv[4];sys.argv=[script];"
    "runpy.run_path(script,run_name='__main__')"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(core: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(core), *args],
        capture_output=True, check=True, timeout=12,
    ).stdout


def source_bound_core(core: Path) -> None:
    if core.is_symlink() or not core.is_dir():
        raise ValueError("reviewed_core_source_missing")
    if git(core, "rev-parse", "HEAD").decode("ascii").strip() != CORE_SHA:
        raise ValueError("reviewed_core_source_commit_changed")
    if git(core, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("reviewed_core_source_not_clean")
    for package, minimum, maximum in PACKAGES:
        inventory = git(core, "ls-files", "-z", "--", package)
        approved = {
            name.decode()
            for name in inventory.split(b"\x00") if name
        }
        if not minimum <= len(approved) <= maximum:
            raise ValueError("reviewed_core_source_inventory_changed")
        actual = set()
        for path in (core / package).rglob("*"):
            if path.is_symlink():
                raise ValueError("unreviewed_python_core_source_symlink")
            if path.is_dir() and path.name.lower() == "__pycache__":
                raise ValueError("ignored_python_bytecode_cache_refused")
            if path.is_file():
                relative = path.relative_to(core).as_posix()
                if path.suffix.lower() in (".pyc", ".pyo", ".pyd", ".dll", ".so",
                                            ".pth", ".dylib"):
                    raise ValueError("unreviewed_python_bytecode_native_loader_refused")
                actual.add(relative)
        if actual != approved:
            raise ValueError("reviewed_core_source_untracked_or_missing_files")


def qualify(args: argparse.Namespace) -> None:
    if sys.platform != "win32":
        raise ValueError("real_windows_native_ui_qa_required")
    core = args.core_source.resolve(strict=True)
    python = args.python.resolve(strict=True)
    gui = args.native_gui.resolve(strict=True)
    source_bound_core(core)
    if (args.python.is_symlink() or args.native_gui.is_symlink()
        or python.name.lower() != "python.exe"
        or gui.name != "medorigin-desktop-d2-native-egui.exe"
        or sha(python) != args.python_sha.lower()
        or sha(gui) != args.native_sha.lower()):
        raise ValueError("reviewed_python_or_native_gui_executable_changed")
    site = args.site.resolve(strict=True)
    if args.site.is_symlink() or not site.is_dir():
        raise ValueError("system_crypto_site_packages_missing")
    root = Path(__file__).resolve().parent.parent
    fixture = root / "fixtures/core/encrypted-readback-projection.json"
    script = root / "scripts/synthetic_encrypted_readback_projection.py"
    observer = root / "tests/windows-encrypted-core-readback-uia.ps1"
    if (any(p.is_symlink() or not p.is_file() for p in (fixture, script, observer))
        or sha(fixture) != PROJECTION_SHA):
        raise ValueError("reviewed_synthetic_core_projection_fixture_changed")
    with TemporaryDirectory(prefix="medorigin-windows-source-core-readback-") as temp:
        work = Path(temp).resolve()
        env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"),
            "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
            "TEMP": str(work),
            "TMP": str(work),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        executed = subprocess.run(
            [str(python), "-I", "-S", "-B", "-c", FIXED_CODE,
             str(core / "src"), str(core / "apps/workspace/src"),
             str(site), str(script)],
            cwd=work, env=env, capture_output=True, timeout=45, check=False,
        )
        if (executed.returncode != 0 or executed.stderr
            or len(executed.stdout) > 2048
            or executed.stdout != fixture.read_bytes()
            or hashlib.sha256(executed.stdout).hexdigest() != PROJECTION_SHA):
            raise ValueError("real_windows_core_encrypted_readback_source_mismatch")
        print("WINDOWS_REAL_ENCRYPTED_CORE_THREE_RESOURCE_READBACK_SOURCE_VERIFIED")
        receipt_path = work / "fixed-source-fantasy-only.json"
        receipt_path.write_bytes(executed.stdout)
        qualified_gui = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-File", str(observer),
             "-ExePath", str(gui), "-ExpectedSha256", args.native_sha,
             "-LiveReceiptPath", str(receipt_path)],
            cwd=work, env=env, capture_output=True, timeout=80, check=False,
        )
        marker = b"WINDOWS_REAL_ENCRYPTED_CORE_READBACK_THREE_RESOURCES_LINK_AND_BACK_UIA_PASS_NOT_CLINICAL"
        if qualified_gui.returncode != 0 or marker not in qualified_gui.stdout:
            raise ValueError("real_windows_encrypted_Core_resource_UIA_refused")
        print(marker.decode())
    source_bound_core(core)
    if sha(python) != args.python_sha.lower() or sha(gui) != args.native_sha.lower():
        raise ValueError("reviewed_core_or_native_binary_changed_during_QA")
    print(SUCCESS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("core-source", "python", "site", "native-gui", "python-sha", "native-sha"):
        parser.add_argument("--" + key, required=True,
                            type=str if key.endswith("-sha") else Path)
    try:
        qualify(parser.parse_args())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print("WINDOWS_REAL_ENCRYPTED_CORE_READBACK_NATIVE_UIA_NO_GO:" + str(error), file=sys.stderr)
        raise SystemExit(2)
