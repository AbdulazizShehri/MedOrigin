#!/usr/bin/env python3
"""Verify a synthetic-only D2 portable archive; not clinical/security clearance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tarfile
import zipfile

from package_preview import (
    APP, BINARY, commit_of, digest, inspect_native_header, selected_target
)


def verify_archive(path: Path, repo: Path, target: str | None = None) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError("expected_regular_archive")
    system, architecture = selected_target(target)
    if system == "linux" and not str(path).endswith(".tar.gz"):
        raise ValueError("linux_archive_requires_tar_gz")
    if system != "linux" and path.suffix != ".zip":
        raise ValueError("desktop_archive_requires_zip")
    payload: dict[str, tuple[bytes, int]] = {}
    if system == "linux":
        with tarfile.open(path, "r:gz") as z:
            for info in z:
                if not info.isfile() or info.issym() or info.islnk():
                    raise ValueError("no_links_or_special_files")
                reader = z.extractfile(info)
                if reader is None:
                    raise ValueError("missing_archive_payload")
                payload[info.name] = (reader.read(), info.mode)
    else:
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir():
                    raise ValueError("no_unexpected_directory_entries")
                mode = (info.external_attr >> 16) & 0o777
                payload[info.filename] = (z.read(info), mode)
    if len(payload) not in (5, 7):
        raise ValueError("unexpected_file_count")
    if not all(name and not name.startswith("/") and ".." not in Path(name).parts
               for name in payload):
        raise ValueError("unsafe_archive_paths")
    manifests = [name for name in payload if name.endswith("/MANIFEST.json")]
    binaries = [name for name in payload if name.endswith(
        "/"+BINARY+(".exe" if system == "windows" else ""))]
    if len(manifests) != 1 or len(binaries) != 1:
        raise ValueError("missing_or_multiple_manifest_or_executable")
    info = json.loads(payload[manifests[0]][0])
    if info.get("schema") != "medorigin-d2-synthetic-archive-v1":
        raise ValueError("unknown_manifest_schema")
    for flag in ("release_authorized", "clinical_use_authorized", "patient_data_supported",
                 "zero_egress_qualified", "signed_or_notarized", "production_installer"):
        if info.get(flag) is not False:
            raise ValueError("unsafe_manifest_claim:"+flag)
    if info.get("synthetic_only") is not True or info.get("name") != APP:
        raise ValueError("synthetic_scope_mismatch")
    if info.get("platform") != system or info.get("architecture") != architecture:
        raise ValueError("host_manifest_mismatch")
    if info.get("source_commit") != commit_of(repo):
        raise ValueError("unexpected_source_commit")
    binary = payload[binaries[0]][0]
    if inspect_native_header(binary) != (system, architecture):
        raise ValueError("native_executable_header_mismatch")
    if info.get("binary_sha256") != digest(binary):
        raise ValueError("binary_sha256_mismatch")
    if (payload[binaries[0]][1] & 0o111) != 0o111:
        raise ValueError("executable_mode_not_preserved")
    if not any(name.endswith("/README-SYNTHETIC.txt") and
               b"NOT FOR PATIENT DATA" in data for name, (data, _) in payload.items()):
        raise ValueError("missing_safety_notice")
    if not any(name.endswith("/LICENSE") for name in payload):
        raise ValueError("missing_license")
    if not any(name.endswith("/UPSTREAM-NOTICE.md") for name in payload):
        raise ValueError("missing_upstream_notice")
    if system == "macos" and not any(name.endswith("/Contents/Info.plist") for name in payload):
        raise ValueError("missing_app_bundle_info")
    print(json.dumps({
        "status": "SYNTHETIC_PORTABLE_ARCHIVE_INTEGRITY_VERIFIED_NOT_RELEASED",
        "archive": str(path), "archive_sha256": digest(path.read_bytes()),
        "binary_sha256": digest(binary), "system": system, "architecture": architecture,
        "source_commit": info["source_commit"],
    }, sort_keys=True, indent=2))
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--target", choices=("linux-x86_64", "linux-arm64", "windows-x86_64",
                                            "windows-arm64", "macos-arm64", "macos-x86_64"))
    args = parser.parse_args()
    try:
        verify_archive(args.archive, Path(__file__).resolve().parents[3], args.target)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print("PREVIEW_INTEGRITY_REFUSED: "+str(error), file=sys.stderr)
        sys.exit(2)
