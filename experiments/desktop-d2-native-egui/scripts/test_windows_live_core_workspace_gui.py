"""Adversarial source qualification for Windows live fictional encrypted Workspace."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_windows_core_workspace_to_native_gui as qa


class WindowsRealCoreWorkspaceSourceTests(unittest.TestCase):
    def test_non_windows_refuses_without_launch(self):
        with patch.object(qa.sys, "platform", "darwin"):  # noqa: SIM117
            with patch.object(qa.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "real_windows_desktop_required"):
                    qa.qualify(None)
                run.assert_not_called()

    def test_pin_approved_core_and_exact_aggregate_not_clinical(self):
        self.assertEqual(qa.CORE_SHA, "0351b667ec910480fd61c30f18cf3bb0dd0ae842")
        self.assertEqual(
            qa.RECEIPT_SHA, "25acdb57db8ca3f11d353cf311167973760caaa95bb64de7339fe21e3b05cc2e"
        )
        self.assertIn("'workspace-demo','--synthetic-only','--ephemeral-demo'", qa.FIXED_CLI)

    def test_no_unapproved_cli_input_and_startup_hooks(self):
        source = Path(qa.__file__).read_text()
        self.assertIn('str(python), "-I", "-S", "-B", "-c", FIXED_CLI', source)
        self.assertIn("sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]]", source)
        self.assertIn("subprocess.run(", source)
        self.assertIn("timeout=25, check=False", source)
        self.assertIn("sha256(raw).hexdigest()", source)
        self.assertIn("raw != source_receipt.read_bytes()", source)
        self.assertIn('"windows_actual_native_gui_core_live_receipt_uia_no_go"', source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("patient_path=", source)
        self.assertNotIn("provider_key=", source)

    def test_git_source_only_refusal_and_freshness(self):
        source = Path(qa.__file__).read_text()
        self.assertIn('git(core, "status", "--porcelain", "--untracked-files=all")', source)
        self.assertIn('git(core, "ls-files", "-z", "--", section)', source)
        self.assertIn("core_workspace_source_symlink_refused", source)
        self.assertIn("unreviewed_python_startup_or_native_source", source)
        self.assertIn("reviewed_binary_changed_after_windows_ui_test", source)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(qa.subprocess, "run") as run:
                run.return_value.stdout = b"not-reviewed\n"
                with self.assertRaisesRegex(ValueError, "source_revision_not_matched"):
                    qa.verify_pinned_core(root)
                run.assert_called()

    def test_only_one_terminal_crlf_or_lf_is_removed_and_other_bytes_preserved(self):
        expected = b'{"synthetic":true}'
        self.assertEqual(qa.strip_platform_one_newline(expected + b"\r\n"), expected)
        self.assertEqual(qa.strip_platform_one_newline(expected + b"\n"), expected)
        # Normalization never makes malformed/extra-text output equal to a
        # reviewed canonical receipt; only its last line terminator is removed.
        self.assertNotEqual(qa.strip_platform_one_newline(expected + b"\n\n"), expected)
        self.assertNotEqual(qa.strip_platform_one_newline(expected + b" \r\n"), expected)
        with self.assertRaisesRegex(ValueError, "single_terminal_newline_missing"):
            qa.strip_platform_one_newline(expected)
        with self.assertRaisesRegex(ValueError, "single_terminal_newline_missing"):
            qa.strip_platform_one_newline(b"")

    def test_ignored_bytecode_cache_and_native_loader_shadow_refused(self):
        with TemporaryDirectory() as tmp:
            core = Path(tmp)
            inventories = {}
            for section, count in (
                ("src/medscale", 120),
                ("apps/workspace/src/medscale_workspace", 25),
            ):
                folder = core / section
                folder.mkdir(parents=True)
                files = []
                for index in range(count):
                    rel = f"{section}/fictional_{index:03d}.py"
                    (core / rel).write_text("# fictional QA only\n", encoding="utf-8")
                    files.append(rel)
                inventories[section] = files

            def fixed_git(_core, *args):
                if args == ("rev-parse", "HEAD"):
                    return (qa.CORE_SHA + "\n").encode()
                if args[0] == "status":
                    return b""
                if args[0] == "ls-files":
                    return ("\x00".join(inventories[args[-1]]) + "\x00").encode()
                raise AssertionError("unexpected source inventory operation")

            with patch.object(qa, "git", side_effect=fixed_git):
                qa.verify_pinned_core(core)
                cached = core / "src/medscale/__pycache__"
                cached.mkdir()
                (cached / "fictional_000.cpython-314.pyc").write_bytes(b"bad bytecode")
                with self.assertRaisesRegex(ValueError, "ignored_python_bytecode_refused"):
                    qa.verify_pinned_core(core)
                (cached / "fictional_000.cpython-314.pyc").unlink()
                cached.rmdir()
                rogue = core / "src/medscale/hidden_native_loader.pyd"
                rogue.write_bytes(b"bad native loader")
                with self.assertRaisesRegex(ValueError, "unreviewed_python_startup"):
                    qa.verify_pinned_core(core)

    def test_native_windows_uia_live_file_is_exact_hash_and_size_bounded(self):
        observer = (
            Path(__file__).resolve().parent.parent
            / "tests/windows-encrypted-workspace-native-uia.ps1"
        )
        text = observer.read_text()
        self.assertIn("[string]$LiveReceiptPath", text)
        self.assertIn("$entry.Length -ne 391", text)
        self.assertIn(
            "(Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash -ine $fixtureSha", text
        )
        self.assertIn("$bytes=[System.IO.File]::ReadAllBytes($live)", text)
        self.assertIn("D2_WINDOWS_ENCRYPTED_WORKSPACE_NATIVE_UIA_PASS_NONCLINICAL", text)


if __name__ == "__main__":
    unittest.main()
