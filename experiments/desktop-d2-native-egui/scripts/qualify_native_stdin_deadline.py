#!/usr/bin/env python3
"""Real D2 native executable abandoned Core stdin safety qualification.

Runs exactly two source-fixed, fictional timeout probes; no online calls, PHI,
EHR, user data, arbitrary options or installer. Windows/macOS/Linux local QA.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
MAX_WAIT = 8.0
EXPECTED_NAME = "medorigin-desktop-d2-native-egui" + (
    ".exe" if sys.platform == "win32" else ""
)
KNOWN_REPORT = ROOT / "fixtures/core/known-structure-definition.json"
KNOWN_SHA = "165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08"
SUCCESS = "D2_NATIVE_SYNTHETIC_STDIN_DEADLINE_IDLE_AND_MISSING_EOF_PASS_NOT_RELEASE"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(binary: Path, digest: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{64}", digest.lower()):
        raise ValueError("native_gui_expected_sha_invalid")
    if binary.is_symlink() or not binary.is_file() or binary.name != EXPECTED_NAME:
        raise ValueError("native_gui_binary_identity_invalid")
    binary = binary.resolve(strict=True)
    if sha256(binary) != digest.lower():
        raise ValueError("native_gui_binary_sha_mismatch")
    if KNOWN_REPORT.is_symlink() or sha256(KNOWN_REPORT) != KNOWN_SHA:
        raise ValueError("source_fixed_core_report_changed")
    known = KNOWN_REPORT.read_bytes()
    if not 10 <= len(known) <= 2048:
        raise ValueError("source_fixed_core_report_length_changed")
    for label, payload in (("idle", b""), ("valid_bytes_without_eof", known)):
        start = time.monotonic()
        process = subprocess.Popen(
            [str(binary), "--synthetic-core-stdin"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            assert process.stdin is not None
            if payload:
                process.stdin.write(payload)
                process.stdin.flush()
            # Deliberately keep stdin OPEN: the abandoned parent must NOT
            # block the native GUI's application initialization forever.
            try:
                process.wait(timeout=MAX_WAIT)
            except subprocess.TimeoutExpired as exc:
                raise ValueError("native_gui_stdin_hung_instead_of_refusing") from exc
            if process.returncode == 0:
                raise ValueError("native_gui_accepted_incomplete_stdin_no_eof")
            elapsed = time.monotonic() - start
            if elapsed > MAX_WAIT:
                raise ValueError("native_gui_stdin_deadline_exceeded")
            print(f"NATIVE_SYNTHETIC_STDIN_DEADLINE_PASS {label} exit={process.returncode}")
        finally:
            if process.stdin:
                process.stdin.close()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)
            if process.stderr:
                process.stderr.close()
    if sha256(binary) != digest.lower():
        raise ValueError("native_gui_binary_mutated_after_tests")
    print(SUCCESS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-gui", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    try:
        qualify(args.native_gui, args.sha256)
    except (ValueError, OSError, subprocess.SubprocessError, AssertionError) as error:
        print("D2_NATIVE_SYNTHETIC_STDIN_DEADLINE_NO_GO:" + str(error), file=sys.stderr)
        sys.exit(2)
