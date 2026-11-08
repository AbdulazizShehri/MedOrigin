#!/usr/bin/env python3
"""Live macOS GUI qualification of the exact D2 synthetic preview archive.

No release, code signing, patient data, security sandbox, VoiceOver speech, or
packet/egress claims. Extract only verified canonical files to a private temp
directory, run only the exact embedded executable, and perform real AX actions.
"""

from __future__ import annotations

import argparse
import os
import platform
import stat
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from package_preview import APP, BINARY, digest, files_for
from verify_preview import verify_archive

ROOT = Path(__file__).resolve().parents[3]
TESTS = Path(__file__).resolve().parents[1] / "tests"
AX_BASIC = TESTS / "macos-native-ax-qualification.swift"
AX_FHIR = TESTS / "macos-native-fhir-ax-qualification.swift"
BINARY_NAME = BINARY
BUNDLE = APP + ".app"
BINARY_MEMBER = BUNDLE + "/Contents/MacOS/" + BINARY_NAME
MAX_MEMBER = 120 * 1024 * 1024
SUCCESS = "MACOS_D2_EXACT_ARCHIVE_REAL_AX_PASS_SYNTHETIC_ONLY_NOT_RELEASE"


def extract_verified_macos(archive: Path, dest: Path, repo: Path) -> tuple[Path, str]:
    """Verify source contract, then extract exactly the seven known bundle files."""
    manifest = verify_archive(archive, repo, target="macos-arm64")
    if manifest["platform"] != "macos" or manifest["architecture"] != "arm64":
        raise ValueError("macos_arm64_only")
    if dest.is_symlink() or not dest.is_dir():
        raise ValueError("destination_not_private_directory")
    if os.name == "posix" and (dest.stat().st_mode & 0o077) != 0:
        raise ValueError("private_directory_permissions_required")
    expected_sha = manifest["binary_sha256"]
    bundle_root = dest / BUNDLE
    binary_path = dest / Path(BINARY_MEMBER)
    if bundle_root.exists():
        raise ValueError("refuse_existing_app_bundle")
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        if len(members) != 7 or len({i.filename for i in members}) != 7:
            raise ValueError("archive_member_set_changed")
        for info in members:
            entry = PurePosixPath(info.filename)
            if entry.is_absolute() or ".." in entry.parts or entry.parts[0] != BUNDLE:
                raise ValueError("unsafe_macos_bundle_member")
            mode = info.external_attr >> 16
            if (mode & 0o170000) != stat.S_IFREG:
                raise ValueError("nonregular_bundle_member")
            limit = MAX_MEMBER if info.filename == BINARY_MEMBER else 1024 * 1024
            if info.file_size > limit:
                raise ValueError("oversized_bundle_member")
            target = dest.joinpath(*entry.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            # exclusive creation: never follow a preexisting symlink or overwrite
            with source.open(info) as reader, target.open("xb") as output:
                data = reader.read(limit + 1)
                if len(data) != info.file_size:
                    raise ValueError("archive_content_changed_during_extraction")
                output.write(data)
            target.chmod(mode & 0o777)
    if not binary_path.is_file() or binary_path.is_symlink():
        raise ValueError("missing_native_executable")
    native_bytes = binary_path.read_bytes()
    if digest(native_bytes) != expected_sha:
        raise ValueError("embedded_binary_differs_from_verified_manifest")
    # A mutable ZIP could change between admission and extraction. Reconstruct
    # the exact canonical seven files from the *extracted* binary and source.
    canonical = files_for(
        native_bytes,
        "macos",
        "arm64",
        manifest["source_commit"],
        (repo / "LICENSE").read_bytes(),
        (repo / "experiments/desktop-d2-native-egui/UPSTREAM-NOTICE.md").read_bytes(),
    )
    for name, (expected_data, expected_mode) in canonical.items():
        actual = dest.joinpath(*PurePosixPath(name).parts)
        if not actual.is_file() or actual.is_symlink() or actual.read_bytes() != expected_data:
            raise ValueError("extracted_bundle_source_contract_changed:" + name)
        if os.name == "posix" and (actual.stat().st_mode & 0o777) != expected_mode:
            raise ValueError("extracted_bundle_mode_changed:" + name)
    return binary_path, expected_sha


def run_checked(command: list[str], seconds: int = 90) -> None:
    result = subprocess.run(command, capture_output=True, text=True, timeout=seconds, check=False)
    if result.stdout:
        print(result.stdout.strip(), flush=True)
    if result.returncode:
        raise ValueError(
            "accessibility_qualification_refused:"
            + str(result.returncode)
            + ":"
            + result.stderr[-1800:]
        )


def qualify(archive: Path, repo: Path = ROOT) -> None:
    if sys.platform != "darwin" or platform.machine().lower() not in ("arm64", "aarch64"):
        raise ValueError("real_interactive_apple_silicon_mac_required")
    if not AX_BASIC.is_file() or not AX_FHIR.is_file():
        raise ValueError("source_controlled_ax_tests_missing")
    with TemporaryDirectory(prefix="medorigin-d2-archive-gui-") as temp:
        dest = Path(temp)
        dest.chmod(0o700)
        binary, source_sha = extract_verified_macos(archive, dest, repo)
        app = dest / BUNDLE
        proc: subprocess.Popen[bytes] | None = None
        try:
            proc = subprocess.Popen(
                [str(binary)],
                cwd=app,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            time.sleep(1.5)
            if proc.poll() is not None:
                raise ValueError("native_gui_exited_before_ax")
            # The 4 primary and 8 additional fictional fixtures must be
            # visited through real AX actions, with distinct digest labels.
            run_checked(["swift", str(AX_BASIC), str(proc.pid)], 120)
            if proc.poll() is not None:
                raise ValueError("native_gui_exited_during_ax")
            run_checked(["swift", str(AX_FHIR), str(proc.pid), source_sha], 120)
            if proc.poll() is not None:
                raise ValueError("native_gui_exited_during_fhir_ax")
            if digest(binary.read_bytes()) != source_sha:
                raise ValueError("native_binary_mutated_during_real_gui_run")
            print(SUCCESS, flush=True)
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    try:
        qualify(args.archive)
    except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print("MACOS_D2_ARCHIVE_GUI_NO_GO: " + str(exc), file=sys.stderr)
        sys.exit(2)
