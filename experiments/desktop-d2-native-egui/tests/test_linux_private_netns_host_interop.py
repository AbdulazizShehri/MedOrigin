#!/usr/bin/env python3
"""Source-only regression: WSL Windows-process interop must fail closed.

No network, GUI, operating system policy changes or real Windows executable
is launched by these tests.
"""

import contextlib
import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).with_name("linux-private-netns-smoke.py")
SPEC = importlib.util.spec_from_file_location("medorigin_linux_netns_probe", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("probe source not readable")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class TestWslInteropFailClosed(unittest.TestCase):
    def test_microsoft_kernel_refuses(self):
        with (
            mock.patch.object(
                PROBE.os,
                "uname",
                create=True,
                return_value=types.SimpleNamespace(release="6.18.33.1-microsoft-standard-WSL2"),
            ),
            self.assertRaisesRegex(RuntimeError, "WSL_WINDOWS_PROCESS_INTEROP_UNCONFINED"),
        ):
            PROBE.host_windows_broker_preconditions()

    def test_interop_environment_refuses_on_other_kernel(self):
        with (
            mock.patch.object(
                PROBE.os,
                "uname",
                create=True,
                return_value=types.SimpleNamespace(release="6.18-generic"),
            ),
            mock.patch.dict(PROBE.os.environ, {"WSL_INTEROP": "/run/WSL/placeholder"}, clear=False),
            self.assertRaisesRegex(RuntimeError, "WSL_WINDOWS_PROCESS_INTEROP_UNCONFINED"),
        ):
            PROBE.host_windows_broker_preconditions()

    def test_binfmt_wsl_registration_refuses_on_other_kernel(self):
        with (
            mock.patch.object(
                PROBE.os,
                "uname",
                create=True,
                return_value=types.SimpleNamespace(release="6.18-generic"),
            ),
            mock.patch.dict(PROBE.os.environ, {}, clear=True),
            mock.patch.object(PROBE.Path, "exists", return_value=True),
            self.assertRaisesRegex(RuntimeError, "WSL_WINDOWS_PROCESS_INTEROP_UNCONFINED"),
        ):
            PROBE.host_windows_broker_preconditions()

    def test_ordinary_linux_without_windows_broker_can_continue(self):
        with (
            mock.patch.object(
                PROBE.os,
                "uname",
                create=True,
                return_value=types.SimpleNamespace(release="6.18-generic"),
            ),
            mock.patch.dict(PROBE.os.environ, {}, clear=True),
            mock.patch.object(PROBE.Path, "exists", return_value=False),
        ):
            self.assertIsNone(PROBE.host_windows_broker_preconditions())

    def test_main_rejects_wsl_before_socket_or_app(self):
        with (
            mock.patch.object(PROBE, "network_preconditions", return_value="net:[12345]"),
            mock.patch.object(
                PROBE.os,
                "uname",
                create=True,
                return_value=types.SimpleNamespace(release="6.18.33.1-microsoft-standard-WSL2"),
            ),
            mock.patch.dict(
                PROBE.os.environ, {"MEDORIGIN_D2_PRIVATE_NETNS_EXPERIMENT": "1"}, clear=False
            ),
            mock.patch.object(
                PROBE, "negative_controls", side_effect=AssertionError("socket probe happened")
            ),
            mock.patch.object(
                PROBE.subprocess, "Popen", side_effect=AssertionError("app launched")
            ),
            mock.patch.object(
                sys,
                "argv",
                [
                    "probe",
                    "--binary",
                    "/not/a/binary",
                    "--sha256",
                    "0" * 64,
                    "--host-netns",
                    "net:[2]",
                ],
            ),
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = PROBE.main()
        self.assertEqual(exit_code, 2)
        packet = json.loads(output.getvalue())
        self.assertEqual(packet["decision"], "NO_GO")
        self.assertEqual(packet["reason"], "WSL_WINDOWS_PROCESS_INTEROP_UNCONFINED")
        self.assertFalse(packet["release_authorized"])
        self.assertNotIn("negative_controls", packet)
        self.assertNotIn("binary_sha256", packet)
        self.assertNotIn("native_x11_window_seen", packet)


if __name__ == "__main__":
    unittest.main()
