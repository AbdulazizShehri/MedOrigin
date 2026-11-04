"""Fictional-only D2 per-launch HMAC session frame adversarial tests."""

from __future__ import annotations

import hashlib
import hmac
import unittest
from pathlib import Path
from unittest.mock import patch

import fictional_session_frame as qa


class FictionalSessionFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.approved = (
            Path(__file__).resolve().parent.parent
            / "fixtures/core/encrypted-readback-projection.json"
        ).read_bytes()
        assert len(cls.approved) == 1164
        assert hashlib.sha256(cls.approved).hexdigest() == qa.REVIEWED_RAW_SHA

    def test_known_hmac_sha256_golden_agrees_with_rust_session(self):
        self.assertEqual(
            hmac.new(bytes([0x3B]) * 32, b"hello", hashlib.sha256).hexdigest(),
            "5a72ba66ff1caa9cb76fd3b027019532b7d763ce84f7ffa360e4c3b88f7dcea4",
        )

    def test_fresh_random_key_nonce_and_exact_canonical_projection(self):
        one_nonce, one_key = qa.fresh_ephemeral_session()
        next_nonce, next_key = qa.fresh_ephemeral_session()
        self.assertEqual((len(one_nonce), len(one_key)), (16, 32))
        self.assertNotEqual((one_nonce, one_key), (next_nonce, next_key))
        envelope = qa.frame_one_time_fictional_core(self.approved, one_nonce, one_key)
        self.assertLessEqual(len(envelope), 2048)
        self.assertEqual(envelope[: len(qa.MAGIC)], qa.MAGIC)
        self.assertEqual(envelope[len(qa.MAGIC) : len(qa.MAGIC) + 16], one_nonce)
        self.assertEqual(envelope[-1164:], self.approved)
        signed = qa.MAGIC + one_nonce + len(self.approved).to_bytes(4, "big") + self.approved
        expected = hmac.new(one_key, signed, hashlib.sha256).digest()
        self.assertEqual(envelope[len(qa.MAGIC) + 16 : -1164], expected)

    def test_unapproved_bytes_even_json_whitespace_refused(self):
        nonce, key = qa.fresh_ephemeral_session()
        for raw in (b"", b"{}", self.approved + b"\n", self.approved[:-1]):
            with self.assertRaisesRegex(ValueError, "unreviewed_data_or_secret"):
                qa.frame_one_time_fictional_core(raw, nonce, key)

    def test_wrong_session_key_nonce_and_implicit_payload_type_refused(self):
        nonce, key = qa.fresh_ephemeral_session()
        for args in (
            (self.approved, b"short", key),
            (self.approved, nonce, b"too-short"),
            (bytearray(self.approved), nonce, key),
            (self.approved, bytearray(nonce), key),
        ):
            with self.assertRaisesRegex(ValueError, "unreviewed_data_or_secret"):
                qa.frame_one_time_fictional_core(*args)

    def test_random_generator_is_only_used_explicitly_and_never_stored(self):
        with patch.object(qa.secrets, "token_bytes", side_effect=[b"n" * 16, b"k" * 32]):
            self.assertEqual(qa.fresh_ephemeral_session(), (b"n" * 16, b"k" * 32))
        source = Path(qa.__file__).read_text(encoding="utf-8")
        self.assertNotIn("random.Random", source)
        self.assertNotIn("os.environ[", source)
        self.assertNotIn(".write_bytes(", source)


if __name__ == "__main__":
    unittest.main()
