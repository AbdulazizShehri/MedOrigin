#!/usr/bin/env python3
"""Real native Windows D2 GUI from a different process's persisted fictional Core.

Private pinned source GUI qualification only. The exact three invented FHIR
records are actually read back from a user-DPAPI-protected test-only Workspace.
No PHI, production key resolver, clinical claims, network, or release.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fictional_session_frame import frame_one_time_fictional_core, fresh_ephemeral_session
from launch_windows_portable_fictional_core import _launch_gui, _qa_native_clicks
from qualify_windows_encrypted_readback_native_gui import sha
from supervise_windows_encrypted_core_job import execute_encrypted_source_under_job
from windows_fictional_persistent_vault import QA_DIR_NAME

EXPECTED_SOURCE_SHA = "3673eb77b2dbef25fd6cb33d9c345d2f37d38a86bcf1652ed9defae4da139243"
SUCCESS = (
    "WINDOWS_REAL_PERSISTENT_FICTIONAL_AESGCM_DPAPI_COLD_REOPEN_TO_NATIVE_D2_PASS_NOT_CLINICAL"
)


def qualify(args: argparse.Namespace) -> None:
    if sys.platform != "win32":
        raise ValueError("windows_native_qa_required")
    for p in (args.python, args.site, args.core_source, args.native_gui, args.qa_root):
        if p.is_symlink():
            raise ValueError("fictional_qa_reparse_point_refused")
    python = args.python.resolve(strict=True)
    site = args.site.resolve(strict=True)
    core = args.core_source.resolve(strict=True)
    gui = args.native_gui.resolve(strict=True)
    qa_root = args.qa_root.resolve(strict=True)
    if (
        not python.is_file()
        or python.name != "python.exe"
        or sha(python) != args.python_sha.lower()
        or not site.is_dir()
        or not core.is_dir()
        or gui.name != "medorigin-desktop-d2-native-egui.exe"
        or sha(gui) != args.native_sha.lower()
        or qa_root.name != QA_DIR_NAME
    ):
        raise ValueError("reviewed_persistent_core_native_qa_prerequisites_refused")
    root = Path(__file__).resolve().parent.parent
    exporter = root / "scripts/windows_fictional_persistent_vault.py"
    fixture = root / "fixtures/core/encrypted-persistent-readback-projection.json"
    if sha(fixture) != EXPECTED_SOURCE_SHA or exporter.is_symlink():
        raise ValueError("reviewed_persistent_qa_fixture_or_exporter_refused")
    with TemporaryDirectory(prefix="medorigin-d2-persistent-native-qa-") as scratch:
        work = Path(scratch).resolve()
        raw = execute_encrypted_source_under_job(
            python,
            core,
            site,
            exporter,
            work,
            persistent_qa_root=qa_root,
        )
        if (
            len(raw) != 1215
            or raw != fixture.read_bytes()
            or hashlib.sha256(raw).hexdigest() != EXPECTED_SOURCE_SHA
        ):
            raise ValueError("real_persistent_fictional_worker_source_mismatch")
        print("WINDOWS_REAL_PERSISTENT_FICTIONAL_SOURCE_CONTENT_REOPENED_JOB_BOUND")
        nonce, secret = fresh_ephemeral_session()
        framed = frame_one_time_fictional_core(raw, nonce, secret)
        if args.qa_uia:
            _qa_native_clicks(
                root,
                gui,
                work,
                raw,
                framed,
                nonce,
                secret,
                persistent=True,
            )
        else:
            _launch_gui(
                gui,
                framed,
                work,
                qa_auto_close=True,
                nonce=nonce,
                key=secret,
            )
    print(SUCCESS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("core-source", "python", "site", "native-gui", "qa-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--python-sha", required=True)
    parser.add_argument("--native-sha", required=True)
    parser.add_argument("--qa-uia", action="store_true")
    try:
        qualify(parser.parse_args())
    except (ValueError, OSError, subprocess.SubprocessError):
        print("WINDOWS_PERSISTENT_FICTIONAL_CORE_NATIVE_QA_NO_GO", file=sys.stderr)
        raise SystemExit(2) from None
