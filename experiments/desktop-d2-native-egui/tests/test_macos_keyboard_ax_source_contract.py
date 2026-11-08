"""Source-only checks: macOS AX/keyboard test must keep bounded actual GUI QA."""

import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent


class MacNativeAXKeyboardHarnessContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ax = (TESTS / "macos-native-ax-qualification.swift").read_text()
        cls.keyboard = (TESTS / "macos-native-keyboard-qualification.swift").read_text()

    def test_ax_window_admission_is_bounded_and_unambiguous(self):
        self.assertIn("for _ in 0..<40", self.ax)
        self.assertIn("windows.count == 1", self.ax)
        self.assertIn("guard let nativeWindow", self.ax)
        self.assertIn("AXIsProcessTrusted()", self.ax)
        self.assertIn("MACOS_AX_NO_GO", self.ax)

    def test_real_keyboard_events_and_bounded_longer_focus_cycle(self):
        self.assertIn("CGEvent(keyboardEventSource:", self.keyboard)
        self.assertIn("down.post(tap: .cghidEventTap)", self.keyboard)
        self.assertIn("for _ in 0..<28", self.keyboard)
        self.assertIn("visited.suffix(8)", self.keyboard)
        self.assertIn("tab(true)", self.keyboard)
        self.assertIn("space()", self.keyboard)
        self.assertIn("MACOS_KEYBOARD_4_OF_4_PASS_NONPUBLISHING", self.keyboard)

    def test_no_programmatic_ax_action_substitution_for_keyboard(self):
        for unsafe in ("AXUIElementPerformAction(", "kAXPressAction", "AXPress("):
            self.assertNotIn(unsafe, self.keyboard)
        self.assertIn("windows.count == 1", self.keyboard)
        self.assertIn("guard let window = nativeWindow", self.keyboard)
        self.assertIn("AXIsProcessTrusted()", self.keyboard)

    def test_no_silent_keyboard_skip_or_unbounded_target_navigation(self):
        self.assertIn("guard found else {", self.keyboard)
        self.assertIn('fail("Tab cannot reach selector', self.keyboard)
        self.assertIn("guard displayed else {", self.keyboard)
        self.assertIn('fail("Space-activated', self.keyboard)


if __name__ == "__main__":
    unittest.main()
