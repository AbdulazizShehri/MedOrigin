#!/usr/bin/env python3
"""Actual Mac Core encrypted historical fictional imports -> native D2 AX.

Source-bound QA ONLY. The QA parent, not D2, starts pinned Python Core
under a macOS deny-default Seatbelt network/outside-write profile. No PHI,
user-supplied path/key/URL, production crypto chain or authenticated IPC.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory

from qualify_sandboxed_synthetic_core import (
    prove_restrictive_mac_policy, run_sandboxed, sandbox_profile,
)

CORE_GIT_SHA = "35290b7c0f6f47995b52a10bb0ade9f7b27a67a8"
CATALOG_SHA = "cfa5c71cd07763b6a1b32f7e6de8c51c565c4b6caf09224c51fcba095263b623"
AX_PASS = b"MACOS_REAL_ENCRYPTED_CORE_HISTORICAL_IMPORT_LIST_NATIVE_AX_PASS_NOT_CLINICAL"
SUCCESS = "MACOS_SOURCE_CORE_ENCRYPTED_HISTORY_TO_REAL_NATIVE_D2_GUI_PASS_NONCLINICAL"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["/usr/bin/git", "-C", str(root), *args],
        capture_output=True, check=True, timeout=15,
    ).stdout


def require_pinned_core(core: Path) -> None:
    if core.is_symlink() or not core.is_dir():
        raise ValueError("pinned_catalog_core_source_missing")
    if git(core, "rev-parse", "HEAD").decode().strip() != CORE_GIT_SHA:
        raise ValueError("unreviewed_core_catalog_git_checkpoint")
    if git(core, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("core_catalog_checkout_not_clean")
    for package in ("src/medscale", "apps/workspace/src/medscale_workspace"):
        tracked = {
            name.decode() for name in git(core, "ls-files", "-z", "--", package).split(b"\0") if name
        }
        actual = set()
        if not 30 <= len(tracked) <= 500:
            raise ValueError("reviewed_core_catalog_modules_missing")
        for item in (core / package).rglob("*"):
            if item.is_symlink() or (item.is_dir() and item.name == "__pycache__"):
                raise ValueError("core_catalog_ignored_python_source_shadow_refused")
            if item.is_file():
                actual.add(item.relative_to(core).as_posix())
        if actual != tracked:
            raise ValueError("unreviewed_core_catalog_python_source_files")


def qualify(args: argparse.Namespace) -> None:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise ValueError("real_apple_silicon_mac_host_required")
    if any(path.is_symlink() for path in
           (args.core_source, args.python, args.native_gui, args.crypto_cache, args.cffi_cache)):
        raise ValueError("reviewed_python_core_native_path_symlink_refused")
    core = args.core_source.resolve(strict=True)
    python = args.python.resolve(strict=True)
    gui = args.native_gui.resolve(strict=True)
    crypto = args.crypto_cache.resolve(strict=True)
    cffi = args.cffi_cache.resolve(strict=True)
    if (python.name != "python3.13" or gui.name != "medorigin-desktop-d2-native-egui"
        or sha(gui) != args.native_sha.lower()
        or not crypto.is_dir() or not cffi.is_dir()):
        raise ValueError("native_or_python_exact_executable_refused")
    require_pinned_core(core)
    root = Path(__file__).resolve().parent.parent
    receipt = root / "fixtures/core/encrypted-import-catalog-demo.json"
    ax = root / "tests/macos-encrypted-import-catalog-ax.swift"
    if (receipt.is_symlink() or ax.is_symlink() or sha(receipt) != CATALOG_SHA
        or receipt.stat().st_size != 799):
        raise ValueError("source_compiled_catalog_receipt_refused")
    fixed = (
        "import sys;"
        "sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]];"
        "from medscale.fhirkit.workspace_catalog_demo import receipt_json;"
        "print(receipt_json(),end='')"
    )
    with TemporaryDirectory(prefix="medorigin-real-core-import-history-") as temp:
        work = Path(temp).resolve()
        work.chmod(0o700)
        policy = sandbox_profile(work)
        prove_restrictive_mac_policy(policy, work, python)
        result = run_sandboxed(policy, [
            str(python), "-I", "-S", "-B", "-c", fixed,
            str(core/"src"), str(core/"apps/workspace/src"),
            str(crypto), str(cffi),
        ], work)
        if (result.returncode != 0 or result.stderr
            or result.stdout != receipt.read_bytes()
            or hashlib.sha256(result.stdout).hexdigest() != CATALOG_SHA):
            raise ValueError("real_encrypted_core_catalog_source_not_exact")
        print("MACOS_REAL_CORE_TWO_ENCRYPTED_HISTORICAL_IMPORTS_PROVEN")
        native = subprocess.Popen(
            [str(gui), "--synthetic-encrypted-import-history-stdin"],
            cwd=work, stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={"PATH":"/usr/bin:/bin","HOME":str(work)},
        )
        try:
            assert native.stdin is not None
            native.stdin.write(result.stdout)
            native.stdin.close()
            observed = subprocess.run(
                ["/usr/bin/swift", str(ax), str(native.pid)],
                capture_output=True, timeout=70, check=False,
            )
            if observed.returncode != 0 or AX_PASS not in observed.stdout or native.poll() is not None:
                failure = observed.stderr.decode("utf-8",errors="replace")[:700]
                raise ValueError("mac_real_import_catalog_native_AX_refused:" + failure)
            print(AX_PASS.decode())
        finally:
            if native.poll() is None:
                native.terminate()
                try:
                    native.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    native.kill()
                    native.wait(timeout=4)
    if sha(gui) != args.native_sha.lower():
        raise ValueError("reviewed_native_GUI_executable_modified_after_QA")
    require_pinned_core(core)
    print(SUCCESS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("core-source","python","native-gui","native-sha","crypto-cache","cffi-cache"):
        parser.add_argument("--"+key,required=True,type=str if key=="native-sha" else Path)
    try:
        qualify(parser.parse_args())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print("MACOS_ENCRYPTED_IMPORT_HISTORY_GUI_NO_GO:"+str(exc),file=sys.stderr)
        raise SystemExit(2)
