#!/usr/bin/env python3
"""Archive D2's prebuilt, 64-bit, fictional-only native GUI for local testing.

No publishing, installer, signature, notarization, medical data, or downloads.
Windows=ZIP, macOS=unsigned .app in ZIP, Linux=glibc runtime-dependent tar.gz.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import platform
import plistlib
import re
import struct
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

BINARY = "medorigin-desktop-d2-native-egui"
APP = "MedOrigin Synthetic Preview"
NOTICE = (
    "MEDORIGIN SYNTHETIC DEVELOPER PREVIEW - NOT FOR PATIENT DATA.\n\n"
    "This native Rust/egui program contains ONLY fixed fictional fixtures.\n"
    "It is not the full MedOrigin Clinical Workspace or Python Research Core.\n"
    "No clinical FHIR validation, PHI, patient use or production is permitted.\n"
    "Network isolation, code signing/notarization, security review, full feature\n"
    "coverage, and OS-specific accessibility are NOT independently qualified.\n\n"
    "Windows: extract ZIP and launch the executable locally.\n"
    "macOS: extracted .app is unsigned; Gatekeeper may reject it. Never bypass\n"
    "OS protections for patient use. This is not a notarized DMG.\n"
    "Linux: extract tar.gz, supply compatible glibc/X11/Wayland/OpenGL libraries;\n"
    "this is NOT an AppImage or distro-supported installation package.\n"
    "Do not redistribute or install in a healthcare environment.\n"
)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def normalize_arch(value: str) -> str:
    value = value.lower()
    if value in ("amd64", "x86_64", "x64"):
        return "x86_64"
    if value in ("aarch64", "arm64"):
        return "arm64"
    raise ValueError("unsupported_architecture:" + value)


def target_host() -> tuple[str, str]:
    system = (
        "windows"
        if sys.platform == "win32"
        else (
            "macos"
            if sys.platform == "darwin"
            else ("linux" if sys.platform.startswith("linux") else "unknown")
        )
    )
    if system == "unknown":
        raise ValueError("unsupported_operating_system")
    return system, normalize_arch(platform.machine())


def selected_target(requested: str | None = None) -> tuple[str, str]:
    if requested is None:
        return target_host()
    try:
        system, arch = requested.split("-", 1)
    except ValueError as error:
        raise ValueError("invalid_explicit_cross_package_target") from error
    if system not in ("linux", "windows", "macos") or arch not in ("x86_64", "arm64"):
        raise ValueError("unsupported_explicit_cross_package_target")
    return system, arch


def inspect_native_header(data: bytes) -> tuple[str, str]:
    """Refuse a spoofed Windows/ELF/Mach-O filename or cross-architecture payload."""
    if data.startswith(b"MZ"):
        if len(data) < 128:
            raise ValueError("truncated_pe")
        offset = struct.unpack_from("<I", data, 0x3C)[0]
        if offset + 6 > len(data) or data[offset : offset + 4] != b"PE\x00\x00":
            raise ValueError("invalid_pe")
        cpu = struct.unpack_from("<H", data, offset + 4)[0]
        arch = {0x8664: "x86_64", 0xAA64: "arm64"}.get(cpu)
        if arch is None:
            raise ValueError("unsupported_pe_architecture")
        return "windows", arch
    if data.startswith(b"\x7fELF"):
        if len(data) < 20 or data[4] != 2 or data[5] != 1:
            raise ValueError("unsupported_elf")
        cpu = struct.unpack_from("<H", data, 18)[0]
        arch = {62: "x86_64", 183: "arm64"}.get(cpu)
        if arch is None:
            raise ValueError("unsupported_elf_architecture")
        return "linux", arch
    if data.startswith(b"\xcf\xfa\xed\xfe"):
        if len(data) < 12:
            raise ValueError("truncated_macho")
        cpu = struct.unpack_from("<I", data, 4)[0]
        arch = {0x01000007: "x86_64", 0x0100000C: "arm64"}.get(cpu)
        if arch is None:
            raise ValueError("unsupported_macho_architecture")
        return "macos", arch
    raise ValueError("not_a_supported_native_executable")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def commit_of(repo: Path) -> str:
    commit = (
        subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .lower()
    )
    if not COMMIT_RE.fullmatch(commit):
        raise ValueError("invalid_source_commit")
    return commit


def files_for(
    binary: bytes, system: str, arch: str, commit: str, license_text: bytes, upstream_text: bytes
) -> dict[str, tuple[bytes, int]]:
    executable = BINARY + (".exe" if system == "windows" else "")
    meta = {
        "schema": "medorigin-d2-synthetic-archive-v1",
        "name": APP,
        "source_commit": commit,
        "platform": system,
        "architecture": arch,
        "executable": executable,
        "binary_sha256": digest(binary),
        "synthetic_only": True,
        "release_authorized": False,
        "clinical_use_authorized": False,
        "patient_data_supported": False,
        "zero_egress_qualified": False,
        "signed_or_notarized": False,
        "production_installer": False,
    }
    if system == "macos":
        root = APP + ".app/Contents"
        where = root + "/Resources"
        binary_path = root + "/MacOS/" + executable
        info = plistlib.dumps(
            {
                "CFBundleDisplayName": APP,
                "CFBundleExecutable": executable,
                "CFBundleIdentifier": "si.medorigin.d2.synthetic.preview",
                "CFBundleInfoDictionaryVersion": "6.0",
                "CFBundleName": APP,
                "CFBundlePackageType": "APPL",
                "CFBundleShortVersionString": "0.0.0",
                "CFBundleVersion": "0.0.0",
                "LSMinimumSystemVersion": "12.0",
                "NSHighResolutionCapable": True,
            },
            sort_keys=True,
        )
    else:
        root = "MedOrigin-Synthetic-Preview"
        where = root
        binary_path = root + "/" + executable
    files = {
        binary_path: (binary, 0o755),
        where + "/README-SYNTHETIC.txt": (NOTICE.encode(), 0o644),
        where + "/MANIFEST.json": (
            (json.dumps(meta, indent=2, sort_keys=True) + "\n").encode(),
            0o644,
        ),
        where + "/LICENSE": (license_text, 0o644),
        where + "/UPSTREAM-NOTICE.md": (upstream_text, 0o644),
    }
    if system == "macos":
        files[root + "/Info.plist"] = (info, 0o644)
        files[root + "/PkgInfo"] = (b"APPL????", 0o644)
    return files


def write_archive(path: Path, files: dict[str, tuple[bytes, int]], system: str) -> None:
    if path.exists():
        raise ValueError("refuse_to_overwrite_existing_artifact")
    if system == "linux":
        with (
            path.open("xb") as handle,
            gzip.GzipFile(fileobj=handle, mode="wb", filename="", mtime=0) as gz,
            tarfile.open(fileobj=gz, mode="w") as tar,
        ):
            for name, (data, permissions) in sorted(files.items()):
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                entry.mode = permissions
                entry.mtime = 0
                entry.uid = 0
                entry.gid = 0
                tar.addfile(entry, io.BytesIO(data))
    else:
        with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as z:
            for name, (data, permissions) in sorted(files.items()):
                entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = (0o100000 | permissions) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=7)


def create(binary_path: Path, output: Path, repo: Path, target: str | None = None) -> Path:
    system, arch = selected_target(target)
    expected_name = BINARY + (".exe" if system == "windows" else "")
    if binary_path.is_symlink() or not binary_path.is_file() or binary_path.name != expected_name:
        raise ValueError("expected_exact_non_symlink_native_executable")
    size = binary_path.stat().st_size
    if size < 4096 or size > 120 * 1024 * 1024:
        raise ValueError("native_binary_size_out_of_bounds")
    binary = binary_path.read_bytes()
    if inspect_native_header(binary) != (system, arch):
        raise ValueError("binary_header_does_not_match_host_architecture")
    commit = commit_of(repo)
    files = files_for(
        binary,
        system,
        arch,
        commit,
        (repo / "LICENSE").read_bytes(),
        (repo / "experiments" / "desktop-d2-native-egui" / "UPSTREAM-NOTICE.md").read_bytes(),
    )
    output.mkdir(parents=True, exist_ok=True)
    extension = ".tar.gz" if system == "linux" else ".zip"
    archive = output / (
        "MedOrigin-Synthetic-D2-" + system + "-" + arch + "-" + commit[:8] + extension
    )
    write_archive(archive, files, system)
    print(
        json.dumps(
            {
                "status": "SYNTHETIC_ONLY_UNRELEASED",
                "archive": str(archive),
                "archive_sha256": digest(archive.read_bytes()),
                "binary_sha256": digest(binary),
                "source_commit": commit,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--target",
        choices=(
            "linux-x86_64",
            "linux-arm64",
            "windows-x86_64",
            "windows-arm64",
            "macos-arm64",
            "macos-x86_64",
        ),
        help="Optional cross-package target, binary header must match.",
    )
    args = parser.parse_args()
    try:
        create(args.binary, args.output, Path(__file__).resolve().parents[3], args.target)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print("SYNTHETIC_PACKAGE_REFUSED: " + str(error), file=sys.stderr)
        sys.exit(2)
