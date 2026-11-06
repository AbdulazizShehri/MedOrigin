"""Adversarial offline installed Wheel-to-Git source identity contract.

The tests use a synthetic two-package filesystem and fake git output; they
are safe for hosted Windows/Ubuntu without fetching packages or using PHI.
"""

from __future__ import annotations

import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import attest_installed_encrypted_core_readback as qa


class AttestedInstalledCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="test-installed-synthetic-wheel-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.core = self.base / "core"
        self.wheels = self.base / "wheels"
        self.site = self.base / "site"
        for folder in (self.core, self.wheels, self.site):
            folder.mkdir()
        self.sources = {}
        specifications = []
        for module, section, wheel_name in (
            ("medscale", "src/medscale", "source-core.whl"),
            ("medscale_workspace", "apps/workspace/src/medscale_workspace", "source-workspace.whl"),
        ):
            source = self.core / section / "reviewed.py"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"FICTIONAL_ONLY = True\n")
            installed = self.site / module / "reviewed.py"
            installed.parent.mkdir(parents=True)
            installed.write_bytes(source.read_bytes())
            path = module + "/reviewed.py"
            with zipfile.ZipFile(self.wheels / wheel_name, "w") as archive:
                archive.writestr(path, source.read_bytes())
            specifications.append(
                (
                    module,
                    section,
                    wheel_name,
                    qa.sha256((self.wheels / wheel_name).read_bytes()),
                    1,
                )
            )
            self.sources[section] = section + "/reviewed.py"
        self.expected_site = {"medscale", "medscale_workspace"}
        self.patches = [
            patch.object(qa, "EXPECTED_WHEELS", tuple(specifications)),
            patch.object(qa, "EXPECTED_SITE", self.expected_site),
            patch.object(qa.subprocess, "run", side_effect=self.git_run),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def git_run(self, args, **kwargs):
        op = args[3]
        if op == "rev-parse":
            return SimpleNamespace(stdout=qa.PINNED_CORE_SHA + "\n")
        if op == "status":
            return SimpleNamespace(stdout=b"")
        if op == "ls-files":
            return SimpleNamespace(stdout=(self.sources[args[-1]] + "\x00").encode())
        raise AssertionError("unexpected git operation")

    def verified(self):
        qa.attest_installed(self.core, self.wheels, self.site)

    def test_approved_source_wheel_and_installed_package_matches(self):
        self.verified()

    def test_installed_python_source_mutation_is_rejected(self):
        target = self.site / "medscale/reviewed.py"
        target.write_text("print('FORGED')\n")
        with self.assertRaisesRegex(ValueError, "installed_core_wheel_module"):
            self.verified()

    def test_tracked_source_drift_is_rejected_even_when_wheel_pinned(self):
        (self.core / "src/medscale/reviewed.py").write_bytes(b"CHANGED\n")
        with self.assertRaisesRegex(ValueError, "installed_core_wheel_module"):
            self.verified()

    def test_forged_wheel_bytes_are_rejected(self):
        (self.wheels / "source-core.whl").write_bytes(b"not a reviewed wheel")
        with self.assertRaisesRegex(ValueError, "approved_offline_wheel_content_mismatch"):
            self.verified()

    def test_ignored_bytecode_or_native_loader_in_site_is_rejected(self):
        target = self.site / "medscale/__pycache__"
        target.mkdir()
        with self.assertRaisesRegex(ValueError, "symlink_or_bytecode"):
            self.verified()
        target.rmdir()
        (self.site / "medscale/injected.pyd").write_bytes(b"FORGED")
        with self.assertRaisesRegex(ValueError, "executable_shadow_refused"):
            self.verified()

    def test_unapproved_source_file_ignored_by_git_is_rejected(self):
        (self.core / "src/medscale/unaudited.py").write_bytes(b"unreviewed code")
        with self.assertRaisesRegex(ValueError, "unreviewed_ignored_or_missing_source"):
            self.verified()

    def test_unapproved_site_top_level_pth_or_package_rejected(self):
        (self.site / "evil.pth").write_text("import evil\n")
        with self.assertRaisesRegex(ValueError, "unreviewed_top_level_entry"):
            self.verified()

    def test_imported_wheel_additional_file_is_rejected(self):
        wheel = self.wheels / "source-core.whl"
        with zipfile.ZipFile(wheel, "a") as archive:
            archive.writestr("medscale/injected.py", b"SHADOW\n")
        # For this adversarial test the Wheel hash is deliberately re-pinned
        # to the attacker's altered bytes to test inventory defense in depth.
        specs = list(qa.EXPECTED_WHEELS)
        original = specs[0]
        specs[0] = (
            original[0],
            original[1],
            original[2],
            qa.sha256(wheel.read_bytes()),
            original[4],
        )
        with (
            patch.object(qa, "EXPECTED_WHEELS", tuple(specs)),
            self.assertRaisesRegex(ValueError, "wheel_does_not_match"),
        ):
            self.verified()

    def test_explicit_empty_or_partial_wheel_pinset_never_falls_back_to_default(self):
        with self.assertRaisesRegex(ValueError, "two_exact_approved_wheel_packages_required"):
            qa.attest_installed(self.core, self.wheels, self.site, approved_wheels=())
        with self.assertRaisesRegex(ValueError, "two_exact_approved_wheel_packages_required"):
            qa.attest_installed(
                self.core,
                self.wheels,
                self.site,
                approved_wheels=(qa.EXPECTED_WHEELS[0],),
            )

    def test_installed_readback_runner_requires_mac_sandbox_and_explicit_site(self):
        from unittest.mock import patch as patched

        import qualify_mac_installed_encrypted_readback_gui as runner

        source = Path(runner.__file__).read_text()
        self.assertIn("attest_installed(core, wheels, site)", source)
        self.assertEqual(source.count("attest_installed(core, wheels, site)"), 2)
        self.assertIn("prove_restrictive_mac_policy(profile, work, python)", source)
        self.assertIn("run_sandboxed(", source)
        self.assertIn("proc.terminate()", source)
        self.assertIn("proc.kill()", source)
        self.assertIn("result.stdout != fixture.read_bytes()", source)
        self.assertIn("--synthetic-encrypted-readback-stdin", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("requests.", source)
        with (
            patched.object(runner.sys, "platform", "linux"),
            self.assertRaisesRegex(ValueError, "genuine_mac_apple_silicon"),
        ):
            runner.qualify(None)

    def test_dirty_git_checkout_refused_even_when_files_match(self):
        def dirty_run(args, **kwargs):
            if args[3] == "status":
                return SimpleNamespace(stdout=b" M src/medscale/reviewed.py\n")
            return self.git_run(args, **kwargs)

        with (
            patch.object(qa.subprocess, "run", side_effect=dirty_run),
            self.assertRaisesRegex(ValueError, "git_checkout_modified"),
        ):
            self.verified()


if __name__ == "__main__":
    unittest.main()
