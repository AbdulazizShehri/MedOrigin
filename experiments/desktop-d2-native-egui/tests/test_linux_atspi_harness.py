"""Pure source and negative-path tests; never open X11 or alter real D-Bus."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parent / "linux-native-fhir-atspi-qualification.py"
SPEC = importlib.util.spec_from_file_location("medorigin_linux_atspi_qualification", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise AssertionError("Native Linux acceptance source could not be loaded")
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


class LinuxATSPITestHarness(unittest.TestCase):
    def test_fatal_acceptance_failure_never_retried_or_obscured(self) -> None:
        called = 0

        def actual_failure() -> object:
            nonlocal called
            called += 1
            APP.refuse("native GUI exited rc=101")

        with self.assertRaisesRegex(APP.FatalQualificationError, "rc=101"):
            APP.wait_for(actual_failure, "real native app", 0.8)
        self.assertEqual(called, 1)

    def test_temporary_registry_transient_can_retry(self) -> None:
        called = 0

        def transient_then_present() -> object:
            nonlocal called
            called += 1
            if called == 1:
                raise RuntimeError("AT-SPI initialization race")
            return "native accessible window"

        self.assertEqual(APP.wait_for(transient_then_present, "window", 2),
                         "native accessible window")
        self.assertEqual(called, 2)

    def test_invalid_expected_binary_digest_rejected_before_importing_atspi(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "medorigin-desktop-d2-native-egui"
            path.write_bytes(b"fictional-only-fixture")
            with patch.object(APP.sys, "argv", ["test", str(path), "0" * 64]):
                with self.assertRaisesRegex(APP.FatalQualificationError, "binary identity mismatch"):
                    APP.main()

    def test_missing_binary_refused_before_any_service_or_app_is_started(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "medorigin-desktop-d2-native-egui"
            with patch.object(APP.sys, "argv", ["test", str(path), "0" * 64]):
                with self.assertRaisesRegex(APP.FatalQualificationError, "explicit native"):
                    APP.main()

    def test_only_fixed_fictional_catalog_is_present(self) -> None:
        self.assertEqual(len(APP.CASES), 12)
        self.assertEqual(len({case[0] for case in APP.CASES}), 12)
        self.assertEqual(APP.CASES[0][0], "patient-minimal")
        self.assertEqual(APP.CASES[-1][0], "bundle-dangling")
        self.assertTrue(all(len(case[2]) == 64 for case in APP.CASES))


if __name__ == "__main__":
    unittest.main()
