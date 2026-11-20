#!/usr/bin/env python3
"""Actual Windows GUI must reject stale/replayed/modified fictional Core frames.

No valid GUI window is intentionally created in this negative suite. This is
only a private developer process-bound MAC proof, not secure production IPC.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from fictional_session_frame import (
    KEY_ENV,
    NONCE_ENV,
    SESSION_FLAG,
    SESSION_FOCUSED_FLAG,
    frame_one_time_fictional_core,
    fresh_ephemeral_session,
)
from qualify_windows_encrypted_readback_native_gui import PROJECTION_SHA, sha

PASS = "WINDOWS_NATIVE_D2_FICTIONAL_SESSION_REPLAY_AND_MAC_REFUSALS_PASS_NONCLINICAL"


def qualify(native_gui: Path, native_sha: str) -> None:
    if sys.platform != "win32":
        raise ValueError("actual_windows_required")
    if native_gui.is_symlink():
        raise ValueError("native_reparse_point_refused")
    gui = native_gui.resolve(strict=True)
    if gui.name != "medorigin-desktop-d2-native-egui.exe" or sha(gui) != native_sha.lower():
        raise ValueError("native_gui_reviewed_binary_mismatch")
    fixture = (
        Path(__file__).resolve().parent.parent / "fixtures/core/encrypted-readback-projection.json"
    )
    if fixture.is_symlink() or sha(fixture) != PROJECTION_SHA:
        raise ValueError("fictional_fixture_identity_refused")
    raw = fixture.read_bytes()
    nonce, key = fresh_ephemeral_session()
    frame = frame_one_time_fictional_core(raw, nonce, key)
    baseline = {
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"),
        "WINDIR": os.environ.get("SYSTEMROOT", r"C:\Windows"),
        "PATH": str(gui.parent),
    }
    cases = (
        (
            "fresh-session-frame-in-legacy-mode",
            "--synthetic-encrypted-readback-stdin",
            frame,
            nonce,
            key,
        ),
        ("unframed-source-in-session-mode", SESSION_FLAG, raw, nonce, key),
        (
            "session-frame-in-focused-unframed-source-mode",
            "--synthetic-encrypted-readback-focused-stdin",
            frame,
            nonce,
            key,
        ),
        ("unframed-source-in-focused-session-mode", SESSION_FOCUSED_FLAG, raw, nonce, key),
        ("stale-focused-session-nonce", SESSION_FOCUSED_FLAG, frame, b"\x10" * 16, key),
        ("foreign-focused-session-secret", SESSION_FOCUSED_FLAG, frame, nonce, b"\x11" * 32),
        (
            "tampered-focused-session-payload",
            SESSION_FOCUSED_FLAG,
            frame[:-1] + bytes([frame[-1] ^ 1]),
            nonce,
            key,
        ),
        ("stale-replayed-nonce", SESSION_FLAG, frame, b"\x10" * 16, key),
        ("foreign-session-secret", SESSION_FLAG, frame, nonce, b"\x11" * 32),
        ("tampered-payload", SESSION_FLAG, frame[:-1] + bytes([frame[-1] ^ 1]), nonce, key),
        (
            "tampered-mac",
            SESSION_FLAG,
            frame[: len(frame) - 1164 - 32]
            + bytes([frame[len(frame) - 1164 - 32] ^ 1])
            + frame[len(frame) - 1164 - 31 :],
            nonce,
            key,
        ),
    )
    for label, flag, submitted, current_nonce, current_key in cases:
        env = dict(baseline, **{NONCE_ENV: current_nonce.hex(), KEY_ENV: current_key.hex()})
        try:
            outcome = subprocess.run(
                [str(gui), flag],
                input=submitted,
                env=env,
                capture_output=True,
                timeout=8,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ValueError("unapproved_native_GUI_launched_on_" + label) from error
        if outcome.returncode == 0:
            raise ValueError("native_replay_or_mac_forgery_accepted_" + label)
        print("WINDOWS_NATIVE_SESSION_NO_GO_CONFIRMED_" + label)
    print(PASS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-gui", type=Path, required=True)
    parser.add_argument("--native-sha", type=str, required=True)
    try:
        args = parser.parse_args()
        qualify(args.native_gui, args.native_sha)
    except (OSError, ValueError, subprocess.SubprocessError):
        print("WINDOWS_FICTIONAL_SESSION_NATIVE_REFUSAL_QA_FAILED", file=sys.stderr)
        raise SystemExit(2) from None
