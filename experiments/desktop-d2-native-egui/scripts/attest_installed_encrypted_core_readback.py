#!/usr/bin/env python3
"""Attest exact Git -> offline Wheel -> installed Python Core/Workspace sources.

Private fictional-only desktop qualification. This proves the two PURE-PYTHON
packages' approved bytes, NOT crypto/native extension supply chain, Windows
process isolation, authenticated IPC, patient safety, or release eligibility.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import zipfile
from pathlib import Path

PINNED_CORE_SHA = "8e5ed5430f4ab2ebc8981c52c67234023382954b"
EXPECTED_WHEELS = (
    (
        "medscale",
        "src/medscale",
        "medscale-0.3.0-py3-none-any.whl",
        "9b43d0c48678234838d6b76ea794741e8bafe78338c55aa2c7ccbc7e8d22adc8",
        256,
    ),
    (
        "medscale_workspace",
        "apps/workspace/src/medscale_workspace",
        "medscale_workspace-0.1.0.dev1-py3-none-any.whl",
        "1eedca3fb868e916e3597f7e158ca81fdc56475410d9e7534c6a82797f78b703",
        34,
    ),
)
EXPECTED_SITE = {
    "bin",
    "medscale",
    "medscale_workspace",
    "medscale-0.3.0.dist-info",
    "medscale_workspace-0.1.0.dev1.dist-info",
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_files(core: Path, section: str, count: int) -> dict[str, Path]:
    listing = subprocess.run(
        [
            "git" if os.name == "nt" else "/usr/bin/git",
            "-C",
            str(core),
            "ls-files",
            "-z",
            "--",
            section,
        ],
        capture_output=True,
        check=True,
        timeout=12,
    ).stdout
    names = [x.decode("utf-8") for x in listing.split(b"\x00") if x]
    if len(names) != count or len(set(names)) != count:
        raise ValueError("pinned_source_inventory_count_mismatch")
    inventory = {}
    for name in names:
        expected = name.removeprefix("src/").removeprefix("apps/workspace/src/")
        path = core / name
        if (
            path.is_symlink()
            or not path.is_file()
            or not name.startswith(section + "/")
            or not expected.startswith(section.split("/")[-1] + "/")
        ):
            raise ValueError("pinned_source_file_identity_refused")
        inventory[expected] = path
    # Git ignores Python bytecode, which can shadow reviewed code.
    seen = set()
    for file in (core / section).rglob("*"):
        if file.is_symlink() or (file.is_dir() and file.name == "__pycache__"):
            raise ValueError("unreviewed_source_symlink_or_bytecode")
        if file.is_file():
            seen.add(file.relative_to(core).as_posix())
    if seen != set(names):
        raise ValueError("unreviewed_ignored_or_missing_source")
    return inventory


def attest_installed(
    core: Path,
    wheels: Path,
    site: Path,
    *,
    approved_wheels: tuple[tuple[str, str, str, str, int], ...] | None = None,
) -> None:
    for path in (core, wheels, site):
        if path.is_symlink() or not path.is_dir():
            raise ValueError("untrusted_core_wheels_or_site_directory")
    head = subprocess.run(
        ["git" if os.name == "nt" else "/usr/bin/git", "-C", str(core), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        timeout=12,
    ).stdout.strip()
    if head != PINNED_CORE_SHA:
        raise ValueError("core_source_sha_changed")
    dirty = subprocess.run(
        [
            "git" if os.name == "nt" else "/usr/bin/git",
            "-C",
            str(core),
            "status",
            "--porcelain",
            "--untracked-files=all",
        ],
        capture_output=True,
        check=True,
        timeout=12,
    ).stdout
    if dirty:
        raise ValueError("reviewed_core_git_checkout_modified")
    if {entry.name for entry in site.iterdir()} != EXPECTED_SITE:
        raise ValueError("installed_python_site_unreviewed_top_level_entry")
    for entry in site.rglob("*"):
        if entry.is_symlink() or (entry.is_dir() and entry.name == "__pycache__"):
            raise ValueError("installed_python_site_symlink_or_bytecode_refused")
        if entry.is_file() and entry.suffix.lower() in (
            ".pyc",
            ".pyo",
            ".pyd",
            ".dll",
            ".so",
            ".dylib",
            ".pth",
        ):
            raise ValueError("installed_python_site_executable_shadow_refused")
    pins = EXPECTED_WHEELS if approved_wheels is None else approved_wheels
    if len(pins) != 2 or {row[0] for row in pins} != {"medscale", "medscale_workspace"}:
        raise ValueError("two_exact_approved_wheel_packages_required")
    for package, section, filename, approved_sha, count in pins:
        wheel = wheels / filename
        if wheel.is_symlink() or not wheel.is_file() or sha256(wheel.read_bytes()) != approved_sha:
            raise ValueError("approved_offline_wheel_content_mismatch")
        expected = source_files(core, section, count)
        with zipfile.ZipFile(wheel) as archive:
            members = archive.namelist()
            package_members = [item for item in members if item.startswith(package + "/")]
            if len(set(members)) != len(members) or set(package_members) != set(expected):
                raise ValueError("wheel_does_not_match_approved_git_source_inventory")
            for name, git_source in expected.items():
                installed = site / name
                if (
                    installed.is_symlink()
                    or not installed.is_file()
                    or archive.read(name) != git_source.read_bytes()
                    or installed.read_bytes() != git_source.read_bytes()
                ):
                    raise ValueError("installed_core_wheel_module_not_git_source_exact")
    print("TWO_OFFLINE_WHEELS_AND_290_INSTALLED_SOURCE_FILES_BYTE_ATTESTED_NOT_CLINICAL")
