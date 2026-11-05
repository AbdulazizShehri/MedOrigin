"""Physical Windows process negative qualification of fictional Core -> native HMAC.
No patient data, network, persistent keys, arbitrary file picker or GUI success.
Run on a reviewed compiled binary with its exact SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
from pathlib import Path
import subprocess
import sys

import launch_windows_real_core963_fictional_batch as bridge

SOURCE = Path(__file__).resolve().parent.parent
RECEIPT = SOURCE / "fixtures/core/core963-real-encrypted-fictional-file-batch-redacted.json"
REVIEWED_RECEIPT_SHA = "34beba4dd887ab5e26fb8ceaf91d06f85a6ebaca349359aa0f9ecccb612d2292"


def qualify(exe: Path, sha256: str) -> None:
    if sys.platform != "win32" or exe.is_symlink() or exe.name != bridge.EXE_NAME:
        raise ValueError("unreviewed_windows_native_binary")
    exe = exe.resolve(strict=True)
    if not exe.is_file() or bridge._file_sha(exe) != sha256:
        raise ValueError("native_binary_sha_refused")
    raw = RECEIPT.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REVIEWED_RECEIPT_SHA:
        raise ValueError("fictional_core_receipt_mutated")
    bridge._verified_receipt(raw)
    nonce = bytes([0x5A]) * 16  # deterministic NEGATIVE ONLY; not production key material
    secret = bytes([0x39]) * 32
    valid = bridge._per_launch_core_frame(raw, nonce, secret)
    legacy_domain = b"MedOrigin-D2-FICTIONAL-SESSION-V1\x00"
    wrong_domain = (
        legacy_domain + nonce
        + hmac.new(secret, legacy_domain+nonce+len(raw).to_bytes(4,"big")+raw,hashlib.sha256).digest()
        + raw
    )
    env = {**os.environ, bridge.ENV_SESSION_KEY: secret.hex(),
           bridge.ENV_SESSION_NONCE: nonce.hex()}
    denials = (
        ("raw_unbound", raw, env),
        ("tampered", valid[:-1] + bytes([valid[-1] ^ 1]), env),
        ("stale_nonce", valid, {**env, bridge.ENV_SESSION_NONCE:(bytes([0x5B])*16).hex()}),
        ("wrong_domain", wrong_domain, env),
        ("missing_secret", valid,
         {k: v for k, v in os.environ.items()
          if k not in (bridge.ENV_SESSION_KEY, bridge.ENV_SESSION_NONCE)}),
        ("oversize", b"x" * 5000, env),
    )
    for label, framed, vars_for_test in denials:
        try:
            child = subprocess.run(
                [str(exe), bridge.D2_SESSION_BATCH_FLAG],
                cwd=exe.parent,
                input=framed,
                env=vars_for_test,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=6,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("forbidden_gui_started_in_negative_"+label) from exc
        if child.returncode == 0:
            raise ValueError("invalid_hmac_frame_accepted_"+label)
        print("BOUND_FRAME_DENIAL_"+label.upper()+"_PASS")
    print("ALL_SIX_REAL_NATIVE_HMAC_NEGATIVES_PASS_NONCLINICAL")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-exe", required=True, type=Path)
    parser.add_argument("--native-sha256", required=True)
    try:
        args = parser.parse_args()
        qualify(args.native_exe, args.native_sha256)
    except (ValueError, OSError) as exc:
        print("CORE963_HMAC_NATIVE_NEGATIVE_NO_GO:"+str(exc), file=sys.stderr)
        raise SystemExit(2) from None
