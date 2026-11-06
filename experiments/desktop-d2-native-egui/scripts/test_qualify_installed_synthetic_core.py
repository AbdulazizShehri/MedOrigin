"""Offline hostile-input tests for SOURCE ATTESTED installed Wheel Core QA.

Never build/install packages, contact GitHub, or use clinical/user content.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_installed_synthetic_core as installed


class InstalledWheelD2Tests(unittest.TestCase):
    def test_wheel_record_digest_and_self_record_are_exact(self):
        digest = installed._digest_record(b"fake fictional code")
        self.assertEqual(len(digest), 43)
        result = installed.parse_record(
            (
                "medscale/fake.py,sha256=" + digest + ",19\nmedscale-0.3.0.dist-info/RECORD,,\n"
            ).encode()
        )
        self.assertEqual(result["medscale/fake.py"], (digest, 19))
        self.assertIsNone(result["medscale-0.3.0.dist-info/RECORD"])

    def test_malformed_or_duplicate_record_is_refused(self):
        for malicious in (
            b"medscale/foo.py,sha256=bogus,7\n",
            b"medscale/foo.py,,\n",
            b"medscale/foo.py,sha512=x,5\n",
            b"medscale/foo.py,sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,-1\n",
            b"medscale/foo.py,sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,1000000000\n",
            b"medscale/foo.py,sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,1\n"
            b"medscale/foo.py,sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,1\n",
            b"medscale/foo.py,sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
        ):
            with self.subTest(malicious=malicious[:33]), self.assertRaises(ValueError):
                installed.parse_record(malicious)

    def test_record_paths_are_bounded_even_for_generated_venv_launcher(self):
        digest = installed._digest_record(b"one")
        for name in (
            "../unsafe",
            "medscale/../../bad.py",
            "/absolute",
            "medscale/./bad.py",
            "../../../bin/malicious",
            "medscale\\evil.py",
        ):
            with self.subTest(name=name):
                record = (f"{name},sha256={digest},3\n").encode()
                with self.assertRaisesRegex(ValueError, "path_traversal"):
                    installed.parse_record(record, allow_venv_script=True)
        valid_generated = f"../../../bin/medscale,sha256={digest},3\n".encode()
        with self.assertRaisesRegex(ValueError, "path_traversal"):
            installed.parse_record(valid_generated)
        self.assertEqual(
            installed.parse_record(valid_generated, allow_venv_script=True)[
                "../../../bin/medscale"
            ],
            (digest, 3),
        )

    def test_changed_or_missing_wheel_rejected_before_install_observation(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / installed.WHEEL_FILENAME
            wheel.write_bytes(b"unreviewed modified wheel")
            with patch.object(installed.base, "source_commit", return_value="pinned"):
                with self.assertRaisesRegex(ValueError, "wheel_changed_or_unapproved"):
                    installed.attest_offline_wheel_and_install(root, wheel, root)
                with self.assertRaisesRegex(ValueError, "wheel_filename_or_file_refused"):
                    installed.attest_offline_wheel_and_install(
                        root,
                        root / "missing.whl",
                        root,
                    )

    def test_symlinked_wheel_and_extra_startup_hook_are_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.chmod(0o700)
            wheel = root / installed.WHEEL_FILENAME
            actual = root / "real.whl"
            actual.write_bytes(b"wheel-like synthetic test bytes")
            can_symlink = True
            try:
                wheel.symlink_to(actual)
            except (OSError, NotImplementedError):
                can_symlink = False
            with patch.object(installed.base, "source_commit", return_value="pinned"):
                if can_symlink:
                    with self.assertRaisesRegex(ValueError, "wheel_filename_or_file_refused"):
                        installed.attest_offline_wheel_and_install(root, wheel, root)
                    wheel.unlink()
                wheel.write_bytes(b"wheel-like synthetic test bytes")
                venv = root / "venv"
                venv.mkdir(mode=0o700)
                venv.chmod(0o700)
                (venv / "pyvenv.cfg").write_text("home = synthetic\n")
                site = venv / "lib/python3.11/site-packages"
                site.mkdir(parents=True)
                (site / "unreviewed-hook.pth").write_text("import usercode\n")
                with (
                    patch.object(
                        installed, "WHEEL_SHA256", installed.base.sha256(wheel.read_bytes())
                    ),
                    self.assertRaisesRegex(ValueError, "startup_hook"),
                ):
                    installed.attest_offline_wheel_and_install(root, wheel, venv)

    def test_non_macos_never_attempts_launch_or_read_fhir(self):
        with (
            patch.object(installed.sys, "platform", "win32"),
            self.assertRaisesRegex(ValueError, "macos_arm64"),
        ):
            installed.qualify(
                Path("/invalid"),
                Path("/invalid"),
                Path("/invalid"),
                Path("/invalid"),
                "0" * 64,
                Path("/invalid"),
                "0" * 64,
            )

    def test_isolated_installed_python_disables_startup_hooks(self):
        self.assertIn("sys.path.insert(0,sys.argv[1])", installed.INSTALLED_CODE)
        self.assertIn("from medscale.cli.fhir import main", installed.INSTALLED_CODE)
        self.assertIn("INSTALLED_CORE_PACKAGED_SOURCE_ONLY", installed.ISOLATED_SOURCE_PROBE)
        self.assertEqual(installed.WHEEL_PACKAGE_FILES, 250)
        self.assertEqual(installed.WHEEL_MEMBERS, 255)
        self.assertEqual(
            installed.WHEEL_SHA256,
            "4f3a66c9657c8040832970fdffcaa0d2bf15c74c79ae76b17566fe573c9536c2",
        )
        source = Path(installed.__file__).read_text()
        self.assertRegex(source, r'"-I"\s*,\s*"-S"\s*,\s*"-B"')
        self.assertIn("prove_restrictive_mac_policy", source)
        self.assertIn("attest_offline_wheel_and_install(core, wheel, venv)", source)
        self.assertIn('forged["status"] = "valid"', source)


if __name__ == "__main__":
    unittest.main()
