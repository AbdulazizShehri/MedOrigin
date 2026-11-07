#!/usr/bin/env python3
"""Real installed Core + encrypted Workspace QA into native D2, Mac only.

No PHI, source URLs, networking or arbitrary subprocess instructions. This
observes a short-lived encrypted fictional demo with a TEST-ONLY key provider
under macOS Seatbelt and renders only exact source-bound aggregate metadata.
Does NOT enable in-GUI Python process control, clinical storage or release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile

from qualify_sandboxed_synthetic_core import (
    sandbox_profile, prove_restrictive_mac_policy, run_sandboxed,
)

EXPECTED_CORE_COMMIT = "0351b667ec910480fd61c30f18cf3bb0dd0ae842"
EXPECTED_CORE_WHEEL = "7b1a7eb088b7f14a23fca335f174fe9710bdad497499ba4178e20fe90b6fb778"
EXPECTED_WORKSPACE_WHEEL = "c37516f2b7b831b3fcfc417a2d7703c29d0917f3c684c19215f7e07399e05b73"
EXPECTED_RECEIPT_SHA = "25acdb57db8ca3f11d353cf311167973760caaa95bb64de7339fe21e3b05cc2e"
SUCCESS = "MACOS_INSTALLED_CORE_ENCRYPTED_WORKSPACE_NATIVE_D2_GUI_PASS_NOT_CLINICAL"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def attest_installed(core: Path, wheels: Path, site: Path) -> None:
    sha_head = subprocess.run(
        ["/usr/bin/git", "-C", str(core), "rev-parse", "HEAD"],
        capture_output=True, check=True, text=True, timeout=12,
    ).stdout.strip()
    if sha_head != EXPECTED_CORE_COMMIT:
        raise ValueError("reviewed_core_source_commit_not_matched")
    for package, wheel_filename, expected in (
        ("medscale", "medscale-0.3.0-py3-none-any.whl", EXPECTED_CORE_WHEEL),
        ("medscale_workspace", "medscale_workspace-0.1.0.dev1-py3-none-any.whl", EXPECTED_WORKSPACE_WHEEL),
    ):
        wheel = wheels / wheel_filename
        if wheel.is_symlink() or not wheel.is_file() or sha(wheel.read_bytes()) != expected:
            raise ValueError("core_or_workspace_wheel_unreviewed_bytes")
        path = "src/medscale" if package == "medscale" else "apps/workspace/src/medscale_workspace"
        tracked = subprocess.run(
            ["/usr/bin/git", "-C", str(core), "ls-files", "-z", "--", path],
            capture_output=True, check=True, timeout=12,
        ).stdout
        files = [x.decode("utf-8") for x in tracked.split(b"\x00") if x]
        if not 25 <= len(files) <= 400:
            raise ValueError("unreviewed_core_or_workspace_source_inventory")
        with zipfile.ZipFile(wheel) as archive:
            expected_files = {
                name.removeprefix("src/").removeprefix("apps/workspace/src/"): name
                for name in files
            }
            packaged = {n for n in archive.namelist() if n.startswith(package + "/")}
            if set(expected_files) != packaged:
                raise ValueError("core_or_workspace_wheel_package_source_members_changed")
            for pkg_file, git_path in expected_files.items():
                source = core / git_path
                installed = site / pkg_file
                if (
                    source.is_symlink() or installed.is_symlink()
                    or not source.is_file() or not installed.is_file()
                    or archive.read(pkg_file) != source.read_bytes()
                    or installed.read_bytes() != source.read_bytes()
                ):
                    raise ValueError("installed_core_workspace_module_bytes_not_source")
    print("INSTALLED_CORE_WORKSPACE_TWO_WHEELS_BYTE_ATTESTED")


def qualify(args: argparse.Namespace) -> None:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise ValueError("apple_silicon_mac_real_ax_host_required")
    root = args.core_source.resolve(strict=True)
    site = args.site.resolve(strict=True)
    python = args.python.resolve(strict=True)
    binary = args.native_gui.resolve(strict=True)
    if (
        binary.name != "medorigin-desktop-d2-native-egui"
        or sha(binary.read_bytes()) != args.native_sha.lower()
        or python.name != "python3.13"
        or args.native_gui.is_symlink()
    ):
        raise ValueError("native_gui_or_python_identity_not_reviewed")
    attest_installed(root, args.wheels.resolve(strict=True), site)
    fixture = Path(__file__).resolve().parent.parent / "fixtures/core/workspace-ephemeral-demo.json"
    if fixture.is_symlink() or sha(fixture.read_bytes()) != EXPECTED_RECEIPT_SHA:
        raise ValueError("canonical_synthetic_encrypted_demo_fixture_changed")
    for cache in [args.crypto_cache, args.cffi_cache]:
        if cache.is_symlink() or not cache.is_dir():
            raise ValueError("unreviewed_optional_crypto_cache_location")
    with tempfile.TemporaryDirectory(prefix="medorigin-real-encrypted-d2-demo-") as tmp:
        work = Path(tmp).resolve()
        work.chmod(0o700)
        profile = sandbox_profile(work)
        prove_restrictive_mac_policy(profile, work, python)
        code = (
            "import sys;"
            "sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]];"
            "from medscale.cli.fhir import main;"
            "raise SystemExit(main(['workspace-demo','--synthetic-only','--ephemeral-demo']))"
        )
        result = run_sandboxed(
            profile, [str(python), "-I", "-S", "-B", "-c", code,
                      str(site), str(args.crypto_cache), str(args.cffi_cache)], work,
        )
        if result.returncode != 0 or not result.stdout.endswith(b"\n"):
            raise ValueError("mac_sandboxed_ephemeral_encrypted_core_demo_refused")
        raw = result.stdout[:-1]
        if raw != fixture.read_bytes() or sha(raw) != EXPECTED_RECEIPT_SHA:
            raise ValueError("real_encrypted_core_demo_did_not_match_compiled_receipt")
        if json.loads(raw)["clinical_use_authorized"] is not False:
            raise ValueError("core_demo_falsely_authorized_clinical_data")
        process = subprocess.Popen(
            [str(binary), "--synthetic-workspace-receipt-stdin"],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, cwd=work,
            env={"PATH": "/usr/bin:/bin", "HOME": str(work)},
        )
        try:
            assert process.stdin is not None
            process.stdin.write(raw)
            process.stdin.close()
            ax = Path(__file__).resolve().parent.parent / "tests/macos-encrypted-workspace-native-ax.swift"
            observed = subprocess.run(
                ["/usr/bin/swift", str(ax), str(process.pid), EXPECTED_RECEIPT_SHA],
                capture_output=True, timeout=35, check=False,
            )
            expected = ("MACOS_INSTALLED_ENCRYPTED_CORE_WORKSPACE_NATIVE_GUI_AX_PASS "
                        + EXPECTED_RECEIPT_SHA + "\n").encode()
            if observed.returncode != 0 or observed.stdout != expected or process.poll() is not None:
                raise ValueError("native_gui_encrypted_workspace_real_ax_refused")
            print("REAL_MAC_ENCRYPTED_WORKSPACE_FICTIONAL_REOPEN_AND_DELETE_DISPLAYED")
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=4)
            if process.stderr: process.stderr.close()
    if sha(binary.read_bytes()) != args.native_sha.lower():
        raise ValueError("native_gui_binary_changed_during_test")
    attest_installed(root, args.wheels.resolve(strict=True), site)
    print(SUCCESS)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("core-source", "wheels", "site", "python", "native-gui", "native-sha", "crypto-cache", "cffi-cache"):
        ap.add_argument("--"+name, required=True, type=str if name == "native-sha" else Path)
    try:
        qualify(ap.parse_args())
    except (ValueError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print("D2_ENCRYPTED_WORKSPACE_NATIVE_GUI_QA_NO_GO:" + str(error), file=sys.stderr)
        sys.exit(2)
