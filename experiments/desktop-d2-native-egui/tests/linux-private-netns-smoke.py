#!/usr/bin/env python3
"""Real Linux native D2 private-netns smoke (not a release/PHI qualification).

Run ONLY under linux-private-netns-smoke.sh. It refuses to attempt any socket
operation unless the host and guest namespaces differ, the guest has exactly
one DOWN loopback interface, and both IPv4/IPv6 route tables are empty.
"""

import argparse
import errno
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

DENIED_ERRNOS = {
    errno.ENETUNREACH,
    errno.EHOSTUNREACH,
    errno.ENETDOWN,
    errno.EADDRNOTAVAIL,
    errno.EAFNOSUPPORT,
}
WINDOW_TITLE = "MedOrigin Native Rust"


def run(argv, timeout=10):
    proc = subprocess.run(
        argv,
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError("OS_PROBE_COMMAND_FAILED")
    return proc.stdout.strip()


def network_preconditions(host_netns):
    current = os.readlink("/proc/self/ns/net")  # noqa: PTH115
    if not re.fullmatch(r"net:\[\d+\]", host_netns):
        raise RuntimeError("MISSING_PINNED_HOST_NAMESPACE")
    if current == host_netns:
        raise RuntimeError("NOT_IN_PRIVATE_NETWORK_NAMESPACE")
    links = run(["ip", "-o", "link", "show"]).splitlines()
    if len(links) != 1 or not re.match(r"^\d+: lo: ", links[0]):
        raise RuntimeError("NONLOOPBACK_NETWORK_INTERFACE_PRESENT")
    match = re.search(r"<([^>]*)>", links[0])
    if not match or "UP" in match.group(1).split(","):
        raise RuntimeError("LOOPBACK_INTERFACE_UP")
    for family in ("-4", "-6"):
        if run(["ip", family, "route", "show", "table", "all"]):
            raise RuntimeError("UNEXPECTED_NETWORK_ROUTE")
    return current


def host_windows_broker_preconditions():
    """Fail closed when WSL may launch a Windows process outside Linux netns.

    Merely removing IPv4/IPv6 routes cannot contain WSLInterop PE execution.
    Do not try to mutate global WSL configuration or assert that masking one
    binfmt mount proves all Windows host escape paths are blocked.
    """
    kernel_release = os.uname().release.lower()
    if (
        "microsoft" in kernel_release
        or os.environ.get("WSL_INTEROP")
        or Path("/proc/sys/fs/binfmt_misc/WSLInterop").exists()
    ):
        raise RuntimeError("WSL_WINDOWS_PROCESS_INTEROP_UNCONFINED")


def negative_controls():
    attempts = [
        ("tcp_ipv4", socket.AF_INET, socket.SOCK_STREAM, ("192.0.2.7", 9)),
        ("dns_udp_ipv4", socket.AF_INET, socket.SOCK_DGRAM, ("192.0.2.7", 53)),
        ("tcp_ipv6", socket.AF_INET6, socket.SOCK_STREAM, ("2001:db8::7", 9)),
        ("dns_udp_ipv6", socket.AF_INET6, socket.SOCK_DGRAM, ("2001:db8::7", 53)),
    ]
    observed = []
    for label, family, socktype, destination in attempts:
        try:
            with socket.socket(family, socktype) as connection:
                connection.settimeout(1.0)
                if socktype == socket.SOCK_STREAM:
                    connection.connect(destination)
                else:
                    connection.sendto(b"synthetic-no-phi", destination)
        except OSError as error:
            if error.errno not in DENIED_ERRNOS:
                raise RuntimeError(f"UNEXPECTED_SOCKET_RESULT:{label}:{error.errno}") from error
            observed.append({"probe": label, "denied_errno": error.errno})
        else:
            raise RuntimeError(f"UNEXPECTED_SOCKET_SUCCESS:{label}")
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--host-netns", required=True)
    args = parser.parse_args()

    record = {
        "schema": "medorigin-native-linux-network-namespace-smoke-v1",
        "decision": "NO_GO",
        "release_authorized": False,
        "os_enforced_cross_platform_offline_proven": False,
        "clinical_data_used": False,
    }
    app = None
    try:
        if os.environ.get("MEDORIGIN_D2_PRIVATE_NETNS_EXPERIMENT") != "1":
            raise RuntimeError("EXPLICIT_EXPERIMENT_OPT_IN_MISSING")
        guest_ns = network_preconditions(args.host_netns)
        # Windows PE execution via WSLInterop escapes the Linux network namespace.
        # This gate runs BEFORE any socket probe or native application launch.
        host_windows_broker_preconditions()
        record["host_netns"] = args.host_netns
        record["guest_netns"] = guest_ns
        binary = Path(args.binary).resolve(strict=True)
        if binary.name != "medorigin-desktop-d2-native-egui":
            raise RuntimeError("WRONG_NATIVE_EXECUTABLE_NAME")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", args.sha256):
            raise RuntimeError("INVALID_PINNED_BINARY_SHA")
        with binary.open("rb") as data:
            if data.read(4) != b"\x7fELF":
                raise RuntimeError("NOT_A_LINUX_ELF")
            data.seek(0)
            digest = hashlib.file_digest(data, "sha256").hexdigest()
        if digest.lower() != args.sha256.lower():
            raise RuntimeError("BINARY_SHA256_MISMATCH")
        record["binary_sha256"] = digest
        record["negative_controls"] = negative_controls()

        # Launch actual native Linux ELF, with no HTTP/remote/EHR/PHI inputs.
        # Its X server and D-Bus session were also started inside this namespace.
        env = dict(os.environ)
        env.pop("WAYLAND_DISPLAY", None)
        env.pop("WAYLAND_SOCKET", None)
        env["WINIT_UNIX_BACKEND"] = "x11"
        env["XDG_SESSION_TYPE"] = "x11"
        app = subprocess.Popen(
            [str(binary)],
            cwd=str(binary.parent),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        window_found = False
        deadline = time.monotonic() + 9
        while time.monotonic() < deadline:
            if app.poll() is not None:
                raise RuntimeError("NATIVE_APP_EXITED_BEFORE_GUI_ACCEPTANCE")
            windows = run(["xwininfo", "-root", "-tree"], timeout=5)
            if WINDOW_TITLE in windows:
                window_found = True
                break
            time.sleep(0.35)
        if not window_found:
            raise RuntimeError("NATIVE_X11_WINDOW_NOT_FOUND")
        # Repeat independent TCP/UDP denial probes *while* the real native
        # GUI is alive, not just before its startup.
        record["negative_controls_while_app_running"] = negative_controls()
        time.sleep(1)
        if app.poll() is not None:
            raise RuntimeError("NATIVE_APP_EXITED_AFTER_WINDOW")
        if network_preconditions(args.host_netns) != guest_ns:
            raise RuntimeError("NETWORK_NAMESPACE_CHANGED_DURING_APP")
        record["native_x11_window_seen"] = True
        record["app_stayed_running"] = True
        record["decision"] = "LINUX_NETNS_NEGATIVE_CONTROL_PASS_NOT_RELEASE"
        return_code = 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        record["reason"] = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        return_code = 2
    finally:
        if app is not None:
            try:
                if app.poll() is None:
                    app.terminate()
                app.wait(timeout=5)
                record["owned_app_process_stopped"] = True
            except (OSError, subprocess.TimeoutExpired):
                try:
                    app.kill()
                    app.wait(timeout=5)
                    record["owned_app_process_stopped"] = True
                except (OSError, subprocess.TimeoutExpired):
                    record["owned_app_process_stopped"] = False
                    record["decision"] = "NO_GO"
                    record["reason"] = "FAILED_PROCESS_CLEANUP"
                    return_code = 2
        print(json.dumps(record, sort_keys=True, separators=(",", ":")), flush=True)
    return return_code


if __name__ == "__main__":
    sys.exit(main())
