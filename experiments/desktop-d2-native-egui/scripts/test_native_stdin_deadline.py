"""No-dependency source and refusal regression checks for bounded native D2 stdin."""

from __future__ import annotations

import sys
import unittest
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_native_stdin_deadline as qa

ROOT = Path(__file__).resolve().parent.parent


class NativeOneShotDeadlineTests(unittest.TestCase):
    def test_native_requires_explicit_mode_and_bounded_deadline(self):
        source = (ROOT / "src/main.rs").read_text(encoding="utf-8")
        self.assertIn(
            "const SYNTHETIC_CORE_STDIN_DEADLINE: Duration = Duration::from_secs(5)", source
        )
        self.assertIn("mpsc::sync_channel(1)", source)
        self.assertIn("recv_timeout(deadline)", source)
        self.assertIn("Err(RecvTimeoutError::Timeout)", source)
        self.assertIn('"synthetic_core_stdin_deadline_refused"', source)
        self.assertIn("fn complete_report_without_eof_is_not_accepted()", source)
        self.assertIn(
            "fn stalled_one_shot_stdin_refuses_on_deadline_without_starting_gui()", source
        )
        self.assertIn("if args.is_empty()", source)
        self.assertIn("let app = make_app(&args, io::stdin())?", source)
        self.assertNotIn("std::process::Command", source)
        self.assertNotIn("std::net::", source)

    def test_stale_input_exact_attestation_refuses_unapproved_binary_before_spawn(self):
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / qa.EXPECTED_NAME
            file.write_bytes(b"fake fictional shell-free test executable")
            with mock.patch.object(qa.subprocess, "Popen") as mock_spawn:
                with self.assertRaisesRegex(ValueError, "native_gui_binary_sha_mismatch"):
                    qa.qualify(file, "0" * 64)
                mock_spawn.assert_not_called()

    def test_missing_symlink_and_unapproved_hash_are_refused_without_process(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / qa.EXPECTED_NAME
            # Some Windows hosts disallow nonprivileged symlinks. The
            # missing-file/hash refusal must still be tested there.
            with suppress(OSError, NotImplementedError):
                file.symlink_to(root / "outside-missing")
            with mock.patch.object(qa.subprocess, "Popen") as mock_spawn:
                with self.assertRaisesRegex(ValueError, "binary_identity_invalid"):
                    qa.qualify(file, "0" * 64)
                with self.assertRaisesRegex(ValueError, "expected_sha_invalid"):
                    qa.qualify(file, "wrong")
                mock_spawn.assert_not_called()

    def test_local_runtime_qualification_covers_idle_partial_and_exact_source(self):
        source = Path(qa.__file__).read_text(encoding="utf-8")
        self.assertEqual(qa.MAX_WAIT, 8.0)
        self.assertIn("('idle', b'')", source.replace('"', "'"))
        self.assertIn("valid_bytes_without_eof", source)
        self.assertIn("process.stdin.write(payload)", source)
        self.assertIn("process.wait(timeout=MAX_WAIT)", source)
        self.assertIn("native_gui_stdin_hung_instead_of_refusing", source)
        self.assertIn(
            "D2_NATIVE_SYNTHETIC_STDIN_DEADLINE_IDLE_AND_MISSING_EOF_PASS_NOT_RELEASE", source
        )
        self.assertEqual(
            qa.KNOWN_SHA, "165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08"
        )


if __name__ == "__main__":
    unittest.main()
