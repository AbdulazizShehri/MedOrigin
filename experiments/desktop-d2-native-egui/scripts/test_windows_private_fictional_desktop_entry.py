"""Source-only opt-in Windows one-click fictional Desktop installer tests."""

from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import install_windows_private_fictional_desktop_entry as entry

# An arbitrary runner OS temp path can include CMD metacharacters which the
# installer deliberately refuses. Use the reviewed Git checkout directory for
# source-only temporary fixtures instead; NEVER relax the installer path guard.
_REVIEWED_TEST_PARENT = Path(__file__).resolve().parents[3]


class PrivateFictionalOneClickTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows reviewed checkout path")
    def test_fixture_root_is_shell_safe_but_metacharacter_root_is_not(self):
        self.assertIsNotNone(entry._REVIEWED_PATH.fullmatch(str(_REVIEWED_TEST_PARENT)))
        self.assertIsNone(entry._REVIEWED_PATH.fullmatch(r"C:\Test\unsafe@runner"))
        self.assertIsNone(entry._REVIEWED_PATH.fullmatch(r"C:\Test\unsafe&cmd"))

    def _fixture(self, base: Path) -> tuple[Namespace, Path, Path]:
        kit = base / "known-source-verified-kit"
        (kit / "scripts").mkdir(parents=True)
        launcher = kit / "scripts/launch_windows_portable_fictional_core.py"
        launcher.write_text("# fictional only", encoding="ascii")
        fake_gui = base / "known-native-gui.exe"
        fake_gui.write_bytes(b"synthetic-only")
        dummy_report = base / "fictional.json"
        dummy_report.write_bytes(b"{}")
        parent = base / entry.PRIVATE_PARENT_NAME
        parent.mkdir()
        python = Path(sys.executable).resolve()
        args = Namespace(
            kit=kit,
            python=python,
            crypto_site=base,
            python_sha=entry.sha(python),
            qa_mode="interactive",
        )
        return args, parent, fake_gui

    @unittest.skipUnless(sys.platform == "win32", "Actual Windows local test root")
    def test_one_time_shortcut_is_exact_pinned_and_never_overwritten(self):
        with TemporaryDirectory(
            prefix="medorigin-private-entry-QA-", dir=_REVIEWED_TEST_PARENT
        ) as tmp:
            args, parent, gui = self._fixture(Path(tmp))
            reporter = Path(tmp) / "fictional.json"
            with (
                patch.object(entry, "_installed_parent", return_value=parent),
                patch.object(
                    entry,
                    "attest_kit",
                    return_value=(gui, reporter, reporter),
                ) as attest,
            ):
                created = entry.make_entry(args)
                attest.assert_called_once_with(args.kit)
                self.assertEqual(created.name, entry.ENTRY_NAME)
                cmd = created.read_text(encoding="ascii")
                self.assertIn("setlocal DisableDelayedExpansion", cmd)
                self.assertIn("--ensure-fictional-demo", cmd)
                self.assertIn("--fictional-persistent-qa-root", cmd)
                self.assertIn(
                    str(args.kit / "scripts/launch_windows_portable_fictional_core.py"), cmd
                )
                self.assertIn(args.python_sha, cmd)
                self.assertIn("NEVER real patient data", cmd)
                self.assertNotIn("--qa-uia", cmd)
                self.assertNotIn(" --qa-auto-close", cmd)
                self.assertNotIn("%*", cmd)
                self.assertNotIn("powershell", cmd.lower())
                self.assertNotIn("start /b", cmd.lower())
                with self.assertRaisesRegex(ValueError, "exists_do_not_overwrite"):
                    entry.make_entry(args)
                self.assertEqual(cmd, created.read_text(encoding="ascii"))
                self.assertFalse((parent / entry.QA_DIR_NAME).exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows local no-network path guard")
    def test_refuse_wrong_python_hash_and_injected_metacharacters(self):
        with TemporaryDirectory(
            prefix="medorigin-private-entry-QA-", dir=_REVIEWED_TEST_PARENT
        ) as tmp:
            args, parent, gui = self._fixture(Path(tmp))
            reporter = Path(tmp) / "fictional.json"
            with (
                patch.object(entry, "_installed_parent", return_value=parent),
                patch.object(
                    entry,
                    "attest_kit",
                    return_value=(gui, reporter, reporter),
                ) as attest,
            ):
                args.python_sha = "0" * 64
                with self.assertRaisesRegex(ValueError, "python_digest_refused"):
                    entry.make_entry(args)
                attest.assert_not_called()
                args.python_sha = entry.sha(args.python)
                args.kit = Path(str(args.kit) + "&whoami")
                with self.assertRaisesRegex(ValueError, "unreviewed_shell_path"):
                    entry.make_entry(args)
                attest.assert_not_called()
                self.assertEqual(list(parent.iterdir()), [])

    @unittest.skipUnless(sys.platform == "win32", "Windows private test root")
    def test_all_three_modes_allow_only_fixed_output_names_and_nonclinical_flags(self):
        with TemporaryDirectory(
            prefix="medorigin-private-entry-QA-", dir=_REVIEWED_TEST_PARENT
        ) as tmp:
            args, parent, gui = self._fixture(Path(tmp))
            reporter = Path(tmp) / "fictional.json"
            with (
                patch.object(entry, "_installed_parent", return_value=parent),
                patch.object(entry, "attest_kit", return_value=(gui, reporter, reporter)),
            ):
                args.qa_mode = "uia"
                a = entry.make_entry(args)
                self.assertEqual(a.name, entry.QA_ENTRY_NAME)
                self.assertIn(" --qa-uia", a.read_text(encoding="ascii"))
                args.qa_mode = "auto-close"
                b = entry.make_entry(args)
                self.assertEqual(b.name, entry.CLOSE_ENTRY_NAME)
                self.assertIn(" --qa-auto-close", b.read_text(encoding="ascii"))
                args.qa_mode = "unreviewed"
                with self.assertRaisesRegex(ValueError, "unreviewed_mode"):
                    entry.make_entry(args)
                self.assertEqual(
                    {x.name for x in parent.iterdir()},
                    {
                        entry.QA_ENTRY_NAME,
                        entry.CLOSE_ENTRY_NAME,
                    },
                )

    def test_platform_gate_refuses_without_windows(self):
        with (
            patch.object(entry.sys, "platform", "linux"),
            self.assertRaisesRegex(ValueError, "windows_native_private_entry_only"),
        ):
            entry._installed_parent()


if __name__ == "__main__":
    unittest.main()
