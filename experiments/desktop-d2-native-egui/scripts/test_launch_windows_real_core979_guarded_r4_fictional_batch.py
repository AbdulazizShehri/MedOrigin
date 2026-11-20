"""Unit contracts for the strict exact-Core979 opt-in native R4 worklist launcher."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import launch_windows_real_core971_official_r4_fictional_batch as r4
import launch_windows_real_core979_guarded_r4_fictional_batch as core979


class GuardedCore979Contracts(unittest.TestCase):
    def test_only_exact_known_sha_and_mutually_exclusive_modes(self):
        self.assertEqual(core979.CORE979_SHA, "440cee21494a62c458106631931f3610c05d1ea8")
        self.assertEqual(r4.CORE979_SHA, core979.CORE979_SHA)
        self.assertEqual(r4.CORE971_SHA, "9c27397f956303f92aeaf4bc173257c093a53238")
        with self.assertRaisesRegex(ValueError, "core_source_revision_not_reviewed"):
            r4._attest_core(Path("missing"), required_core_sha="0" * 40)
        with self.assertRaisesRegex(ValueError, "core_source_revision_not_reviewed"):
            r4.launch(
                Path("missing"),
                Path("missing"),
                "0" * 64,
                Path("missing"),
                required_core_sha="1" * 40,
            )
        with (
            patch.object(sys, "platform", "linux"),
            self.assertRaisesRegex(ValueError, "guarded_core979_windows_host_required"),
        ):
            core979.launch(Path("missing"), Path("missing"), "0" * 64, Path("missing"))
        with (
            patch.object(sys, "platform", "win32"),
            self.assertRaisesRegex(ValueError, "guarded_core979_qa_mode_conflict"),
        ):
            core979.launch(
                Path("missing"),
                Path("missing"),
                "0" * 64,
                Path("missing"),
                qa_auto_close=True,
                qa_uia=True,
            )

    def test_probe_checks_positive_and_negative_regardless_of_entry_order(self):
        probe = core979._CROSS_PERSON_PROBE
        self.assertIn("inspect_synthetic_bundle(good)", probe)
        self.assertIn("observation_encounter_patient_mismatch", probe)
        self.assertIn("reversed(valid['entry'])", probe)
        self.assertIn("INVENTED_PRIVATE_NAME_NEVER_LOGGED", probe)
        self.assertIn("clinical_use_authorized", probe)
        self.assertNotIn("https://", probe)
        self.assertNotIn("socket", probe)

    def test_source_gate_requires_pin_and_executes_probe_before_gui(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)
            path = source / "tests/test_workspace_guarded_sha256.py"
            path.parent.mkdir()
            path.write_text("# fixture")
            with (
                patch.object(r4, "_attest_core", return_value=source) as attest,
                patch.object(
                    core979.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0, b"", b""),
                ) as run,
            ):
                self.assertEqual(core979._require_guarded_core(source), source)
            self.assertEqual(attest.call_count, 2)
            for item in attest.call_args_list:
                self.assertEqual(item.kwargs["required_core_sha"], core979.CORE979_SHA)
            self.assertEqual(run.call_count, 1)
            argv = run.call_args.args[0]
            self.assertEqual(argv[1:3], ["-B", "-c"])
            self.assertIn("observation_encounter_patient_mismatch", argv[3])
            self.assertTrue(run.call_args.kwargs["capture_output"])
            self.assertEqual(run.call_args.kwargs["timeout"], 60)

    def test_source_without_sha_guard_never_starts_probe(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)
            with (
                patch.object(r4, "_attest_core", return_value=source),
                patch.object(core979.subprocess, "run") as run,
            ):
                with self.assertRaisesRegex(ValueError, "guarded_core979_sha_boundary_missing"):
                    core979._require_guarded_core(source)
                run.assert_not_called()

    def test_probe_denies_nonzero_stdout_stderr_and_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)
            path = source / "tests/test_workspace_guarded_sha256.py"
            path.parent.mkdir()
            path.write_text("# fixture")
            for failure in (
                subprocess.CompletedProcess([], 1, b"", b""),
                subprocess.CompletedProcess([], 0, b"sensitive", b""),
                subprocess.CompletedProcess([], 0, b"", b"sensitive"),
            ):
                with (
                    patch.object(r4, "_attest_core", return_value=source),
                    patch.object(core979.subprocess, "run", return_value=failure),
                    self.assertRaisesRegex(
                        ValueError, "guarded_core979_cross_patient_preflight_refused"
                    ),
                ):
                    core979._require_guarded_core(source)
            with (
                patch.object(r4, "_attest_core", return_value=source),
                patch.object(
                    core979.subprocess, "run", side_effect=subprocess.TimeoutExpired(["python"], 15)
                ),
                self.assertRaisesRegex(
                    ValueError, "guarded_core979_cross_patient_probe_unavailable"
                ),
            ):
                core979._require_guarded_core(source)

    def test_only_guarded_sha_is_delegated_to_exact_hmac_r4_bridge(self):
        with (
            patch.object(sys, "platform", "win32"),
            patch.object(core979, "_require_guarded_core", return_value=Path("reviewed")) as guard,
            patch.object(r4, "launch") as launch,
        ):
            core979.launch(
                Path("source"),
                Path("medorigin-desktop-d2-native-egui.exe"),
                "a" * 64,
                Path("fhir.schema.json.zip"),
                qa_uia=True,
            )
            guard.assert_called_once_with(Path("source"))
            launch.assert_called_once()
            self.assertEqual(launch.call_args.kwargs["required_core_sha"], core979.CORE979_SHA)
            self.assertTrue(launch.call_args.kwargs["qa_uia"])
            self.assertFalse(launch.call_args.kwargs["qa_auto_close"])

    def test_wrapper_preserves_no_patient_selection_and_test_only_hmac_contract(self):
        code = Path(core979.__file__).read_text("utf8")
        old = Path(r4.__file__).read_text("utf8")
        self.assertNotIn('parser.add_argument("--patient', code)
        self.assertNotIn('parser.add_argument("--files', code)
        self.assertNotIn("credential_manager", code)
        self.assertNotIn("WindowsProtectedSyntheticKeyProvider", code)
        self.assertIn("legacy.D2_SESSION_BATCH_FLAG", old)
        self.assertIn("legacy._per_launch_core_frame", old)
        self.assertIn("--offline-r4-schema", old)
        self.assertIn("--synthetic-only", r4.CHILD)
        self.assertIn("--ephemeral-demo", r4.CHILD)


if __name__ == "__main__":
    unittest.main()
