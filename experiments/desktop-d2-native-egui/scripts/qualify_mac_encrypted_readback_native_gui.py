#!/usr/bin/env python3
"""Real synthetic encrypted Core in-memory readback -> native Mac D2 GUI QA.

No patient paths/data/keys, no production process supervisor. The fixed Core
Python process is restricted by the existing Mac deny-default Seatbelt QA
policy. Source-pinned 3-record projection only, exact bytes + SHA, no sender
freshness proof. Source-only and locally cached crypto are NOT trusted Wheels.
"""

from __future__ import annotations

import argparse
import hashlib
import platform
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from qualify_sandboxed_synthetic_core import (
    prove_restrictive_mac_policy,
    run_sandboxed,
    sandbox_profile,
)

PINNED_CORE_SHA = "8e5ed5430f4ab2ebc8981c52c67234023382954b"
PINNED_PROJECTION_SHA = "c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49"
PASS = "MACOS_SEATBELT_LIVE_CORE_ENCRYPTED_READBACK_NATIVE_D2_GUI_PASS_NOT_CLINICAL"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_core(core: Path) -> None:
    if core.is_symlink() or not core.is_dir():
        raise ValueError("source_core_checkout_missing")
    head = subprocess.run(
        ["/usr/bin/git", "-C", str(core), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout.strip()
    if head != PINNED_CORE_SHA:
        raise ValueError("source_core_sha_mismatch")
    status = subprocess.run(
        ["/usr/bin/git", "-C", str(core), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        timeout=10,
        check=True,
    ).stdout
    if status:
        raise ValueError("source_core_git_dirty")
    for pkg in ("src/medscale", "apps/workspace/src/medscale_workspace"):
        tracked = subprocess.run(
            ["/usr/bin/git", "-C", str(core), "ls-files", "-z", "--", pkg],
            capture_output=True,
            timeout=10,
            check=True,
        ).stdout
        approved = {(core / path.decode()).resolve() for path in tracked.split(b"\x00") if path}
        if not 25 <= len(approved) <= 400:
            raise ValueError("source_core_expected_inventory_missing")
        actual = set()
        for path in (core / pkg).rglob("*"):
            if path.is_symlink():
                raise ValueError("core_unreviewed_symlink")
            if path.is_file():
                actual.add(path.resolve())
        if actual != approved:
            raise ValueError("core_unreviewed_ignored_or_missing_files")


def qualify(args: argparse.Namespace) -> None:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise ValueError("apple_silicon_real_native_ax_required")
    core = args.core_source.resolve(strict=True)
    python = args.python.resolve(strict=True)
    app = args.native_gui.resolve(strict=True)
    root = Path(__file__).resolve().parent.parent
    if (
        args.core_source.is_symlink()
        or args.native_gui.is_symlink()
        or args.python.is_symlink()
        or python.name != "python3.13"
        or app.name != "medorigin-desktop-d2-native-egui"
        or sha(app) != args.native_sha.lower()
    ):
        raise ValueError("native_gui_or_python_not_qualified")
    pinned_core(core)
    projection = root / "fixtures/core/encrypted-readback-projection.json"
    script = root / "scripts/synthetic_encrypted_readback_projection.py"
    observer = root / "tests/macos-encrypted-core-readback-ax.swift"
    if (
        any(path.is_symlink() or not path.is_file() for path in (projection, script, observer))
        or sha(projection) != PINNED_PROJECTION_SHA
    ):
        raise ValueError("source_pinned_encrypted_readback_fixture_changed")
    caches = [arg.resolve(strict=True) for arg in (args.crypto_cache, args.cffi_cache)]
    if any(not cache.is_dir() or cache.is_symlink() for cache in caches):
        raise ValueError("local_QA_crypto_cache_missing")
    with TemporaryDirectory(prefix="medorigin-d2-real-encrypted-readback-") as temp:
        work = Path(temp).resolve()
        work.chmod(0o700)
        policy = sandbox_profile(work)
        prove_restrictive_mac_policy(policy, work, python)
        fixed = (
            "import sys,runpy;"
            "sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]];"
            "script=sys.argv[5];sys.argv=[script];"
            "runpy.run_path(script,run_name='__main__')"
        )
        cmd = [
            str(python),
            "-I",
            "-S",
            "-B",
            "-c",
            fixed,
            str(core / "src"),
            str(core / "apps/workspace/src"),
            str(caches[0]),
            str(caches[1]),
            str(script),
        ]
        executed = run_sandboxed(policy, cmd, work)
        if executed.returncode != 0 or executed.stderr:
            raise ValueError("mac_restricted_core_encrypted_readback_refused")
        if executed.stdout != projection.read_bytes():
            raise ValueError("real_core_recovered_projection_not_source_exact")
        if hashlib.sha256(executed.stdout).hexdigest() != PINNED_PROJECTION_SHA:
            raise ValueError("real_core_encrypted_readback_digest_changed")
        print("MACOS_REAL_ENCRYPTED_CORE_THREE_RESOURCE_READBACK_SOURCE_VERIFIED")
        process = subprocess.Popen(
            [str(app), "--synthetic-encrypted-readback-stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=work,
            env={"HOME": str(work), "PATH": "/usr/bin:/bin"},
        )
        try:
            assert process.stdin is not None
            process.stdin.write(executed.stdout)
            process.stdin.close()
            observed = subprocess.run(
                ["/usr/bin/swift", str(observer), str(process.pid)],
                capture_output=True,
                timeout=60,
                check=False,
            )
            token = (
                b"MACOS_REAL_ENCRYPTED_CORE_READBACK_NATIVE_"
                b"THREE_FICTIONAL_RESOURCE_NAV_AX_PASS_NOT_CLINICAL"
            )
            if (
                observed.returncode != 0
                or token not in observed.stdout
                or process.poll() is not None
            ):
                detail = observed.stderr.decode("utf-8", errors="replace")[:600]
                raise ValueError("mac_real_encrypted_readback_native_gui_AX_refused:" + detail)
            print(token.decode())
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=4)
    if sha(app) != args.native_sha.lower():
        raise ValueError("native_gui_executable_changed_during_QA")
    pinned_core(core)
    print(PASS)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("core-source", "python", "native-gui", "native-sha", "crypto-cache", "cffi-cache"):
        p.add_argument("--" + name, required=True, type=str if name == "native-sha" else Path)
    try:
        qualify(p.parse_args())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print("MACOS_LIVE_ENCRYPTED_CORE_READBACK_NATIVE_GUI_NO_GO:" + str(error), file=sys.stderr)
        raise SystemExit(2) from None
