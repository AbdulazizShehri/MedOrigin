"""Regression tests for source-verified extracted private Windows GUI archive."""

from __future__ import annotations

import hashlib
import io
import struct
import subprocess
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import package_preview as package
import qualify_windows_extracted_portable_gui as qa
import verify_preview as verify


def fake_windows_binary() -> bytes:
    raw = bytearray(4096)
    raw[:2] = b"MZ"
    struct.pack_into("<I", raw, 0x3C, 128)
    raw[128:132] = b"PE" + bytes([0, 0])
    struct.pack_into("<H", raw, 132, 0x8664)
    return bytes(raw)


class ExtractedPortableWindowsGuiTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = TemporaryDirectory(prefix="d2-extracted-archive-unit-")
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.source = self.work / "reviewed-source"
        self.scratch = self.work / "private-scratch"
        self.out = self.work / "private-out"
        self.source.mkdir()
        self.scratch.mkdir()
        self.out.mkdir()
        self.git_sha = "a" * 40
        self.data = fake_windows_binary()
        self.exe_sha = hashlib.sha256(self.data).hexdigest()
        (self.source / "LICENSE").write_bytes(b"Apache-2.0")
        desktop = self.source / "experiments" / "desktop-d2-native-egui"
        (desktop / "tests").mkdir(parents=True)
        (desktop / "UPSTREAM-NOTICE.md").write_bytes(b"Attribution")
        for name, _, _ in qa.TESTS:
            (desktop / "tests" / name).write_text("# fictional-only source test", encoding="utf-8")
        files = package.files_for(
            self.data,
            "windows",
            "x86_64",
            self.git_sha,
            b"Apache-2.0",
            b"Attribution",
        )
        self.archive = self.out / (
            "MedOrigin-Synthetic-D2-windows-x86_64-" + self.git_sha[:8] + ".zip"
        )
        package.write_archive(self.archive, files, "windows")
        self.archive_sha = qa._sha(self.archive)
        self.host = patch.object(qa, "_owner_windows_x64", return_value=True)
        self.host.start()
        self.addCleanup(self.host.stop)
        self.commit = patch.object(verify, "commit_of", return_value=self.git_sha)
        self.commit.start()
        self.addCleanup(self.commit.stop)

    def _call(self, *, runner=None) -> None:
        with redirect_stdout(io.StringIO()):
            qa.qualify(
                self.archive,
                self.source,
                self.scratch,
                self.archive_sha,
                self.exe_sha,
                runner=runner or self._good_runner,
            )

    def _good_runner(self, args, **kwargs):
        self.assertEqual(
            args[0:5],
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
            ],
        )
        self.assertIn("-ExePath", args)
        actual_binary = Path(args[args.index("-ExePath") + 1])
        self.assertEqual(qa._sha(actual_binary), self.exe_sha)
        self.assertEqual(Path(kwargs["cwd"]), actual_binary.parents[1])
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(kwargs["check"] is False)
        self.assertEqual(kwargs["timeout"], 90)
        return subprocess.CompletedProcess(
            args,
            0,
            chr(10).join(entry[2] for entry in qa.TESTS) + chr(10),
            "",
        )

    def test_genuine_canonical_archive_extracted_and_all_three_gui_suites(self):
        commands = []

        def runner(args, **kwargs):
            commands.append(args)
            return self._good_runner(args, **kwargs)

        self._call(runner=runner)
        self.assertEqual(len(commands), 3)
        self.assertEqual(
            [Path(args[args.index("-File") + 1]).name for args in commands],
            [entry[0] for entry in qa.TESTS],
        )
        self.assertEqual(
            [args[args.index("-ExePath") + 2] for args in commands],
            [entry[1] for entry in qa.TESTS],
        )
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_archive_digest_mismatch_stops_before_extraction_or_gui(self):
        with self.assertRaisesRegex(ValueError, "archive_identity_refused"):
            self._call_digest("0" * 64)
        self.assertEqual(list(self.scratch.iterdir()), [])

    def _call_digest(self, digest: str) -> None:
        with patch.object(qa.subprocess, "run", side_effect=AssertionError("GUI forbidden")):
            qa.qualify(self.archive, self.source, self.scratch, digest, self.exe_sha)

    def test_claimed_binary_sha_changed_stops_before_gui(self):
        with (
            self.assertRaisesRegex(ValueError, "binary_identity_refused"),
            patch.object(qa.subprocess, "run", side_effect=AssertionError("GUI forbidden")),
        ):
            qa.qualify(self.archive, self.source, self.scratch, self.archive_sha, "0" * 64)

    def test_extra_member_and_path_traversal_are_rejected(self):
        for name in ("../../evil.exe", "MedOrigin-Synthetic-Preview/unreviewed.dll"):
            with self.subTest(name=name):
                with zipfile.ZipFile(self.archive, "a") as f:
                    f.writestr(name, b"not approved")
                self.archive_sha = qa._sha(self.archive)
                with self.assertRaisesRegex(ValueError, "unexpected_or_duplicate_archive_members"):
                    self._call()
                self.assertEqual(list(self.scratch.iterdir()), [])
                self.archive.unlink()
                package.write_archive(
                    self.archive,
                    package.files_for(
                        self.data,
                        "windows",
                        "x86_64",
                        self.git_sha,
                        b"Apache-2.0",
                        b"Attribution",
                    ),
                    "windows",
                )
                self.archive_sha = qa._sha(self.archive)

    def test_modified_binary_or_manifest_not_accepted(self):
        with zipfile.ZipFile(self.archive, "r") as original:
            members = [(x, original.read(x.filename)) for x in original.infolist()]
        self.archive.unlink()
        with zipfile.ZipFile(self.archive, "w") as altered:
            for member, data in members:
                if member.filename.endswith(".exe"):
                    data = data[:-1] + bytes([1])
                altered.writestr(member, data)
        self.archive_sha = qa._sha(self.archive)
        with self.assertRaisesRegex(
            ValueError, "noncanonical_archive_content_or_permissions|manifest_provenance_mismatch"
        ):
            self._call()

    def test_gui_errors_missing_success_marker_and_stderr_refuse(self):
        cases = (
            subprocess.CompletedProcess([], 1, "", ""),
            subprocess.CompletedProcess([], 0, "not a UIA pass", ""),
            subprocess.CompletedProcess(
                [], 0, chr(10).join(row[2] for row in qa.TESTS), "bad stderr"
            ),
        )
        for response in cases:
            with self.subTest(code=response.returncode, stdout=response.stdout):
                with self.assertRaisesRegex(ValueError, "actual_windows_uia_refused"):
                    self._call(runner=lambda *_args, expected=response, **_kwargs: expected)
                self.assertEqual(list(self.scratch.iterdir()), [])

    def test_wrong_host_or_missing_scratch_refused_without_launch(self):
        with (
            patch.object(qa, "_owner_windows_x64", return_value=False),
            self.assertRaisesRegex(ValueError, "requires_owner_windows_x64"),
        ):
            self._call()
        with self.assertRaisesRegex(ValueError, "missing_or_reparse_path"):
            qa.qualify(
                self.archive,
                self.source,
                self.scratch / "absent",
                self.archive_sha,
                self.exe_sha,
            )

    def test_bad_digest_encodings_fail_closed(self):
        for malformed in ("A" * 64, "a" * 63, "a" * 64 + chr(10), "not_sha"):
            with (
                self.subTest(malformed=repr(malformed)),
                self.assertRaisesRegex(ValueError, "archive_sha_malformed"),
            ):
                qa.qualify(
                    self.archive,
                    self.source,
                    self.scratch,
                    malformed,
                    self.exe_sha,
                )


if __name__ == "__main__":
    unittest.main()
