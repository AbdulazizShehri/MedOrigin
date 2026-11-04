#!/usr/bin/env python3
"""Prepare private Windows fictional-only Core+native GUI kit from attested Wheels.

Offline dev artifact, never a clinical installer. Preparation requires the
historical reviewed source checkout; running the prepared kit does NOT.
No automatic download, signing, publication or patient imports.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from attest_installed_encrypted_core_readback import PINNED_CORE_SHA, attest_installed
from launch_windows_installed_fictional_core import WINDOWS_APPROVED_WHEELS
from portable_core_tree import (
    APPROVED_TREE_SHA256,
    attest_portable_core_tree,
    digest_installed_packages,
)
from qualify_windows_encrypted_readback_native_gui import PROJECTION_SHA, sha

RUNTIME_SCRIPTS = (
    "launch_windows_portable_fictional_core.py",
    "fictional_session_frame.py",
    "portable_core_tree.py",
    "supervise_windows_encrypted_core_job.py",
    "qualify_windows_job_subtree.py",
    "synthetic_encrypted_readback_projection.py",
    "launch_windows_encrypted_fictional_preview.py",
    "qualify_windows_encrypted_readback_native_gui.py",
)
SOURCE_EXTRAS = (
    "fixtures/core/encrypted-readback-projection.json",
    "tests/windows-encrypted-core-readback-uia.ps1",
)
LAUNCHER_NAME = "medorigin-desktop-d2-native-egui.exe"
MANIFEST_SCHEMA = "medorigin-d2-private-portable-fictional-core-windows/v1"


def prepare(args: argparse.Namespace) -> Path:
    if sys.platform != "win32":
        raise ValueError("Windows_preparation_only")
    inputs = (args.core_source, args.wheels, args.installed_site, args.native_gui)
    if any(p.is_symlink() for p in inputs):
        raise ValueError("unreviewed_preparation_reparse_point")
    core, wheels, site, native = (p.resolve(strict=True) for p in inputs)
    if (
        native.name != LAUNCHER_NAME
        or not native.is_file()
        or len(args.native_sha) != 64
        or sha(native) != args.native_sha.lower()
    ):
        raise ValueError("unreviewed_native_gui_executable")
    destination = args.out.absolute()
    if (
        destination.exists()
        or destination.is_symlink()
        or destination.parent.is_symlink()
        or not destination.parent.is_dir()
    ):
        raise ValueError("portable_bundle_destination_must_not_exist")
    attest_installed(core, wheels, site, approved_wheels=WINDOWS_APPROVED_WHEELS)
    if digest_installed_packages(site) != APPROVED_TREE_SHA256:
        raise ValueError("installed_source_tree_changed_from_reviewed_git")
    source_root = Path(__file__).resolve().parent.parent
    srcs = {f"scripts/{name}": source_root / "scripts" / name for name in RUNTIME_SCRIPTS}
    srcs.update({name: source_root / name for name in SOURCE_EXTRAS})
    for name, source in srcs.items():
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"reviewed_runtime_bundle_source_missing:{name}")
    if sha(srcs["fixtures/core/encrypted-readback-projection.json"]) != PROJECTION_SHA:
        raise ValueError("reviewed_fictional_bundle_projection_changed")
    with TemporaryDirectory(
        prefix="medorigin-private-portable-staging-", dir=destination.parent
    ) as temp:
        stage = Path(temp)
        (stage / "core").mkdir()
        for package in ("medscale", "medscale_workspace"):
            shutil.copytree(site / package, stage / "core" / package, symlinks=False)
        attest_portable_core_tree(stage / "core")
        for name, source in srcs.items():
            target = stage / name
            target.parent.mkdir(exist_ok=True, parents=True)
            shutil.copyfile(source, target, follow_symlinks=False)
        (stage / "native").mkdir()
        shutil.copyfile(native, stage / "native" / LAUNCHER_NAME)
        if sha(stage / "native" / LAUNCHER_NAME) != args.native_sha.lower():
            raise ValueError("native_gui_copy_checksum_changed")
        files = {name: sha(stage / name) for name in sorted(srcs)}
        files[f"native/{LAUNCHER_NAME}"] = args.native_sha.lower()
        document = {
            "schema": MANIFEST_SCHEMA,
            "source_commit": PINNED_CORE_SHA,
            "core_sha256": APPROVED_TREE_SHA256,
            "source_file_count": 290,
            "generated_by": "offline_source_attested_developer_tool",
            "production_or_clinical_use_authorized": False,
            "sender_or_session_authenticated": False,
            "os_network_egress_confined": False,
            "files_sha256": dict(sorted(files.items())),
        }
        (stage / "manifest.json").write_text(
            json.dumps(document, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        if (
            destination.exists()
            or destination.is_symlink()
            or sha(native) != args.native_sha.lower()
        ):
            raise ValueError("portable_destination_or_native_changed")
        attest_installed(core, wheels, site, approved_wheels=WINDOWS_APPROVED_WHEELS)
        stage.rename(destination)
    print("WINDOWS_PORTABLE_290_BYTE_ATTESTED_FICTIONAL_CORE_BUNDLE_PREPARED_NOT_CLINICAL")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("core-source", "wheels", "installed-site", "native-gui", "out"):
        parser.add_argument("--" + field, type=Path, required=True)
    parser.add_argument("--native-sha", type=str, required=True)
    try:
        prepare(parser.parse_args())
    except (OSError, ValueError, shutil.Error):
        print("WINDOWS_FICTIONAL_PORTABLE_PREPARATION_REFUSED", file=sys.stderr)
        raise SystemExit(2) from None
