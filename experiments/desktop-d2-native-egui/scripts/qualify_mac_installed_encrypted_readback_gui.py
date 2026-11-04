#!/usr/bin/env python3
"""Verified installed Core+Workspace Wheels → encrypted synthetic readback → D2.

Explicit, externally supervised private QA only. No patient input or storage,
no in-GUI Python spawn, no production worker identity/keys. OS sandbox is
applied to the Python child, not to the native GUI. Crypto QA caches on Mac
are NOT a trusted/pinned production chain and must be disclosed as such.
"""
from __future__ import annotations

import argparse
import hashlib
import platform
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from attest_installed_encrypted_core_readback import attest_installed
from qualify_sandboxed_synthetic_core import (
    prove_restrictive_mac_policy,
    run_sandboxed,
    sandbox_profile,
)

PROJECTION_SHA = "c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49"
MAC_PASS = "MACOS_ATTESTED_INSTALLED_CORE_ENCRYPTED_READBACK_TO_NATIVE_D2_GUI_PASS_NONCLINICAL"
NATIVE_AX = (
    "MACOS_REAL_ENCRYPTED_CORE_READBACK_NATIVE_THREE_FICTIONAL_RESOURCE_NAV_AX_PASS_NOT_CLINICAL"
).encode()
# No wheel dynamically passes caller-selected code, flags, URL, FHIR, or key.
INSTALLED_RUNNER = (
    "import sys,runpy;"
    "sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]];"
    "script=sys.argv[4];sys.argv=[script];"
    "runpy.run_path(script,run_name='__main__')"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(args: argparse.Namespace) -> None:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise ValueError("genuine_mac_apple_silicon_QA_host_required")
    core = args.core_source
    wheels = args.wheels
    site = args.installed_site
    if any(path.is_symlink() or not path.is_dir() for path in (core, wheels, site)):
        raise ValueError("reviewed_core_wheel_site_directory_refused")
    core = core.resolve(strict=True)
    wheels = wheels.resolve(strict=True)
    site = site.resolve(strict=True)
    python = args.python.resolve(strict=True)
    gui = args.native_gui.resolve(strict=True)
    if (
        args.python.is_symlink() or args.native_gui.is_symlink()
        or python.name != "python3.13"
        or gui.name != "medorigin-desktop-d2-native-egui"
        or sha(gui) != args.native_sha.lower()
    ):
        raise ValueError("reviewed_python_or_D2_executable_refused")
    root = Path(__file__).resolve().parent.parent
    exporter = root / "scripts/synthetic_encrypted_readback_projection.py"
    fixture = root / "fixtures/core/encrypted-readback-projection.json"
    observer = root / "tests/macos-encrypted-core-readback-ax.swift"
    if (
        any(path.is_symlink() or not path.is_file()
            for path in (exporter, fixture, observer))
        or sha(fixture) != PROJECTION_SHA
    ):
        raise ValueError("source_pinned_synthetic_projection_refused")
    caches = [args.crypto_cache, args.cffi_cache]
    if any(path.is_symlink() or not path.is_dir() for path in caches):
        raise ValueError("unreviewed_optional_QA_crypto_cache")
    caches = [path.resolve(strict=True) for path in caches]
    # Requires exact source Git commit + 2 offline Wheel file SHA256s,
    # all 290 Git-tracked packaged files and all installed package bytes.
    attest_installed(core, wheels, site)
    with TemporaryDirectory(prefix="medorigin-installed-core-readback-gui-") as tmp:
        work = Path(tmp).resolve()
        work.chmod(0o700)
        profile = sandbox_profile(work)
        prove_restrictive_mac_policy(profile, work, python)
        result = run_sandboxed(
            profile,
            [str(python), "-I", "-S", "-B", "-c", INSTALLED_RUNNER,
             str(site), str(caches[0]), str(caches[1]), str(exporter)],
            work,
        )
        if (
            result.returncode != 0 or result.stderr
            or len(result.stdout) != 1164
            or sha(fixture) != PROJECTION_SHA
            or result.stdout != fixture.read_bytes()
            or hashlib.sha256(result.stdout).hexdigest() != PROJECTION_SHA
        ):
            raise ValueError("installed_python_Core_real_encrypted_readback_output_refused")
        print("MACOS_REAL_INSTALLED_WHEELS_CORE_ENCRYPTED_READBACK_SOURCE_MATCHED")
        # The D2 window uses reviewed finite stdin only. This external QA
        # parent owns process lifetime, and always kills it on refusal/exit.
        proc = subprocess.Popen(
            [str(gui), "--synthetic-encrypted-readback-stdin"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, cwd=work,
            env={"PATH": "/usr/bin:/bin", "HOME": str(work)},
        )
        try:
            assert proc.stdin is not None
            proc.stdin.write(result.stdout)
            proc.stdin.close()
            tested = subprocess.run(
                ["/usr/bin/swift", str(observer), str(proc.pid)],
                capture_output=True, timeout=60, check=False,
            )
            if (
                tested.returncode != 0 or NATIVE_AX not in tested.stdout
                or proc.poll() is not None
            ):
                raise ValueError("installed_core_decrypted_native_D2_accessibility_failed")
            print(NATIVE_AX.decode())
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
    if sha(gui) != args.native_sha.lower():
        raise ValueError("native_gui_binary_changed_after_installed_Core_test")
    attest_installed(core, wheels, site)
    print(MAC_PASS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "core-source", "wheels", "installed-site", "python", "native-gui",
        "native-sha", "crypto-cache", "cffi-cache",
    ):
        parser.add_argument("--" + name, required=True,
                            type=str if name == "native-sha" else Path)
    try:
        qualify(parser.parse_args())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("MACOS_INSTALLED_CORE_READBACK_NATIVE_GUI_NO_GO:" + str(error), file=sys.stderr)
        raise SystemExit(2)
