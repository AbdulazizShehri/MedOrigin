"""Per-launch HMAC frame for a reviewed fictional-only Core projection.

The owner alone generates a fresh random nonce and key for each GUI process.
This blocks naive static byte replay / corruption, but passing an environment
secret is NOT an OS-authenticated sender, secure key custody, or patient IPC.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

MAGIC = b"MedOrigin-D2-FICTIONAL-SESSION-V1\0"
SESSION_FLAG = "--synthetic-encrypted-readback-session-stdin"
SESSION_FOCUSED_FLAG = "--synthetic-encrypted-readback-session-focused-stdin"
KEY_ENV = "MEDORIGIN_D2_FICTIONAL_SESSION_KEY"
NONCE_ENV = "MEDORIGIN_D2_FICTIONAL_SESSION_NONCE"
MAX_FRAME = 2048
REVIEWED_RAW_SIZE = 1164
REVIEWED_RAW_SHA = "c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49"
REVIEWED_PERSISTENT_RAW_SIZE = 1215
REVIEWED_PERSISTENT_RAW_SHA = "3673eb77b2dbef25fd6cb33d9c345d2f37d38a86bcf1652ed9defae4da139243"


def fresh_ephemeral_session() -> tuple[bytes, bytes]:
    return secrets.token_bytes(16), secrets.token_bytes(32)


def frame_one_time_fictional_core(raw: bytes, nonce: bytes, key: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or (len(raw), hashlib.sha256(raw).hexdigest())
        not in (
            (REVIEWED_RAW_SIZE, REVIEWED_RAW_SHA),
            (REVIEWED_PERSISTENT_RAW_SIZE, REVIEWED_PERSISTENT_RAW_SHA),
        )
        or type(nonce) is not bytes
        or len(nonce) != 16
        or type(key) is not bytes
        or len(key) != 32
    ):
        raise ValueError("fictional_core_session_unreviewed_data_or_secret")
    authenticated = MAGIC + nonce + len(raw).to_bytes(4, "big") + raw
    mac = hmac.new(key, authenticated, hashlib.sha256).digest()
    framed = MAGIC + nonce + mac + raw
    if len(framed) > MAX_FRAME:
        raise ValueError("fictional_session_frame_oversized")
    return framed
