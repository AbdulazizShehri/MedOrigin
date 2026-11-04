#!/usr/bin/env python3
"""Real installed-Wheel Python Core -> Rust D2 QA, macOS Apple Silicon only.

Fixed two fictional FHIR cases, no arbitrary clinical/user inputs or GUI launch.
A SOURCE ATTESTATION harness and deprecation-limited local sandbox proof;
NOT an approved installed Core product launcher or release security boundary.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import zipfile

import qualify_sandboxed_synthetic_core as base

WHEEL_FILENAME = "medscale-0.3.0-py3-none-any.whl"
WHEEL_SHA256 = "4f3a66c9657c8040832970fdffcaa0d2bf15c74c79ae76b17566fe573c9536c2"
WHEEL_PACKAGE_FILES = 250
WHEEL_MEMBERS = 255
MAX_WHEEL_SIZE = 1_500_000
MAX_WHEEL_UNCOMPRESSED = 20_000_000
MAX_WHEEL_ENTRY = 3_000_000
INSTALLED_CODE = (
    "import sys;"
    "sys.path.insert(0,sys.argv[1]);"
    "from medscale.cli.fhir import main;"
    "raise SystemExit(main(sys.argv[2:]))"
)
ISOLATED_SOURCE_PROBE = (
    "import sys,pathlib;"
    "sys.path.insert(0,str(pathlib.Path(sys.argv[1]).resolve().parent.parent));"
    "import medscale;"
    "assert pathlib.Path(medscale.__file__).resolve()==pathlib.Path(sys.argv[1]).resolve();"
    "assert all('core-src' not in p for p in sys.path);"
    "print('INSTALLED_CORE_PACKAGED_SOURCE_ONLY')"
)
SUCCESS = "D2_MAC_INSTALLED_WHEEL_SANDBOXED_CORE_TO_RUST_2_OF_2_PASS_NOT_RELEASE"


def _digest_record(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii").rstrip("=")


def parse_record(
    record: bytes, *, allow_venv_script: bool = False
) -> dict[str, tuple[str, int] | None]:
    try:
        lines = list(csv.reader(io.StringIO(record.decode("utf-8"))))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("wheel_record_encoding_invalid") from exc
    parsed: dict[str, tuple[str, int] | None] = {}
    for row in lines:
        if len(row) != 3 or not row[0] or row[0] in parsed:
            raise ValueError("wheel_record_duplicate_or_malformed")
        name, sha, size = row
        permitted_venv_launcher = allow_venv_script and name == "../../../bin/medscale"
        if not permitted_venv_launcher and (
            name.startswith("/") or "\\" in name
            or any(part in (".", "..") for part in name.split("/"))
        ):
            raise ValueError("wheel_record_path_traversal")
        if sha == "" and size == "":
            if not name.endswith(".dist-info/RECORD"):
                raise ValueError("wheel_record_missing_file_digest")
            parsed[name] = None
            continue
        if not sha.startswith("sha256=") or not re.fullmatch(r"[a-zA-Z0-9_-]{43}", sha[7:]):
            raise ValueError("wheel_record_digest_invalid")
        if not size.isdecimal() or int(size) > MAX_WHEEL_ENTRY:
            raise ValueError("wheel_record_size_invalid")
        parsed[name] = (sha[7:], int(size))
    return parsed


def attest_offline_wheel_and_install(
    core_source: Path, wheel_path: Path, venv_root: Path
) -> Path:
    base.source_commit(core_source)
    wheel = wheel_path.absolute()
    if wheel.is_symlink() or not wheel.is_file() or wheel.name != WHEEL_FILENAME:
        raise ValueError("installed_core_wheel_filename_or_file_refused")
    if wheel.stat().st_size > MAX_WHEEL_SIZE or base.sha256(wheel.read_bytes()) != WHEEL_SHA256:
        raise ValueError("installed_core_wheel_changed_or_unapproved")
    venv = venv_root.resolve(strict=True)
    if (venv_root.is_symlink() or not venv.is_dir() or
            (os.name == "posix" and venv.stat().st_mode & 0o077)):
        raise ValueError("installed_core_venv_not_private")
    if not (venv / "pyvenv.cfg").is_file():
        raise ValueError("installed_core_venv_metadata_missing")
    site = venv / "lib/python3.11/site-packages"
    if site.is_symlink() or not site.is_dir():
        raise ValueError("installed_core_site_path_not_directory")
    direct = {e.name for e in site.iterdir()}
    if direct != {
        "medscale", "medscale-0.3.0.dist-info", "_virtualenv.pth", "_virtualenv.py"
    }:
        raise ValueError("installed_core_unreviewed_site_package_or_startup_hook")
    # -I -S -B deliberately disables ALL .pth/venv startup hooks, while
    # a single exact verified site-package directory is added in -c.
    package = site / "medscale"
    if package.is_symlink() or not package.is_dir():
        raise ValueError("installed_core_package_not_regular")
    source = core_source.resolve(strict=True)
    with zipfile.ZipFile(wheel) as archive:
        members = archive.infolist()
        names = [info.filename for info in members]
        if len(names) != WHEEL_MEMBERS or len(names) != len(set(names)):
            raise ValueError("installed_core_wheel_members_changed")
        total = 0
        for info in members:
            mode = info.external_attr >> 16
            if info.is_dir() or stat.S_IFMT(mode) == stat.S_IFLNK:
                raise ValueError("installed_core_zip_symlink_or_directory")
            if info.file_size > MAX_WHEEL_ENTRY:
                raise ValueError("installed_core_wheel_member_oversized")
            total += info.file_size
        if total > MAX_WHEEL_UNCOMPRESSED:
            raise ValueError("installed_core_wheel_expansion_refused")
        tracked = subprocess.run(
            ["/usr/bin/git", "-C", str(source), "ls-files", "-z", "--", "src/medscale"],
            capture_output=True, timeout=10, check=True,
        ).stdout
        paths = [Path(s.decode("utf-8")) for s in tracked.split(b"\0") if s]
        if len(paths) != WHEEL_PACKAGE_FILES:
            raise ValueError("installed_core_source_inventory_changed")
        expected = {str(p).removeprefix("src/") for p in paths}
        packaged = {n for n in names if n.startswith("medscale/")}
        if packaged != expected:
            raise ValueError("installed_core_wheel_package_inventory_changed")
        actual = set()
        for root, dirs, files in os.walk(package, followlinks=False):
            for subdir in dirs:
                if (Path(root) / subdir).is_symlink():
                    raise ValueError("installed_core_package_directory_symlink")
            for file in files:
                entry = Path(root) / file
                if not entry.is_file() or entry.is_symlink():
                    raise ValueError("installed_core_package_unreviewed_file_type")
                actual.add("medscale/" + str(entry.relative_to(package)))
        if actual != expected:
            raise ValueError("installed_core_extra_missing_or_bytecode_files")
        for tracked_path in paths:
            relative = str(tracked_path).removeprefix("src/")
            original = source / tracked_path
            installed = site / relative
            if original.is_symlink() or installed.is_symlink():
                raise ValueError("installed_core_source_symlink_refused")
            if not original.is_file() or not installed.is_file():
                raise ValueError("installed_core_source_file_missing")
            if original.read_bytes() != archive.read(relative) or installed.read_bytes() != archive.read(relative):
                raise ValueError("installed_core_wheel_or_installed_source_bytes_changed")
        records = [n for n in names if n.endswith(".dist-info/RECORD")]
        if records != ["medscale-0.3.0.dist-info/RECORD"]:
            raise ValueError("installed_core_wheel_record_missing")
        record = parse_record(archive.read(records[0]))
        if set(record) != set(names):
            raise ValueError("installed_core_wheel_record_inventory_changed")
        for n in names:
            meta = record[n]
            if n == records[0]:
                if meta is not None:
                    raise ValueError("installed_core_record_self_hash_invalid")
            else:
                if meta != (_digest_record(archive.read(n)), len(archive.read(n))):
                    raise ValueError("installed_core_wheel_record_hash_or_size_invalid")
        # Wheel metadata is a real part of installed bytes, not ignored.
        for n in names:
            if n.startswith("medscale-0.3.0.dist-info/") and n != records[0]:
                installed_meta = site / n
                if installed_meta.is_symlink() or not installed_meta.is_file():
                    raise ValueError("installed_core_dist_info_file_refused")
                if installed_meta.read_bytes() != archive.read(n):
                    raise ValueError("installed_core_dist_info_changed")
    installed_record = site / "medscale-0.3.0.dist-info/RECORD"
    if installed_record.is_symlink() or not installed_record.is_file():
        raise ValueError("installed_core_record_missing")
    installed_entries = parse_record(installed_record.read_bytes(), allow_venv_script=True)
    for n in expected:
        if installed_entries.get(n) != (
            _digest_record((site / n).read_bytes()), (site / n).stat().st_size
        ):
            raise ValueError("installed_core_record_package_hash_mismatch")
    return site


def qualify(core: Path, wheel: Path, venv: Path, python: Path,
            python_sha: str, rust: Path, rust_sha: str) -> None:
    if sys.platform != "darwin" or platform.machine().lower() != "arm64":
        raise ValueError("macos_arm64_real_sandbox_host_required")
    site = attest_offline_wheel_and_install(core, wheel, venv)
    if python.absolute() != venv.absolute() / "bin/python3.11":
        raise ValueError("unreviewed_virtualenv_interpreter_path")
    python = base.verify_program(python, python_sha, "installed_python")
    rust = base.verify_program(rust, rust_sha, "rust_d2_reader")
    with TemporaryDirectory(prefix="medorigin-d2-installed-core-") as temp:
        work = Path(temp).resolve()
        work.chmod(0o700)
        profile = base.sandbox_profile(work)
        base.prove_restrictive_mac_policy(profile, work, python)
        imported = base.run_sandboxed(profile, [
            str(python), "-I", "-S", "-B", "-c", ISOLATED_SOURCE_PROBE,
            str(site / "medscale/__init__.py"),
        ], work)
        if imported.returncode != 0 or imported.stdout != b"INSTALLED_CORE_PACKAGED_SOURCE_ONLY\n":
            raise ValueError("installed_core_package_import_provenance_refused")
        for label, raw_input in base.expected_inputs(core).items():
            input_file = work / (label + ".json")
            input_file.write_bytes(raw_input)
            output_dir = work / (label + "-output")
            output_dir.mkdir(mode=0o700)
            proc = base.run_sandboxed(profile, [
                str(python), "-I", "-S", "-B", "-c", INSTALLED_CODE,
                str(site), "validate", str(input_file), "--created-at",
                base.TIMESTAMP, "--output-dir", str(output_dir),
            ], work)
            if proc.returncode != 2 or not proc.stdout.endswith(b"\n\n"):
                raise ValueError("installed_core_cli_validation_status_changed")
            report = proc.stdout[:-1]
            base.check_core_report(report, base.PINNED_CASES[label][0])
            artifacts = list(output_dir.rglob("report.json"))
            if len(artifacts) != 1 or artifacts[0].is_symlink() or artifacts[0].read_bytes() != report:
                raise ValueError("installed_core_report_persistence_or_provenance_mismatch")
            accepted = base.run_sandboxed(profile, [str(rust)], work, stdin=report)
            expected = (
                f"D2_CORE_SYNTHETIC_ONLY case={base.PINNED_CASES[label][1]} "
                f"status=not_validated report_sha256={base.sha256(report)} "
                "FHIR_R4_NOT_VALIDATED\n"
            ).encode()
            if accepted.returncode != 0 or accepted.stdout != expected:
                raise ValueError("installed_core_d2_rust_reader_refused")
            forged = json.loads(report)
            forged["status"] = "valid"
            rejected = base.run_sandboxed(
                profile, [str(rust)], work, stdin=base.canonical(forged)
            )
            if rejected.returncode == 0:
                raise ValueError("installed_core_d2_forged_valid_claim_accepted")
            print("INSTALLED_WHEEL_TO_D2_SANDBOXED_FICTIONAL_CASE_PASS " + label)
        base.verify_program(python, python_sha, "installed_python")
        base.verify_program(rust, rust_sha, "rust_d2_reader")
        attest_offline_wheel_and_install(core, wheel, venv)
    print(SUCCESS)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--core-source", type=Path, required=True)
    p.add_argument("--wheel", type=Path, required=True)
    p.add_argument("--venv", type=Path, required=True)
    p.add_argument("--venv-python", type=Path, required=True)
    p.add_argument("--python-sha256", required=True)
    p.add_argument("--d2-reader", type=Path, required=True)
    p.add_argument("--d2-reader-sha256", required=True)
    a = p.parse_args()
    try:
        qualify(
            a.core_source, a.wheel, a.venv, a.venv_python,
            a.python_sha256, a.d2_reader, a.d2_reader_sha256,
        )
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print("INSTALLED_CORE_TO_D2_SANDBOX_NO_GO:" + str(error), file=sys.stderr)
        sys.exit(2)
