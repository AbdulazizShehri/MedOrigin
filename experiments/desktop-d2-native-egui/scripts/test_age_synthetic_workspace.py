"""Fail-closed source-level checks for fictional age workspace QA, no PHI."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_age_synthetic_workspace as ageqa


class SyntheticAgeWorkspaceTests(unittest.TestCase):
    def test_pinned_fixture_is_only_authorized_bytes(self):
        self.assertEqual(ageqa.hash_bytes(ageqa.FIXTURE.rstrip(b"\n")), ageqa.FIXTURE_SHA256)
        ageqa.authorize_fixed_synthetic_only(
            ageqa.FIXTURE,
            role="synthetic_test_owner",
            consent=True,
            purpose="synthetic_workspace_qa",
        )

    def test_roles_consent_and_purpose_must_be_exact(self):
        for role, consent, purpose in (
            ("clinician", True, "synthetic_workspace_qa"),
            ("synthetic_test_owner", False, "synthetic_workspace_qa"),
            ("synthetic_test_owner", None, "synthetic_workspace_qa"),
            ("synthetic_test_owner", 1, "synthetic_workspace_qa"),
            ("synthetic_test_owner", True, "clinical_workspace"),
            ("owner", True, "synthetic_workspace_qa"),
        ):
            with (
                self.subTest(role=role, consent=consent, purpose=purpose),
                self.assertRaisesRegex(ValueError, "intent_not_authorized"),
            ):
                ageqa.authorize_fixed_synthetic_only(
                    ageqa.FIXTURE,
                    role=role,
                    consent=consent,
                    purpose=purpose,
                )

    def test_noncanonical_and_clinical_looking_payloads_are_refused(self):
        for data in (
            b"",
            b"{}",
            ageqa.FIXTURE.rstrip(b"\n"),
            ageqa.FIXTURE + b"\n",
            b'{"resourceType":"Patient","name":"fake-test-data"}\n',
        ):
            with (
                self.subTest(data=data[:18]),
                self.assertRaisesRegex(ValueError, "payload_refused"),
            ):
                ageqa.authorize_fixed_synthetic_only(
                    data,
                    role="synthetic_test_owner",
                    consent=True,
                    purpose="synthetic_workspace_qa",
                )

    def test_source_bound_ciphertext_file_has_private_mode_and_refuses_overwrite(self):
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir(mode=0o700)
            vault.chmod(0o700)
            blob = b"x" * 350  # synthetic fake ciphertext; not a crypto-positive test
            target = ageqa.stage_ciphertext_exclusively(vault, "synthetic.age", blob)
            self.assertEqual(target.read_bytes(), blob)
            if os.name == "posix":
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with self.assertRaisesRegex(ValueError, "refuse_replace"):
                ageqa.stage_ciphertext_exclusively(vault, "synthetic.age", blob)
            self.assertEqual(target.read_bytes(), blob)

    def test_path_traversal_and_invalid_names_are_refused(self):
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir(mode=0o700)
            vault.chmod(0o700)
            for name in (
                "../escape.age",
                "UPPER.age",
                "patient.json",
                ".age",
                "synthetic/../../evil.age",
                "multi unicode 😃.age",
            ):
                with (
                    self.subTest(name=name),
                    self.assertRaisesRegex(ValueError, "filename_unapproved"),
                ):
                    ageqa.stage_ciphertext_exclusively(vault, name, b"x" * 350)

    def test_staging_file_collision_is_refused(self):
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir(mode=0o700)
            vault.chmod(0o700)
            staging = vault / "synthetic.age.staging"
            staging.write_bytes(b"unreviewed")
            with self.assertRaisesRegex(ValueError, "staging_conflict"):
                ageqa.stage_ciphertext_exclusively(vault, "synthetic.age", b"x" * 350)
            self.assertEqual(staging.read_bytes(), b"unreviewed")

    @unittest.skipUnless(os.name == "posix", "POSIX access mode boundary")
    def test_symlink_and_world_readable_vault_are_refused(self):
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir(mode=0o700)
            vault.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "not_owner_private"):
                ageqa.stage_ciphertext_exclusively(vault, "synthetic.age", b"x" * 350)
            vault.chmod(0o700)
            alias = Path(tmp) / "alias"
            alias.symlink_to(vault, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "not_regular"):
                ageqa.stage_ciphertext_exclusively(alias, "synthetic.age", b"x" * 350)

    def test_executable_identity_requires_approved_sha_before_invocation(self):
        with TemporaryDirectory() as tmp:
            binary = Path(tmp) / "age"
            binary.write_bytes(b"untrusted")
            if os.name == "posix":
                binary.chmod(0o700)
            with self.assertRaisesRegex(ValueError, "(binary_hash_changed|not_regular_executable)"):
                ageqa.prove_binary(binary, "0" * 64, "age")
            with self.assertRaisesRegex(ValueError, "unapproved_sha256"):
                ageqa.prove_binary(binary, "bad", "age")

    def test_real_crypto_host_non_mac_is_refused_before_any_process(self):
        with (
            patch.object(ageqa.sys, "platform", "win32"),
            self.assertRaisesRegex(ValueError, "real_macos"),
        ):
            ageqa.qualify(
                Path("/x"),
                "0" * 64,
                Path("/y"),
                "0" * 64,
            )


if __name__ == "__main__":
    unittest.main()
