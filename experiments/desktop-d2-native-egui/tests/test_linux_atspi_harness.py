"""Pure source and negative-path tests; never open X11 or alter real D-Bus."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parent / "linux-native-fhir-atspi-qualification.py"
SPEC = importlib.util.spec_from_file_location("medorigin_linux_atspi_qualification", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise AssertionError("Native Linux acceptance source could not be loaded")
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


class FakeAccessible:
    """Tiny read-only AT-SPI tree double for exact application/frame matching."""

    def __init__(
        self,
        accessible_name: str,
        accessible_role: str,
        children: list[FakeAccessible] | None = None,
    ) -> None:
        self.name = accessible_name
        self._role = accessible_role
        self._children = children or []
        self.childCount = len(self._children)

    def getRoleName(self) -> str:  # noqa: N802 - external pyatspi interface
        return self._role

    def getChildAtIndex(self, index: int) -> FakeAccessible:  # noqa: N802 - pyatspi
        return self._children[index]


class LinuxATSPITestHarness(unittest.TestCase):
    def test_real_linux_accesskit_frame_may_be_unnamed(self) -> None:
        # Source-bound hosted log: process-name APPLICATION, unnamed FRAME,
        # GUI title as its child LABEL. Never use Windows/macOS frame title.
        frame = FakeAccessible(
            "",
            "frame",
            [
                FakeAccessible("MedOrigin — Native Rust Experiment", "label"),
                FakeAccessible("patient-minimal (57 bytes)", "toggle button"),
                FakeAccessible("Verify synthetic SHA-256", "push button"),
            ],
        )
        app = FakeAccessible("medorigin-desktop-d2-native-egui", "application", [frame])
        desktop = FakeAccessible("main", "desktop frame", [app])
        self.assertIs(APP.find_native_frame(desktop), frame)

    def test_ambiguous_or_forged_native_accessibility_identity_is_refused(self) -> None:
        def genuine_frame() -> FakeAccessible:
            return FakeAccessible(
                "",
                "frame",
                [
                    FakeAccessible("MedOrigin — Native Rust Experiment", "label"),
                    FakeAccessible("patient-minimal (57 bytes)", "toggle button"),
                    FakeAccessible("Verify synthetic SHA-256", "push button"),
                ],
            )

        wrong_app = FakeAccessible("other-desktop-app", "application", [genuine_frame()])
        self.assertIsNone(
            APP.find_native_frame(FakeAccessible("main", "desktop frame", [wrong_app]))
        )
        untrusted = FakeAccessible(
            "medorigin-desktop-d2-native-egui",
            "application",
            [
                FakeAccessible(
                    "", "frame", [FakeAccessible("patient-minimal (57 bytes)", "toggle button")]
                )
            ],
        )
        self.assertIsNone(
            APP.find_native_frame(FakeAccessible("main", "desktop frame", [untrusted]))
        )
        duplicated = FakeAccessible(
            "medorigin-desktop-d2-native-egui", "application", [genuine_frame(), genuine_frame()]
        )
        self.assertIsNone(
            APP.find_native_frame(FakeAccessible("main", "desktop frame", [duplicated]))
        )

    def test_fictional_fixture_switch_must_clear_previous_receipt_before_verify(self) -> None:
        sha = FakeAccessible("Synthetic raw SHA-256 verified: earlier", "label")
        status = FakeAccessible("Fictional FHIR envelope: INVALID_REFERENCE", "label")
        old = FakeAccessible("fake native frame", "frame", [sha, status])
        self.assertFalse(APP.verification_receipts_cleared(old))
        self.assertFalse(
            APP.verification_receipts_cleared(FakeAccessible("fake native frame", "frame", [sha]))
        )
        new = FakeAccessible(
            "fake native frame",
            "frame",
            [FakeAccessible("patient-minimal (57 bytes)", "toggle button")],
        )
        self.assertTrue(APP.verification_receipts_cleared(new))

    def test_preview_mode_refuses_bad_executable_digest_before_atspi_import(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "medorigin-desktop-d2-native-egui"
            path.write_bytes(b"fictional-only-byte-content")
            with (
                patch.object(APP.sys, "argv", ["test", str(path), "0" * 64, "--preview"]),
                self.assertRaisesRegex(APP.FatalQualificationError, "binary identity mismatch"),
            ):
                APP.main()

    def test_preview_only_uses_exact_synthetic_ui_literals(self) -> None:
        import inspect

        source = inspect.getsource(APP.verify_linux_fictional_json_preview)
        self.assertIn("Inspect fictional JSON (verified, read-only)", source)
        self.assertIn("Raw fictional source JSON - no normalization or FHIR R4 validation", source)
        self.assertIn("No JSON preview for this raw-byte boundary test fixture.", source)
        self.assertIn("LINUX_D2_JSON_PREVIEW_3_OF_3_PASS_NONPUBLISHING", source)

    def test_keyboard_mode_rejects_unknown_action_before_app_launch(self) -> None:
        with (
            patch.object(APP.sys, "argv", ["test", "/missing/file", "0" * 64, "--unsafe"]),
            self.assertRaisesRegex(APP.FatalQualificationError, "usage"),
        ):
            APP.main()

    def test_keyboard_only_mode_never_programmatically_presses_atspi_action(self) -> None:
        import inspect

        source = inspect.getsource(APP.verify_linux_keyboard_only)
        self.assertIn('["xdotool", "key"', source)
        self.assertIn('"shift+Tab"', source)
        self.assertIn("STATE_FOCUSED", source)
        self.assertNotIn("press(", source)
        self.assertNotIn(".queryAction(", source)
        self.assertIn("LINUX_D2_KEYBOARD_4_OF_4_PASS_NONPUBLISHING", source)

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

        self.assertEqual(
            APP.wait_for(transient_then_present, "window", 2), "native accessible window"
        )
        self.assertEqual(called, 2)

    def test_invalid_expected_binary_digest_rejected_before_importing_atspi(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "medorigin-desktop-d2-native-egui"
            path.write_bytes(b"fictional-only-fixture")
            with (
                patch.object(APP.sys, "argv", ["test", str(path), "0" * 64]),
                self.assertRaisesRegex(APP.FatalQualificationError, "binary identity mismatch"),
            ):
                APP.main()

    def test_missing_binary_refused_before_any_service_or_app_is_started(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "medorigin-desktop-d2-native-egui"
            with (
                patch.object(APP.sys, "argv", ["test", str(path), "0" * 64]),
                self.assertRaisesRegex(APP.FatalQualificationError, "explicit native"),
            ):
                APP.main()

    def test_only_fixed_fictional_catalog_is_present(self) -> None:
        self.assertEqual(len(APP.CASES), 12)
        self.assertEqual(len({case[0] for case in APP.CASES}), 12)
        self.assertEqual(APP.CASES[0][0], "patient-minimal")
        self.assertEqual(APP.CASES[-1][0], "bundle-dangling")
        self.assertTrue(all(len(case[2]) == 64 for case in APP.CASES))


if __name__ == "__main__":
    unittest.main()
