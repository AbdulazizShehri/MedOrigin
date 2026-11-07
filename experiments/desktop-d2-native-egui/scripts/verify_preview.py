#!/usr/bin/env python3
"""Verify the exact nonclinical native D2 archive member contract, not release safety."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat
import sys
import tarfile
import zipfile

from package_preview import (
    APP, BINARY, commit_of, digest, files_for, inspect_native_header, selected_target,
)

MIB = 1024 * 1024
MAX_ARCHIVE_BYTES = 140 * MIB
MAX_BINARY_BYTES = 120 * MIB
MAX_RESOURCE_BYTES = MIB
MAX_SMALL_BYTES = 64 * 1024


def _expected_paths(system: str) -> tuple[str, str, str]:
    executable = BINARY + (".exe" if system == "windows" else "")
    if system == "macos":
        root = APP + ".app/Contents"
        return root + "/MacOS/" + executable, root + "/Resources/MANIFEST.json", root
    root = "MedOrigin-Synthetic-Preview"
    return root + "/" + executable, root + "/MANIFEST.json", root


def _member_limit(name: str, binary_path: str) -> int:
    if name == binary_path:
        return MAX_BINARY_BYTES
    if name.endswith(("/MANIFEST.json", "/Info.plist", "/PkgInfo", "/README-SYNTHETIC.txt")):
        return MAX_SMALL_BYTES
    return MAX_RESOURCE_BYTES


def verify_archive(path: Path, repo: Path, target: str | None = None) -> dict:
    """Fail closed on extra, duplicate, special, oversized, or substituted archive files."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected_regular_archive")
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("oversized_archive")
    system, architecture = selected_target(target)
    extension = ".tar.gz" if system == "linux" else ".zip"
    commit = commit_of(repo)
    expected_filename = (
        "MedOrigin-Synthetic-D2-" + system + "-" + architecture +
        "-" + commit[:8] + extension
    )
    if path.name != expected_filename:
        raise ValueError("unexpected_archive_filename_or_source_commit")

    binary_path, manifest_path, root = _expected_paths(system)
    resource = root + ("/Resources" if system == "macos" else "")
    expected_names = {
        binary_path, manifest_path, resource + "/README-SYNTHETIC.txt",
        resource + "/LICENSE", resource + "/UPSTREAM-NOTICE.md",
    }
    if system == "macos":
        expected_names.update((root + "/Info.plist", root + "/PkgInfo"))

    payload: dict[str, tuple[bytes, int]] = {}
    if system == "linux":
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            if len(members) != len(expected_names) or {m.name for m in members} != expected_names:
                raise ValueError("unexpected_or_duplicate_archive_members")
            for member in members:
                if not member.isfile() or member.issym() or member.islnk():
                    raise ValueError("archive_must_contain_only_regular_files")
                limit = _member_limit(member.name, binary_path)
                if member.size < 0 or member.size > limit:
                    raise ValueError("oversized_member:" + member.name)
                reader = archive.extractfile(member)
                if reader is None:
                    raise ValueError("missing_archive_payload")
                data = reader.read(limit + 1)
                if len(data) != member.size:
                    raise ValueError("member_size_mismatch")
                payload[member.name] = (data, member.mode & 0o7777)
    else:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) != len(expected_names) or {m.filename for m in members} != expected_names:
                raise ValueError("unexpected_or_duplicate_archive_members")
            for member in members:
                mode = (member.external_attr >> 16)
                if (mode & 0o170000) != stat.S_IFREG or member.is_dir():
                    raise ValueError("archive_must_contain_only_regular_files")
                if member.flag_bits & 0x1:
                    raise ValueError("encrypted_archive_member")
                limit = _member_limit(member.filename, binary_path)
                if member.file_size > limit:
                    raise ValueError("oversized_member:" + member.filename)
                with archive.open(member, "r") as reader:
                    data = reader.read(limit + 1)
                if len(data) != member.file_size:
                    raise ValueError("member_size_mismatch")
                payload[member.filename] = (data, mode & 0o7777)

    if len(payload) != len(expected_names):
        raise ValueError("duplicate_archive_members")

    binary = payload[binary_path][0]
    if not 4096 <= len(binary) <= MAX_BINARY_BYTES:
        raise ValueError("native_binary_size_out_of_bounds")
    if inspect_native_header(binary) != (system, architecture):
        raise ValueError("native_executable_header_mismatch")

    manifest = json.loads(payload[manifest_path][0])
    if not isinstance(manifest, dict):
        raise ValueError("manifest_must_be_object")
    for flag in (
        "release_authorized", "clinical_use_authorized", "patient_data_supported",
        "zero_egress_qualified", "signed_or_notarized", "production_installer",
    ):
        if manifest.get(flag) is not False:
            raise ValueError("unsafe_manifest_claim:" + flag)
    if manifest.get("synthetic_only") is not True:
        raise ValueError("synthetic_scope_mismatch")
    if manifest.get("source_commit") != commit or manifest.get("binary_sha256") != digest(binary):
        raise ValueError("manifest_provenance_mismatch")

    # Compare all files, names, byte content and mode with the exact packaging
    # contract at the selected source commit (not merely suffixes or SHA claims).
    expected = files_for(
        binary, system, architecture, commit,
        (repo / "LICENSE").read_bytes(),
        (repo / "experiments" / "desktop-d2-native-egui" / "UPSTREAM-NOTICE.md").read_bytes(),
    )
    if payload != expected:
        raise ValueError("noncanonical_archive_content_or_permissions")

    print(json.dumps({
        "status": "SYNTHETIC_ARCHIVE_SOURCE_CONTRACT_VERIFIED_NOT_RELEASED",
        "archive": str(path), "archive_sha256": digest(path.read_bytes()),
        "binary_sha256": digest(binary), "system": system,
        "architecture": architecture, "source_commit": commit,
    }, sort_keys=True, indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--target", choices=(
        "linux-x86_64", "linux-arm64", "windows-x86_64", "windows-arm64",
        "macos-arm64", "macos-x86_64",
    ))
    args = parser.parse_args()
    try:
        verify_archive(args.archive, Path(__file__).resolve().parents[3], args.target)
    except (OSError, ValueError, KeyError, json.JSONDecodeError,
            tarfile.TarError, zipfile.BadZipFile, EOFError) as error:
        print("PREVIEW_INTEGRITY_REFUSED: " + str(error), file=sys.stderr)
        sys.exit(2)
