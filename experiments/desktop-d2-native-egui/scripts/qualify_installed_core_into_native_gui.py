#!/usr/bin/env python3
"""Actual one-shot installed Core -> source-allowlisted D2 native GUI on Mac.

Only two fixed fictional cases. Never enables PHI, live clinical import,
patient files, D2 subprocess spawning, network access or public signing.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory

import qualify_installed_synthetic_core as installed
import qualify_sandboxed_synthetic_core as base

SUCCESS = "D2_INSTALLED_SANDBOXED_CORE_TO_ACTUAL_NATIVE_GUI_2_OF_2_PASS_NOT_CLINICAL"


def qualify_gui(core: Path, wheel: Path, venv: Path, venv_python: Path,
                python_sha: str, gui: Path, gui_sha: str) -> None:
    if sys.platform != "darwin" or platform.machine().lower() != "arm64":
        raise ValueError("authorized_apple_silicon_native_gui_required")
    site = installed.attest_offline_wheel_and_install(core, wheel, venv)
    if venv_python.absolute() != venv.absolute() / "bin/python3.11":
        raise ValueError("unreviewed_venv_python_entrypoint")
    python = base.verify_program(venv_python, python_sha, "installed_python")
    binary = base.verify_program(gui, gui_sha, "d2_native_gui")
    if binary.name != "medorigin-desktop-d2-native-egui":
        raise ValueError("d2_native_binary_name_unapproved")
    swift = Path("/usr/bin/swift")
    ax_test = (
        Path(__file__).resolve().parent.parent
        / "tests/macos-installed-core-stdin-live-ax-qualification.swift"
    )
    if not swift.is_file() or ax_test.is_symlink() or not ax_test.is_file():
        raise ValueError("real_mac_native_ax_harness_unavailable")
    with TemporaryDirectory(prefix="medorigin-installed-core-native-ui-") as tmp:
        work = Path(tmp).resolve()
        work.chmod(0o700)
        profile = base.sandbox_profile(work)
        base.prove_restrictive_mac_policy(profile, work, python)
        for label, source_input in base.expected_inputs(core).items():
            inp = work / (label + ".json")
            inp.write_bytes(source_input)
            output_dir = work / (label + "-output")
            output_dir.mkdir(mode=0o700)
            real_core = base.run_sandboxed(profile, [
                str(python), "-I", "-S", "-B", "-c", installed.INSTALLED_CODE,
                str(site), "validate", str(inp), "--created-at", base.TIMESTAMP,
                "--output-dir", str(output_dir),
            ], work)
            if real_core.returncode != 2 or not real_core.stdout.endswith(b"\n\n"):
                raise ValueError("installed_core_cli_not_provenance_only")
            report = real_core.stdout[:-1]
            base.check_core_report(report, base.PINNED_CASES[label][0])
            source_files = list(output_dir.rglob("report.json"))
            if (len(source_files) != 1 or source_files[0].is_symlink()
                    or source_files[0].read_bytes() != report):
                raise ValueError("installed_core_report_persistence_mismatch")

            # The GUI is deliberately NOT allowed to spawn a Python worker.
            # An already-source-qualified local QA host supplies one exact
            # fictional report via stdin; the GUI authenticates only its
            # canonical bytes, never the origin/freshness of the transport.
            process = subprocess.Popen(
                [str(binary), "--synthetic-core-stdin"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                cwd=work,
                env={"PATH": "/usr/bin:/bin", "HOME": str(work)},
            )
            try:
                if process.stdin is None:
                    raise ValueError("native_gui_stdin_pipe_unavailable")
                process.stdin.write(report)
                process.stdin.close()
                if process.poll() is not None:
                    raise ValueError("native_gui_exited_before_ax_qualification")
                receipt_hash = base.sha256(report)
                observed = subprocess.run(
                    [str(swift), str(ax_test), str(process.pid), receipt_hash],
                    capture_output=True, timeout=35, check=False,
                )
                expected = (
                    "MACOS_INSTALLED_CORE_STDIN_GUI_AX_EXACT_SHA_NOT_VALIDATED_PASS "
                    + receipt_hash + "\n"
                ).encode()
                if observed.returncode != 0 or observed.stdout != expected:
                    raise ValueError("real_native_gui_source_report_ax_refused")
                if process.poll() is not None:
                    raise ValueError("native_gui_terminated_before_qa_complete")
                print("INSTALLED_WHEEL_SANDBOXED_CORE_REAL_NATIVE_GUI_CASE_PASS " + label)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=4)
                if process.stderr:
                    process.stderr.close()
        base.verify_program(python, python_sha, "installed_python")
        base.verify_program(binary, gui_sha, "d2_native_gui")
        installed.attest_offline_wheel_and_install(core, wheel, venv)
    print(SUCCESS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-source", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument("--venv-python", type=Path, required=True)
    parser.add_argument("--python-sha256", required=True)
    parser.add_argument("--d2-gui", type=Path, required=True)
    parser.add_argument("--d2-gui-sha256", required=True)
    args = parser.parse_args()
    try:
        qualify_gui(
            args.core_source, args.wheel, args.venv, args.venv_python,
            args.python_sha256, args.d2_gui, args.d2_gui_sha256,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("D2_REAL_INSTALLED_CORE_NATIVE_GUI_NO_GO:" + str(error), file=sys.stderr)
        sys.exit(2)
