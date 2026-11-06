"""Real Windows non-elevated socket observer smoke/negative tests.

These tests exercise the source script on a disposable sleeping PowerShell
process. They DO NOT test MedOrigin's actual binary or qualify offline release.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("windows-network-socket-observation.ps1")
WINDOWS = sys.platform == "win32"


def run_probe(pid, sha, exe_name, samples=1):
    process = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-RootPid",
            str(pid),
            "-ExpectedSha256",
            sha,
            "-ExpectedExecutableName",
            exe_name,
            "-Samples",
            str(samples),
            "-IntervalMs",
            "100",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        payload = json.loads(process.stdout.strip())
    except json.JSONDecodeError as exc:
        raise AssertionError(f"observer did not return valid JSON: {process.stderr[:300]}") from exc
    return process.returncode, payload


@unittest.skipUnless(WINDOWS, "actual Windows PowerShell host required")
class TestWindowsObservation(unittest.TestCase):
    def test_nonexistent_pid_rejected(self):
        code, packet = run_probe(2147483647, "0" * 64, "medorigin-desktop-d2-native-egui.exe")
        self.assertNotEqual(code, 0)
        self.assertEqual(packet["reason"], "ROOT_MISSING_OR_AMBIGUOUS")
        self.assertEqual(packet["decision"], "NO_GO")
        self.assertFalse(packet["release_authorized"])

    def test_wrong_digest_refused_before_sampling(self):
        executable = shutil.which("powershell.exe")
        self.assertIsNotNone(executable)
        child = subprocess.Popen(
            [executable, "-NoProfile", "-Command", "Start-Sleep -Seconds 18"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            code, packet = run_probe(child.pid, "0" * 64, Path(executable).name)
            self.assertNotEqual(code, 0)
            self.assertEqual(packet["reason"], "EXECUTABLE_DIGEST_MISMATCH")
            self.assertEqual(packet["observations"], [])
        finally:
            child.terminate()
            child.wait(timeout=10)

    def test_exact_hash_non_network_control_still_no_go(self):
        executable = shutil.which("powershell.exe")
        self.assertIsNotNone(executable)
        with Path(executable).open("rb") as binary:
            digest = hashlib.file_digest(binary, "sha256").hexdigest()
        child = subprocess.Popen(
            [executable, "-NoProfile", "-Command", "Start-Sleep -Seconds 18"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            code, packet = run_probe(child.pid, digest, Path(executable).name, samples=2)
            self.assertEqual(code, 3)
            self.assertEqual(packet["decision"], "NO_GO")
            self.assertEqual(
                packet["reason"], "NO_SOCKET_OBSERVED_BUT_PACKET_AND_DNS_EGRESS_UNVERIFIED"
            )
            self.assertEqual(len(packet["observations"]), 2)
            self.assertFalse(packet["os_packet_enforcement_proven"])
            self.assertFalse(packet["dns_and_udp_egress_covered"])
            self.assertFalse(packet["release_authorized"])
        finally:
            child.terminate()
            child.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
