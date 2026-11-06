"""Strict source-only review for Windows synthetic process-subtree Job Object QA."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qualify_windows_job_subtree as qa


class WindowsJobObjectSyntheticSafetyTests(unittest.TestCase):
    def test_nonwindows_fails_closed_before_loading_windows_kernel(self):
        with (
            patch.object(qa.sys, "platform", "darwin"),
            self.assertRaisesRegex(ValueError, "windows_host_required"),
        ):
            qa.qualify()

    def test_suspended_creation_and_job_membership_before_first_instruction(self):
        source = Path(qa.__file__).read_text()
        self.assertIn("CREATE_SUSPENDED | CREATE_NO_WINDOW", source)
        self.assertIn("AssignProcessToJobObject(job, parent.hProcess)", source)
        self.assertIn("api.ResumeThread(parent.hThread)", source)
        self.assertLess(
            source.index("api.AssignProcessToJobObject(job, parent.hProcess)"),
            source.index("api.ResumeThread(parent.hThread)"),
        )
        self.assertIn("api.IsProcessInJob(parent.hProcess, job", source)
        self.assertIn("api.IsProcessInJob(child_handle, job", source)

    def test_windows_closes_private_job_and_tests_real_child_lifetime(self):
        source = Path(qa.__file__).read_text()
        self.assertEqual(qa.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, 0x2000)
        self.assertIn(
            "limit.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", source
        )
        self.assertIn("api.WaitForSingleObject(parent.hProcess, 0) != WAIT_TIMEOUT", source)
        self.assertIn("api.WaitForSingleObject(child_handle, 0) != WAIT_TIMEOUT", source)
        self.assertIn("api.CloseHandle(job)", source)
        self.assertIn("api.WaitForSingleObject(parent.hProcess, 5000)", source)
        self.assertIn("api.WaitForSingleObject(child_handle, 5000)", source)
        self.assertIn("api.TerminateJobObject(job, 1)", source)
        self.assertIn("api.TerminateProcess(child_handle, 1)", source)
        self.assertIn("WINDOWS_D2_JOB_HANDLE_CLOSE_TERMINATED_PARENT_AND_CHILD", source)

    def test_no_core_ehr_or_arbitrary_process_launch_paths(self):
        source = Path(qa.__file__).read_text()
        self.assertIn("PARENT_CODE", source)
        self.assertIn('CHILD_CODE = "import time;time.sleep(60)"', source)
        self.assertIn('"-I", "-S", "-B", "-c", PARENT_CODE', source)
        self.assertIn("close_fds=True", source)
        self.assertNotIn("argparse", source)
        self.assertNotIn("socket.", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("medscale.", source)
        self.assertNotIn("powershell", source.lower())
        self.assertNotIn("firewall", source.lower().split("def _win32")[1])
        self.assertEqual(
            qa.SUCCESS, "WINDOWS_D2_SOURCE_ONLY_JOB_OBJECT_PARENT_AND_CHILD_KILLED_ON_CLOSE_PASS"
        )


if __name__ == "__main__":
    unittest.main()
