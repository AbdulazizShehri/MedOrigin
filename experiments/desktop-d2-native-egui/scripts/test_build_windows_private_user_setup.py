"""Regression guards for offline, unsigned, per-user fictional Windows setup."""

from __future__ import annotations

import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import build_windows_private_user_setup as setup
import package_preview as package
import verify_preview as verify


def fake_pe() -> bytes:
    raw = bytearray(4096)
    raw[:2] = b"MZ"
    struct.pack_into("<I", raw, 0x3C, 128)
    raw[128:132] = b"PE" + bytes(2)
    struct.pack_into("<H", raw, 132, 0x8664)
    return bytes(raw)


class PrivateWindowsUserSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="mo-setup-")
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.source = self.work / "reviewed-source"
        self.source.mkdir()
        (self.source / "LICENSE").write_bytes(b"Apache-2.0 fictional testing")
        scripts = self.source / "experiments" / "desktop-d2-native-egui" / "scripts"
        scripts.mkdir(parents=True)
        notice = scripts.parent / "UPSTREAM-NOTICE.md"
        notice.write_bytes(b"Review upstream licensing")
        original = Path(__file__).with_name("windows_private_user_setup.template.ps1")
        self.template = original.read_text(encoding="utf-8")
        (scripts / original.name).write_text(self.template, encoding="utf-8")

        self.commit = "a" * 40
        self.native = fake_pe()
        self.binary_sha = setup.digest(self.native)
        payload = package.files_for(
            self.native,
            "windows",
            "x86_64",
            self.commit,
            (self.source / "LICENSE").read_bytes(),
            notice.read_bytes(),
        )
        self.archive = self.work / (
            "MedOrigin-Synthetic-D2-windows-x86_64-" + self.commit[:8] + ".zip"
        )
        package.write_archive(self.archive, payload, "windows")
        self.archive_sha = setup.digest(self.archive.read_bytes())
        self.out = self.work / "private-dist"
        for target in (verify, setup):
            p = patch.object(target, "commit_of", return_value=self.commit)
            p.start()
            self.addCleanup(p.stop)

    def _build(self, **kw):
        return setup.build(
            kw.get("archive", self.archive),
            self.source,
            kw.get("output", self.out),
            kw.get("archive_sha256", self.archive_sha),
            kw.get("native_sha256", self.binary_sha),
        )

    def test_iexpress_timeout_closes_only_its_owned_builder_job(self):
        import qualify_windows_job_subtree as job_contract

        api = Mock()
        owned_job = 0x1234
        api.CreateJobObjectW.return_value = owned_job
        api.SetInformationJobObject.return_value = True
        api.CreateProcessW.return_value = True
        api.AssignProcessToJobObject.return_value = True
        api.ResumeThread.return_value = 1
        api.WaitForSingleObject.return_value = job_contract.WAIT_TIMEOUT
        with (
            patch.object(setup, "_real_path"),
            patch.object(job_contract, "_win32", return_value=api),
            self.assertRaisesRegex(
                ValueError, "windows_iexpress_builder_timed_out_subtree_terminated"
            ),
        ):
            setup._run_iexpress(
                self.work / "fictional-only-test.sed",
                self.work / "fictional-only-test.exe",
            )
        self.assertEqual(api.WaitForSingleObject.call_args.args[1], 240_000)
        api.CloseHandle.assert_called_once_with(owned_job)
        api.TerminateProcess.assert_not_called()

    def test_canonical_source_to_private_iexpress_bundle_has_exact_pins(self):
        observed = {}

        def fake_iexpress(sed: Path, target: Path):
            stage = sed.parent
            names = {item.name for item in stage.iterdir()}
            self.assertEqual(
                names,
                {
                    setup.REVIEWED_ARCHIVE,
                    setup.INSTALLER_SCRIPT,
                    setup.INSTALLER_COMMAND,
                    "private.sed",
                },
            )
            compiled = (stage / setup.INSTALLER_SCRIPT).read_text(encoding="utf-8")
            self.assertIn(self.commit, compiled)
            self.assertIn(self.binary_sha, compiled)
            self.assertIn(self.archive_sha, compiled)
            self.assertEqual(
                setup.digest((stage / setup.REVIEWED_ARCHIVE).read_bytes()),
                self.archive_sha,
            )
            for name in setup.FILES:
                self.assertIn(
                    setup.digest(setup._read_exact_zip_members(self.archive)[name]), compiled
                )
                self.assertFalse((stage / name).exists(), "do not recompress native EXE")
            self.assertNotIn("__EXPECTED_ARCHIVE_SHA256__", compiled)
            self.assertNotIn("__EXPECTED_HASHES__", compiled)
            self.assertNotIn("__EXPECTED_COMMIT__", compiled)
            self.assertIn("Start Menu", compiled)
            self.assertIn("refuse_unc_relative_or_unreviewed_drive_path", compiled)
            self.assertIn("source", compiled.lower())
            sed_text = sed.read_text(encoding="ascii")
            self.assertIn("PackagePurpose=InstallApp", sed_text)
            self.assertIn("AppLaunched=cmd.exe /d /c Install-MedOrigin-Private.cmd", sed_text)
            self.assertIn("SourceFiles0=", sed_text)
            self.assertIn(target.name, sed_text)
            observed["filecount"] = len(names)
            # Simulate an x64 generated setup: do not execute during unit tests.
            target.write_bytes(fake_pe())

        with patch.object(setup, "_run_iexpress", side_effect=fake_iexpress):
            setup_file = self._build()
        self.assertTrue(setup_file.is_file())
        self.assertEqual(observed["filecount"], 4)
        self.assertEqual(
            setup.inspect_native_header(setup_file.read_bytes()), ("windows", "x86_64")
        )
        self.assertEqual(list(self.out.iterdir()), [setup_file])

    def test_archive_digest_mismatch_refuses_before_output(self):
        with self.assertRaisesRegex(ValueError, "archive_sha256_refused"):
            self._build(archive_sha256="0" * 64)
        self.assertFalse(self.out.exists())

    def test_binary_digest_mismatch_refuses_before_output(self):
        with self.assertRaisesRegex(ValueError, "native_sha256_refused"):
            self._build(native_sha256="0" * 64)
        self.assertFalse(self.out.exists())

    def test_modified_repo_license_refuses_source_provenance(self):
        (self.source / "LICENSE").write_text("unreviewed substitute", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "noncanonical_archive_content_or_permissions"):
            self._build()
        self.assertFalse(self.out.exists())

    def test_extra_member_and_traversal_are_refused(self):
        import zipfile

        with zipfile.ZipFile(self.archive, "a") as zf:
            zf.writestr("../../arbitrary.txt", "unreviewed")
        self.archive_sha = setup.digest(self.archive.read_bytes())
        with self.assertRaisesRegex(ValueError, "unexpected_or_duplicate_archive_members"):
            self._build()
        self.assertFalse(self.out.exists())

    def test_output_already_exists_is_never_overwritten(self):
        self.out.mkdir()
        marker = self.out / "keep.txt"
        marker.write_text("do not modify", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "output_already_exists"):
            self._build()
        self.assertEqual(marker.read_text(), "do not modify")

    def test_bad_digest_encodings_refuse(self):
        for bad in ("A" * 64, "a" * 63, "not a sha", "a" * 64 + " "):
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(ValueError, "expected_digest_refused"),
            ):
                self._build(archive_sha256=bad)
        self.assertFalse(self.out.exists())

    def test_iexpress_sed_paths_accept_safe_windows_8dot3_tilde_names(self):
        # Windows hosted runners may resolve temp roots through short 8.3
        # paths (RUNNER~1); '~' is not a cmd.exe metacharacter.
        short_name = Path(r"C:\Users\RUNNER~1\AppData\Local\Temp\MO-SET~1\Private-Setup.exe")
        self.assertEqual(setup._safe_sed_path(short_name), str(short_name))

    def test_iexpress_sed_path_rejects_shell_metacharacters_and_unc(self):
        for bad in (
            r"C:\Temp\bad&echo.exe",
            r"C:\Temp\bad%PATH%",
            r"C:\Temp\evil;del",
            r"\\server\share\evil.exe",
            r"C:\Temp\a" + ("a" * 231),
        ):
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(ValueError, "unreviewed_iexpress_sed_windows_path"),
            ):
                setup._safe_sed_path(Path(bad))

    def test_render_refuses_incomplete_or_forged_template(self):
        files = dict.fromkeys(setup.FILES, b"synthetic")
        with self.assertRaisesRegex(ValueError, "setup_template_identity_missing"):
            setup.render_script("no source placeholder", self.commit, files, self.archive_sha)
        with self.assertRaisesRegex(ValueError, "setup_source_or_member_set_refused"):
            setup.render_script(self.template, "bad", files, self.archive_sha)
        with self.assertRaisesRegex(ValueError, "setup_source_or_member_set_refused"):
            setup.render_script(
                self.template, self.commit, {"one": b"unapproved"}, self.archive_sha
            )

    def test_windows_installer_crypto_and_zip_are_framework_only(self):
        # Hosted Windows runners may disable optional module autoload.
        # SHA-256 and ZIP extraction must not depend on Get-FileHash or
        # Expand-Archive, or invoke an arbitrary external decompressor.
        self.assertNotIn("Get-FileHash", self.template)
        self.assertNotIn("Expand-Archive", self.template)
        self.assertIn("[Security.Cryptography.SHA256]::Create()", self.template)
        self.assertIn("[IO.Compression.ZipFile]::ExtractToDirectory", self.template)

    def test_real_rendered_ps_script_parses_on_windows(self):
        import subprocess
        import sys

        if sys.platform != "win32":
            self.skipTest("Windows PowerShell parser only")
        files = {key: hashlib.sha256(key.encode()).digest() for key in setup.FILES}
        rendered = setup.render_script(self.template, self.commit, files, self.archive_sha)
        source = self.work / "rendered-install.ps1"
        source.write_text(rendered, encoding="utf-8")
        checker = (
            "$tok=$null;$errors=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "'" + str(source) + "',[ref]$tok,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -ne 0){$errors|%{$_.Message};exit 2}"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", checker],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(__import__("sys").platform == "win32", "Windows-only private profile")
    def test_real_windows_installer_expands_pinned_archive_into_isolated_profile(self):
        """Exercise generated PowerShell, not fake IExpress or the user's profile."""
        import os
        import subprocess

        # No default user directories or real binaries. The installer must
        # use only this disposable, synthetic unit-test profile.
        extraction = self.work / "private-extraction"
        extraction.mkdir()
        (extraction / setup.REVIEWED_ARCHIVE).write_bytes(self.archive.read_bytes())
        (extraction / setup.INSTALLER_COMMAND).write_text(
            "@echo off\r\nexit /b 2\r\n", encoding="ascii"
        )  # Never execute the bootstrap in this source test.
        compiled = setup.render_script(
            self.template,
            self.commit,
            setup._read_exact_zip_members(self.archive),
            self.archive_sha,
        )
        script = extraction / setup.INSTALLER_SCRIPT
        script.write_text(compiled, encoding="utf-8")
        local = self.work / "private-profile" / "AppData" / "Local"
        roam = self.work / "private-profile" / "AppData" / "Roaming"
        programs = roam / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        for path in (local, programs):
            path.mkdir(parents=True)
        sentinel = local / "not-an-app-owned-file.txt"
        sentinel.write_text("must survive", encoding="ascii")
        env = {
            **os.environ,
            "LOCALAPPDATA": str(local),
            "APPDATA": str(roam),
            # Simulate hosted runners with optional PowerShell auto-modules
            # unavailable, rather than relying on an inherited PSModulePath.
            "PSModulePath": "",
        }
        ps = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
        ]

        def action(source: Path, verb: str):
            return subprocess.run(
                [*ps, str(source), "-Action", verb],
                env=env,
                capture_output=True,
                text=True,
                timeout=55,
            )

        # A modified ZIP is refused BEFORE writing an install directory.
        archive = extraction / setup.REVIEWED_ARCHIVE
        original = archive.read_bytes()
        archive.write_bytes(original + b"tamper")
        reject = action(script, "Install")
        self.assertNotEqual(reject.returncode, 0)
        self.assertFalse((local / "MedOrigin-D2-Private-Developer-QA").exists())
        archive.write_bytes(original)

        installed = local / "MedOrigin-D2-Private-Developer-QA" / "InstalledPreview"
        install = action(script, "Install")
        self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
        self.assertTrue(installed.is_dir())
        self.assertEqual(
            {item.name for item in installed.iterdir()},
            {*setup.FILES, setup.INSTALLER_SCRIPT},
        )
        for name, original_data in setup._read_exact_zip_members(self.archive).items():
            self.assertEqual((installed / name).read_bytes(), original_data)
        verify = action(installed / setup.INSTALLER_SCRIPT, "Verify")
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        self.assertTrue(any(programs.glob("MedOrigin Synthetic Preview.lnk")))
        self.assertTrue(any(programs.glob("Uninstall MedOrigin Synthetic Preview.lnk")))
        # A replaced shortcut must never pass integrity verification.
        link = programs / "MedOrigin Synthetic Preview.lnk"
        original_link = link.read_bytes()
        link.write_bytes(b"fake-not-a-windows-shell-link")
        self.assertNotEqual(action(installed / setup.INSTALLER_SCRIPT, "Verify").returncode, 0)
        link.write_bytes(original_link)
        self.assertEqual(action(installed / setup.INSTALLER_SCRIPT, "Verify").returncode, 0)

        # Also reject a syntactically valid .lnk redirected to a different
        # existing file. A corrupt .lnk test alone cannot prove this invariant.
        def retarget(destination: Path):
            command = (
                "$link=(New-Object -ComObject WScript.Shell).CreateShortcut('"
                + str(link)
                + "');$link.TargetPath='"
                + str(destination)
                + "';$link.Save()"
            )
            return subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )

        redirect = retarget(sentinel)
        self.assertEqual(redirect.returncode, 0, redirect.stdout + redirect.stderr)
        self.assertNotEqual(action(installed / setup.INSTALLER_SCRIPT, "Verify").returncode, 0)
        restore = retarget(installed / "medorigin-desktop-d2-native-egui.exe")
        self.assertEqual(restore.returncode, 0, restore.stdout + restore.stderr)
        self.assertEqual(action(installed / setup.INSTALLER_SCRIPT, "Verify").returncode, 0)

        tampered = installed / "README-SYNTHETIC.txt"
        before = tampered.read_bytes()
        tampered.write_bytes(before + b"tamper")
        refused = action(installed / setup.INSTALLER_SCRIPT, "Verify")
        self.assertNotEqual(refused.returncode, 0)
        tampered.write_bytes(before)
        self.assertEqual(action(installed / setup.INSTALLER_SCRIPT, "Verify").returncode, 0)
        # The extraction copy is not authorized to uninstall a real installed
        # profile, even when its embedded archive and manifest are valid.
        stray_uninstall = action(script, "Uninstall")
        self.assertNotEqual(stray_uninstall.returncode, 0)
        self.assertTrue(installed.is_dir())
        remove = action(installed / setup.INSTALLER_SCRIPT, "Uninstall")
        self.assertEqual(remove.returncode, 0, remove.stdout + remove.stderr)
        self.assertFalse(installed.exists())
        self.assertFalse(list(programs.glob("*MedOrigin Synthetic Preview.lnk")))
        self.assertEqual(sentinel.read_text(encoding="ascii"), "must survive")


if __name__ == "__main__":
    unittest.main()
