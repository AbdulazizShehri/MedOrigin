"""Offline source-only QA of one-shot installed Core -> native GUI boundary."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent
sys.path.insert(0, str(DIR))
import qualify_installed_core_into_native_gui as guiqa


class NativeOneShotCoreSourceTests(unittest.TestCase):
    def test_real_mac_gui_source_is_present_with_qa_outcome(self):
        native = (ROOT / "src/main.rs").read_text(encoding="utf-8")
        self.assertIn('EXPLICIT_SYNTHETIC_CORE_FLAG: &str = "--synthetic-core-stdin"', native)
        self.assertIn("fn make_app<R: Read>", native)
        self.assertIn(".take(MAX_FICTIONAL_CORE_STDIN as u64 + 1)", native)
        self.assertIn("read_to_end(&mut bytes)", native)
        self.assertIn("if args.is_empty()", native)
        self.assertIn("unapproved_d2_synthetic_core_stdin_report", native)
        self.assertNotIn("std::process::Command", native)
        self.assertNotIn("std::net::", native)
        self.assertNotIn("std::fs::", native)

    def test_external_report_is_source_pinned_and_cleared_by_other_actions(self):
        source = (ROOT / "src/core_provenance.rs").read_text(encoding="utf-8")
        app = (ROOT / "src/app.rs").read_text(encoding="utf-8")
        self.assertIn("admit_exact_source_reviewed_external_core_report", source)
        self.assertIn("inspect_pinned_core_report(0)", source)
        self.assertIn("inspect_pinned_core_report(1)", source)
        self.assertIn("from_one_time_fictional_core_stdin", app)
        self.assertIn("external_core_source_visible = false", app)
        self.assertIn("GUI does not authenticate its origin or freshness", app)
        self.assertIn("not_validated", source)
        self.assertNotIn("Command::new(", app)

    def test_source_controlled_ax_accepts_both_report_sha_and_origin_warning(self):
        ax = (ROOT / "tests/macos-installed-core-stdin-live-ax-qualification.swift").read_text()
        self.assertIn("AXIsProcessTrusted", ax)
        self.assertIn("windows.count == 1", ax)
        self.assertIn("Source report SHA-256:", ax)
        self.assertIn("Core status: not_validated", ax)
        self.assertIn("FHIR R4 NOT validated", ax)
        self.assertIn("One-shot external stdin synthetic Core report accepted", ax)
        self.assertIn("MACOS_INSTALLED_CORE_STDIN_GUI_AX_EXACT_SHA_NOT_VALIDATED_PASS", ax)

    def test_actual_gui_runner_denies_non_mac_before_running_any_process(self):
        with patch.object(guiqa.sys, "platform", "win32"):
            with self.assertRaisesRegex(ValueError, "apple_silicon"):
                guiqa.qualify_gui(*([Path("/not-present")] * 3),
                    Path("/not-present"), "0" * 64, Path("/not-present"), "0" * 64)


if __name__ == "__main__":
    unittest.main()
