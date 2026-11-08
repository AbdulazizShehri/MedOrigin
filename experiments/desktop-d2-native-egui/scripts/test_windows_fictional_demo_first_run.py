"""Private source-only first-run UX controls for the fixed fictional Windows vault.

These tests exercise the actual launcher path in a temporary fake bundle,
without requiring Core, persistent keys, network access or a live GUI.
"""

from __future__ import annotations

import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import launch_windows_portable_fictional_core as launcher
from supervise_windows_encrypted_core_job import (
    PERSISTENT_CREATE_MARKER,
    PERSISTENT_INSTALLED_CREATE_RUNNER,
    PERSISTENT_QA_DIR_NAME,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures/core/encrypted-persistent-readback-projection.json"


class FictionalFirstRunTests(unittest.TestCase):
    def test_create_mode_worker_uses_pinned_installed_source_and_exact_fictional_method(self):
        self.assertIn("import medscale,medscale_workspace;", PERSISTENT_INSTALLED_CREATE_RUNNER)
        self.assertIn("medscale.__file__", PERSISTENT_INSTALLED_CREATE_RUNNER)
        self.assertIn("medscale_workspace.__file__", PERSISTENT_INSTALLED_CREATE_RUNNER)
        self.assertIn("create_fixed_fictional_qa_vault", PERSISTENT_INSTALLED_CREATE_RUNNER)
        self.assertIn("Crypt", (ROOT / "scripts/windows_fictional_persistent_vault.py").read_text())
        self.assertNotIn("shell=True", PERSISTENT_INSTALLED_CREATE_RUNNER)
        self.assertNotIn("subprocess", PERSISTENT_INSTALLED_CREATE_RUNNER)
        self.assertNotIn("socket.", PERSISTENT_INSTALLED_CREATE_RUNNER)
        source = (ROOT / "scripts/supervise_windows_encrypted_core_job.py").read_text()
        self.assertIn("CREATE_SUSPENDED | CREATE_NO_WINDOW", source)
        self.assertLess(
            source.index("api.AssignProcessToJobObject(job, info.hProcess)"),
            source.index("api.ResumeThread(info.hThread)"),
        )

    def test_optional_first_run_creates_only_when_absent_then_reopens_without_overwrite(self):
        with TemporaryDirectory(prefix="medorigin-private-first-run-qa-") as folder:
            base = Path(folder)
            gui = base / "medorigin-desktop-d2-native-egui.exe"
            gui.write_bytes(b"fictional-gui-qa-placeholder")
            py = base / "python.exe"
            py.write_bytes(b"fictional-python-executable-no-execution")
            root = base / PERSISTENT_QA_DIR_NAME
            args = Namespace(
                python=py,
                crypto_site=base,
                python_sha=launcher.sha(py),
                fictional_persistent_qa_root=root,
                ensure_fictional_demo=True,
                qa_uia=False,
                qa_auto_close=True,
            )
            seen = []

            def owned_fake_worker(**kwargs):
                seen.append(
                    {
                        "create": kwargs.get("persistent_create_root"),
                        "reopen": kwargs.get("persistent_qa_root"),
                    }
                )
                if kwargs.get("persistent_create_root") is not None:
                    root.mkdir()
                    (kwargs["work"] / "synthetic-core-readback-job-only.json").write_bytes(
                        PERSISTENT_CREATE_MARKER
                    )
                    return PERSISTENT_CREATE_MARKER
                return FIXTURE.read_bytes()

            with (
                patch.object(launcher.sys, "platform", "win32"),
                patch.object(launcher.sys, "executable", str(py)),
                patch.object(launcher, "attest_kit", return_value=(gui, FIXTURE, FIXTURE)),
                patch.object(
                    launcher,
                    "execute_encrypted_source_under_job",
                    side_effect=owned_fake_worker,
                ),
                patch.object(launcher, "_launch_gui") as display,
            ):
                launcher.launch(args)
                self.assertEqual(len(seen), 2)
                self.assertEqual(seen[0], {"create": root, "reopen": None})
                self.assertEqual(seen[1], {"create": None, "reopen": root})
                self.assertEqual(display.call_count, 1)

                # Second launch of the SAME exact path cannot silently
                # regenerate or overwrite the existing fictional store.
                launcher.launch(args)
                self.assertEqual(len(seen), 3)
                self.assertEqual(seen[2], {"create": None, "reopen": root})
                self.assertEqual(display.call_count, 2)

    def test_missing_path_refuses_before_initialization(self):
        with TemporaryDirectory() as folder:
            py = Path(folder) / "python.exe"
            py.write_bytes(b"fictional-python-executable-no-execution")
            args = Namespace(
                python=py,
                crypto_site=Path(folder),
                python_sha=launcher.sha(py),
                fictional_persistent_qa_root=None,
                ensure_fictional_demo=True,
                qa_uia=False,
                qa_auto_close=True,
            )
            with (
                patch.object(launcher.sys, "platform", "win32"),
                patch.object(launcher.sys, "executable", str(py)),
                patch.object(launcher, "attest_kit") as attest,
                patch.object(launcher, "execute_encrypted_source_under_job") as worker,
            ):
                attest.return_value = (Path(folder) / "foo.exe", FIXTURE, FIXTURE)
                with self.assertRaisesRegex(
                    ValueError, "fictional_demo_requires_explicit_fixed_vault_path"
                ):
                    launcher.launch(args)
                worker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
