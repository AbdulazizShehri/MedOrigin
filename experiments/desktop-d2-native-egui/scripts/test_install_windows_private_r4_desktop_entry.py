"""Strict Windows owner-local clickable R4 Core/native worklist entry tests.

Only task-owned temporary directories, never real user LocalAppData entries.
"""

from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import install_windows_private_r4_desktop_entry as entry

ROOT = Path(__file__).resolve().parents[3]


class PrivateR4DesktopEntryTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Reviewed Windows source path")
    def test_reviewed_shell_path_denies_metacharacters_and_aliases(self):
        self.assertIsNotNone(entry.PATH_RE.fullmatch(str(ROOT)))
        for bad in (
            r"C:\Users\A&whoami",
            r"C:\Users\A%APPDATA%",
            r"C:\Users\A!cmd",
            r"C:\Users\A|cmd",
            r"C:\Users\A^cmd",
            r"C:\Users\A<C",
            r"\\machine\share",
            r"C:drive-relative",
            "C:\\Temp\\evil\ncmd",
            'C:\\Users\\A" --bad',
        ):
            self.assertIsNone(entry.PATH_RE.fullmatch(bad), bad)

    def fixtures(self, base: Path):
        parent = base / entry.PARENT_NAME
        core = base / "fake-reviewed-core"
        core.mkdir()
        exe = base / "medorigin-desktop-d2-native-egui.exe"
        exe.write_bytes(b"fictional-native-test-only")
        archive = base / "fhir.schema.json.zip"
        archive.write_bytes(b"fake-not-official")
        python = Path(sys.executable).resolve(strict=True)
        args = Namespace(
            python=python,
            python_sha256=entry.legacy._file_sha(python),
            core_source=core,
            offline_r4_schema=archive,
            native_exe=exe,
            native_sha256=entry.legacy._file_sha(exe),
            mode="interactive",
        )
        return parent, args

    @unittest.skipUnless(sys.platform == "win32", "Real reviewed Windows temp root")
    def test_clickable_entry_modes_are_bounded_and_never_replaced(self):
        with TemporaryDirectory(prefix="medorigin-private-r4-entry-", dir=ROOT) as temporary:
            parent, args = self.fixtures(Path(temporary))
            with (
                patch.object(entry, "_parent", return_value=parent),
                patch.object(entry.r4, "_attest_core", return_value=args.core_source) as core,
                patch.object(
                    entry.r4, "_attest_offline_r4_schema", return_value=args.offline_r4_schema
                ) as schema,
                patch.object(entry.importlib.metadata, "version", return_value="4.25.1"),
            ):
                for mode in entry.NAMES:
                    args.mode = mode
                    out = entry.create_entry(args)
                    self.assertEqual(out.parent, parent)
                    self.assertEqual(out.name, entry.NAMES[mode])
                    script = out.read_bytes()
                    self.assertIn(b"NEVER patient data", script)
                    self.assertIn(b"setlocal DisableDelayedExpansion", script)
                    self.assertIn(b" --offline-r4-schema ", script)
                    self.assertIn(args.native_sha256.encode(), script)
                    self.assertIn(str(args.core_source).encode(), script)
                    self.assertIn(b"exit /b %ERRORLEVEL%", script)
                    self.assertEqual(script.count(b"\n"), 5)
                    self.assertEqual(script.count(b"\r\n"), 5)
                    self.assertNotIn(b"%*", script)
                    self.assertNotIn(b"powershell", script.lower())
                    expected = {
                        "interactive": (b" --qa-uia", b" --qa-auto-close"),
                        "uia": (b" --qa-uia",),
                        "auto-close": (b" --qa-auto-close",),
                    }[mode]
                    if mode == "interactive":
                        for excluded in expected:
                            self.assertNotIn(excluded, script)
                    else:
                        for required in expected:
                            self.assertIn(required, script)
                    with self.assertRaisesRegex(ValueError, "existing_entry_not_overwritten"):
                        entry.create_entry(args)
                    self.assertEqual(script, out.read_bytes())
                self.assertEqual(
                    {path.name for path in parent.iterdir()}, set(entry.NAMES.values())
                )
                self.assertEqual(core.call_count, len(entry.NAMES) * 2)
                self.assertEqual(schema.call_count, len(entry.NAMES) * 2)

    @unittest.skipUnless(sys.platform == "win32", "Actual Windows test fixtures")
    def test_mutated_binary_and_shell_injection_refused_before_write(self):
        with TemporaryDirectory(prefix="medorigin-private-r4-entry-", dir=ROOT) as temporary:
            parent, args = self.fixtures(Path(temporary))
            with (
                patch.object(entry, "_parent", return_value=parent),
                patch.object(entry.r4, "_attest_core", return_value=args.core_source) as core,
                patch.object(
                    entry.r4, "_attest_offline_r4_schema", return_value=args.offline_r4_schema
                ),
                patch.object(entry.importlib.metadata, "version", return_value="4.25.1"),
            ):
                args.native_sha256 = "0" * 64
                with self.assertRaisesRegex(ValueError, "native_executable_modified"):
                    entry.create_entry(args)
                self.assertFalse(parent.exists())
                args.native_sha256 = entry.legacy._file_sha(args.native_exe)
                args.core_source = Path(str(args.core_source) + "&whoami")
                with self.assertRaisesRegex(ValueError, "unreviewed_windows_shell_path"):
                    entry.create_entry(args)
                self.assertEqual(core.call_count, 1)
                self.assertFalse(parent.exists())
                args.core_source = Path(temporary) / "fake-reviewed-core"
                args.python_sha256 = "1" * 64
                with self.assertRaisesRegex(ValueError, "python_changed"):
                    entry.create_entry(args)
                self.assertFalse(parent.exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows cmd.exe actual invocation")
    def test_actual_click_executes_native_r4_launcher_but_invalid_test_zip_fails_closed(self):
        import subprocess

        with TemporaryDirectory(prefix="medorigin-private-r4-entry-", dir=ROOT) as temporary:
            parent, args = self.fixtures(Path(temporary))
            with (
                patch.object(entry, "_parent", return_value=parent),
                patch.object(entry.r4, "_attest_core", return_value=args.core_source),
                patch.object(
                    entry.r4, "_attest_offline_r4_schema", return_value=args.offline_r4_schema
                ),
                patch.object(entry.importlib.metadata, "version", return_value="4.25.1"),
            ):
                out = entry.create_entry(args)
            # The real CLI is run OUTSIDE mocks. Its reviewed HL7 ZIP SHA gate
            # MUST stop execution before any imaginary import or native GUI.
            click = subprocess.run(
                ["cmd.exe", "/d", "/c", str(out)],
                cwd=Path(temporary),
                capture_output=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(click.returncode, 2)
            self.assertIn(b"CORE971_OFFICIAL_R4_TO_NATIVE_NO_GO", click.stderr)
            self.assertNotIn(
                b"CORE971_OFFICIAL_R4_TWO_FILES_TO_NATIVE_NONCLINICAL_PASS", click.stdout
            )
            self.assertEqual(set(parent.iterdir()), {out})

    @unittest.skipUnless(sys.platform == "win32", "Windows Core979 exact source launcher")
    def test_core979_clickable_uses_distinct_namings_and_guarded_source_before_write(self):
        with TemporaryDirectory(prefix="medorigin-private-core979-entry-", dir=ROOT) as temp:
            parent, args = self.fixtures(Path(temp))
            args.core_revision = "core979"
            with (
                patch.object(entry, "_parent", return_value=parent),
                patch.object(
                    entry.core979, "_require_guarded_core", return_value=args.core_source
                ) as guard,
                patch.object(
                    entry.r4, "_attest_offline_r4_schema", return_value=args.offline_r4_schema
                ),
                patch.object(entry.importlib.metadata, "version", return_value="4.25.1"),
            ):
                for mode, name in entry.CORE979_NAMES.items():
                    args.mode = mode
                    created = entry.create_entry(args)
                    raw = created.read_bytes()
                    self.assertEqual(created.name, name)
                    self.assertIn(b"launch_windows_real_core979_guarded_r4_fictional_batch.py", raw)
                    self.assertNotIn(
                        b"launch_windows_real_core971_official_r4_fictional_batch.py", raw
                    )
                    self.assertIn(b" --offline-r4-schema ", raw)
                    self.assertIn(b" --core-source ", raw)
                    self.assertIn(b"NEVER patient data", raw)
                    self.assertNotIn(b"LOCALAPPDATA", raw)
                    self.assertNotIn(b"%*", raw)
                    with self.assertRaisesRegex(ValueError, "existing_entry_not_overwritten"):
                        entry.create_entry(args)
                self.assertEqual(guard.call_count, len(entry.CORE979_NAMES) * 2)
                self.assertEqual(
                    {x.name for x in parent.iterdir()}, set(entry.CORE979_NAMES.values())
                )

    @unittest.skipUnless(sys.platform == "win32", "Actual Windows Core979 shell negative")
    def test_core979_real_click_with_unreviewed_source_refuses_without_gui(self):
        import subprocess

        with TemporaryDirectory(prefix="medorigin-private-core979-entry-", dir=ROOT) as temp:
            parent, args = self.fixtures(Path(temp))
            args.core_revision = "core979"
            with (
                patch.object(entry, "_parent", return_value=parent),
                patch.object(entry.core979, "_require_guarded_core", return_value=args.core_source),
                patch.object(
                    entry.r4, "_attest_offline_r4_schema", return_value=args.offline_r4_schema
                ),
                patch.object(entry.importlib.metadata, "version", return_value="4.25.1"),
            ):
                created = entry.create_entry(args)
            result = subprocess.run(
                ["cmd.exe", "/d", "/c", str(created)],
                cwd=Path(temp),
                capture_output=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"GUARDED_CORE979_R4_HMAC_NATIVE_NO_GO", result.stderr)
            self.assertNotIn(
                b"CORE971_OFFICIAL_R4_TWO_FILES_TO_NATIVE_NONCLINICAL_PASS", result.stdout
            )
            self.assertEqual(set(parent.iterdir()), {created})

    def test_unreviewed_core_revision_is_refused_without_any_write(self):
        with TemporaryDirectory(prefix="medorigin-private-r4-entry-", dir=ROOT) as temp:
            parent, args = self.fixtures(Path(temp))
            args.core_revision = "nonexistent-core"
            with (
                patch.object(entry, "_parent", return_value=parent),
                self.assertRaisesRegex(ValueError, "core_revision_not_reviewed"),
            ):
                entry.create_entry(args)
            self.assertFalse(parent.exists())

    def test_unreviewed_mode_os_or_source_parameters_refused(self):
        with self.assertRaisesRegex(ValueError, "unreviewed_mode_or_hash"):
            entry._render(Path("a"), Path("b"), Path("c"), Path("d"), "0" * 64, Path("e"), "other")
        with self.assertRaisesRegex(ValueError, "unreviewed_mode_or_hash"):
            entry._render(
                Path("a"), Path("b"), Path("c"), Path("d"), "0" * 63, Path("e"), "interactive"
            )
        with (
            patch.object(sys, "platform", "linux"),
            self.assertRaisesRegex(ValueError, "windows_only"),
        ):
            entry._parent()


if __name__ == "__main__":
    unittest.main()
