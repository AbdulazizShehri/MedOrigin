"""Adversarial nonclinical portable Core bundle integrity and Windows launcher tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import launch_windows_portable_fictional_core as runtime
import portable_core_tree as tree
import prepare_windows_portable_fictional_bundle as prepare


class PortableFictionalCoreContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="fake-2-file-portable-core-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in (
            "core/medscale",
            "core/medscale_workspace",
            "scripts",
            "tests",
            "fixtures/core",
            "native",
        ):
            (self.root / name).mkdir(parents=True)
        (self.root / "core/medscale/test.py").write_bytes(b"FICTIONAL_CORE=True\n")
        (self.root / "core/medscale_workspace/test.py").write_bytes(b"FICTIONAL_WORKSPACE=True\n")
        self.fake_files = (
            "scripts/synthetic_encrypted_readback_projection.py",
            "fixtures/core/encrypted-readback-projection.json",
            "fixtures/core/encrypted-persistent-readback-projection.json",
            "native/medorigin-desktop-d2-native-egui.exe",
        )
        for name in self.fake_files:
            (self.root / name).write_bytes(("toy_" + name).encode())
        self.patch_count = patch.object(tree, "EXACT_FILES", 2)
        self.patch_count.start()
        self.addCleanup(self.patch_count.stop)
        self.digest = tree.digest_installed_packages(self.root / "core")
        for module, attr, value in (
            (tree, "APPROVED_TREE_SHA256", self.digest),
            (runtime, "APPROVED_TREE_SHA256", self.digest),
            (runtime, "RUNTIME_FILES", self.fake_files),
            (runtime, "EXPORTER_SHA256", runtime.sha(self.root / self.fake_files[0])),
            (runtime, "PROJECTION_SHA", runtime.sha(self.root / self.fake_files[1])),
            (
                runtime,
                "PERSISTENT_PROJECTION_SHA256",
                runtime.sha(self.root / self.fake_files[2]),
            ),
        ):
            action = patch.object(module, attr, value)
            action.start()
            self.addCleanup(action.stop)
        self.manifest = {
            "schema": runtime.SCHEMA,
            "source_commit": runtime.PINNED_COMMIT,
            "core_sha256": self.digest,
            "source_file_count": 290,
            "generated_by": "offline_source_attested_developer_tool",
            "production_or_clinical_use_authorized": False,
            "sender_or_session_authenticated": False,
            "os_network_egress_confined": False,
            "files_sha256": {name: runtime.sha(self.root / name) for name in self.fake_files},
        }
        self.flush_manifest()

    def flush_manifest(self):
        (self.root / "manifest.json").write_text(
            json.dumps(self.manifest, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )

    def test_source_exact_portable_without_git_wheels_or_source_checkout(self):
        gui, exporter, fixture = runtime.attest_kit(self.root)
        self.assertEqual(gui, self.root / self.fake_files[3])
        self.assertEqual(exporter, self.root / self.fake_files[0])
        self.assertEqual(fixture, self.root / self.fake_files[1])
        self.assertEqual(tree.digest_installed_packages(self.root / "core"), self.digest)

    def test_mutated_core_source_with_same_file_count_refuses(self):
        (self.root / "core/medscale/test.py").write_bytes(b"FICTIONAL_CORE=FAKE\n")
        with self.assertRaisesRegex(ValueError, "source_digest_refused"):
            runtime.attest_kit(self.root)

    def test_unreviewed_core_file_and_compiled_extension_are_refused(self):
        attacker = self.root / "core/medscale/injected.py"
        attacker.write_bytes(b"print('unreviewed')\n")
        with self.assertRaisesRegex(ValueError, "file_count_changed"):
            runtime.attest_kit(self.root)
        attacker.unlink()
        attacker = self.root / "core/medscale/injected.pyd"
        attacker.write_bytes(b"fake-loader")
        with self.assertRaisesRegex(ValueError, "unreviewed_executable_refused"):
            runtime.attest_kit(self.root)

    def test_manifest_flags_and_runtime_mutation_fail_closed(self):
        self.manifest["sender_or_session_authenticated"] = True
        self.flush_manifest()
        with self.assertRaisesRegex(ValueError, "manifest_contract_refused"):
            runtime.attest_kit(self.root)
        self.manifest["sender_or_session_authenticated"] = False
        self.flush_manifest()
        (self.root / self.fake_files[0]).write_bytes(b"altered code")
        with self.assertRaisesRegex(ValueError, "checksum_refused"):
            runtime.attest_kit(self.root)

    def test_unreviewed_new_runtime_path_refused(self):
        (self.root / "scripts/evil.py").write_bytes(b"fake")
        with self.assertRaisesRegex(ValueError, "runtime_unapproved_files"):
            runtime.attest_kit(self.root)

    def test_bundle_preparation_rejects_nonwindows_and_existing_out_path(self):
        from argparse import Namespace

        with (
            patch.object(prepare.sys, "platform", "darwin"),
            self.assertRaisesRegex(ValueError, "Windows_preparation_only"),
        ):
            prepare.prepare(Namespace())

    def test_runtime_worker_uses_prepared_site_not_git_source(self):
        import supervise_windows_encrypted_core_job as supervisor

        source = Path(supervisor.__file__).read_text(encoding="utf-8")
        launcher = Path(runtime.__file__).read_text(encoding="utf-8")
        self.assertIn("core=None,", launcher)
        self.assertIn("site=site,", launcher)
        self.assertIn("exporter=exporter,", launcher)
        self.assertIn('installed_site=root / "core"', launcher)
        self.assertIn("or (core is None and installed_site is None)", source)
        self.assertIn("AssignProcessToJobObject(job, info.hProcess)", source)
        self.assertIn("api.ResumeThread(info.hThread)", source)
        self.assertLess(
            source.index("api.AssignProcessToJobObject(job, info.hProcess)"),
            source.index("api.ResumeThread(info.hThread)"),
        )
        self.assertIn("attest_portable_core_tree", launcher)
        self.assertNotIn("shell=True", launcher)
        self.assertNotIn("requests.", launcher)
        self.assertNotIn("patient-file", launcher)


if __name__ == "__main__":
    unittest.main()
