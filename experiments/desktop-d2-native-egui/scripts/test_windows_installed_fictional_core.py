"""Nonclinical Windows installed-Wheel Core interactive D2 boundary tests."""

from __future__ import annotations

import hashlib
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import launch_windows_installed_fictional_core as launcher
from attest_installed_encrypted_core_readback import PINNED_CORE_SHA
from supervise_windows_encrypted_core_job import (
    INSTALLED_RUNNER,
    SOURCE_RUNNER,
)


class WindowsInstalledFictionalCoreTests(unittest.TestCase):
    def test_exact_windows_wheel_checkpoint_and_source_pins(self):
        self.assertEqual(PINNED_CORE_SHA, "8e5ed5430f4ab2ebc8981c52c67234023382954b")
        self.assertEqual(
            [entry[4] for entry in launcher.WINDOWS_APPROVED_WHEELS],
            [256, 34],
        )
        for package, source, filename, digest, count in launcher.WINDOWS_APPROVED_WHEELS:
            self.assertIn(package, ("medscale", "medscale_workspace"))
            self.assertTrue(source.startswith(("src/", "apps/workspace/src/")))
            self.assertTrue(filename.endswith("-py3-none-any.whl"))
            self.assertEqual(len(digest), 64)
            self.assertGreater(count, 0)
        self.assertEqual(
            launcher.PROJECTION_SHA,
            "c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49",
        )
        self.assertEqual(len(launcher.EXPORTER_SHA256), 64)

    def test_worker_isolation_from_git_source_and_installed_origin_binding(self):
        self.assertIn("sys.path[:0]=[sys.argv[1],sys.argv[2]]", INSTALLED_RUNNER)
        self.assertIn("medscale.__file__", INSTALLED_RUNNER)
        self.assertIn("medscale_workspace.__file__", INSTALLED_RUNNER)
        self.assertIn("medscale/__init__.py", INSTALLED_RUNNER)
        self.assertIn("medscale_workspace/__init__.py", INSTALLED_RUNNER)
        self.assertIn("m.version('cryptography')=='50.0.1'", INSTALLED_RUNNER)
        self.assertIn("m.version('cffi')=='2.1.1'", INSTALLED_RUNNER)
        self.assertIn("sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]]", SOURCE_RUNNER)
        source = Path(launcher.__file__).read_text(encoding="utf-8")
        for constraint in (
            "attest_installed(core, wheels, installed, approved_wheels=WINDOWS_APPROVED_WHEELS)",
            "installed_site=installed",
            "raw != fixture.read_bytes()",
            "hashlib.sha256(raw).hexdigest() != PROJECTION_SHA",
            "stdin=subprocess.PIPE",
            "input=raw",
            "qa_uia",
            "process.kill()",
        ):
            self.assertIn(constraint, source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("patient-file", source)

    def test_nonwindows_refuses_before_reading_any_files(self):
        with (
            patch.object(launcher.sys, "platform", "linux"),
            self.assertRaisesRegex(ValueError, "windows_host_required"),
        ):
            launcher.qualify_paths(Namespace())

    def test_forged_python_or_gui_identity_refused_before_wheel_attestation(self):
        if sys.platform != "win32":
            self.skipTest("actual Windows local path identity test")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for part in ("core", "wheels", "installed", "crypto"):
                (root / part).mkdir()
            python = root / "python.exe"
            gui = root / "medorigin-desktop-d2-native-egui.exe"
            python.write_bytes(b"fake-reviewed-python-binary")
            gui.write_bytes(b"fake-reviewed-d2-binary")
            args = Namespace(
                core_source=root / "core",
                wheels=root / "wheels",
                installed_site=root / "installed",
                crypto_site=root / "crypto",
                python=python,
                native_gui=gui,
                python_sha="0" * 64,
                native_sha=hashlib.sha256(gui.read_bytes()).hexdigest(),
            )
            with (
                patch.object(
                    launcher,
                    "attest_installed",
                    side_effect=AssertionError("must not attest on bad hash"),
                ),
                self.assertRaisesRegex(
                    ValueError, "reviewed_python_crypto_site_or_native_exe_changed"
                ),
            ):
                launcher.qualify_paths(args)

    def test_gui_uia_script_cannot_succeed_without_exact_result(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            exe = root / "medorigin-desktop-d2-native-egui.exe"
            exe.write_bytes(b"only-a-toy-not-executable")
            with patch.object(launcher.subprocess, "run") as run:
                run.return_value.returncode = 2
                run.return_value.stdout = b""
                with self.assertRaisesRegex(ValueError, "installed_core_real_native_uia_refused"):
                    launcher._verify_installed_core_in_native_uia(exe, b"fictional", root, "0" * 64)
            self.assertTrue((root / "installed-fictional-readback-verified.json").is_file())


if __name__ == "__main__":
    unittest.main()
