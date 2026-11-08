#!/usr/bin/env python3
"""Mac-only Core→D2 real CLI acceptance, restricted to two fictional fixtures.

This is a developer QA harness, never an embedded product Core launcher,
confidential patient-data workflow, installed Wheel verifier, or release gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PINNED_CORE_SHA = "ad0c62b4366789f5c7e41fc601bb6d0f9d640873"
PINNED_CASES = {
    "known": (
        "d1f1167a352bbce42e851336d33d0e292902463c1656860bd7cce3ec67598faf",
        "known-structure-definition",
    ),
    "unknown": (
        "493bdfef2855ab2bb997d56ee7e4afca4b5ae0c4cc75eef39461b00517ef177c",
        "unknown-fictional-negative",
    ),
}
TIMESTAMP = "2026-10-24T00:00:00Z"
WARNING = (
    "FHIR R4 schema, terminology, and profile validation were not performed; "
    "this local report records deterministic provenance only."
)
CORE_CODE = (
    "import sys;"
    "sys.path.insert(0,sys.argv[1]);"
    "from medscale.cli.fhir import main;"
    "raise SystemExit(main(sys.argv[2:]))"
)
NETWORK_CANARY = (
    "import errno,socket,sys;s=socket.socket();s.connect(('127.0.0.1',int(sys.argv[1])))"
)
READONLY_STATUS = "SYNTHETIC_CORE_SOURCE_TO_D2_SANDBOXED_QA_PASS_NOT_RELEASE"
MAX_OUTPUT = 4096


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(payload: dict) -> bytes:
    return (
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate_core_report_key")
        obj[key] = value
    return obj


def check_core_report(raw: bytes, expected_input_hash: str) -> None:
    if not raw or len(raw) > MAX_OUTPUT:
        raise ValueError("core_report_output_size_refused")
    parsed = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(parsed, dict) or raw != canonical(parsed):
        raise ValueError("noncanonical_core_report")
    if set(parsed) != {
        "created_at",
        "errors",
        "format_version",
        "input_hash",
        "report_id",
        "status",
        "validator_name",
        "validator_version",
        "warnings",
    }:
        raise ValueError("core_report_fields_changed")
    if (
        parsed["created_at"] != TIMESTAMP
        or parsed["errors"] != []
        or parsed["format_version"] != "fhirkit-validation-report/v1"
        or parsed["input_hash"] != expected_input_hash
        or parsed["report_id"] != ""
        or parsed["status"] != "not_validated"
        or parsed["validator_name"] != "medscale-fhirkit-local"
        or parsed["validator_version"] != "0.1.0"
        or parsed["warnings"] != [WARNING]
    ):
        raise ValueError("core_report_validation_claim_or_provenance_changed")


def source_commit(core: Path) -> str:
    if core.is_symlink() or not core.is_dir():
        raise ValueError("core_checkout_not_directory")
    commit = subprocess.run(
        ["/usr/bin/git", "-C", str(core), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=8,
        check=True,
    ).stdout.strip()
    if commit != PINNED_CORE_SHA:
        raise ValueError("core_source_commit_not_pinned")
    dirty = subprocess.run(
        ["/usr/bin/git", "-C", str(core), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        timeout=8,
        check=True,
    )
    if dirty.stdout:
        raise ValueError("core_tracked_or_untracked_files_modified")
    # Git deliberately hides ignored .pyc/__pycache__, which can still replace
    # imported Python code. Inspect real filesystem entries, not git status alone.
    source_paths = ("src/medscale", "examples/synthetic_fhir_developer_beta")
    listed = subprocess.run(
        ["/usr/bin/git", "-C", str(core), "ls-files", "-z", "--", *source_paths],
        capture_output=True,
        timeout=8,
        check=True,
    ).stdout
    approved = {Path(name.decode("utf-8")) for name in listed.split(b"\0") if name}
    actual: set[Path] = set()
    for relative in source_paths:
        directory = core / relative
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError("core_source_directory_invalid")
        for root, dirs, names in os.walk(directory, followlinks=False):
            for subdir in dirs:
                if (Path(root) / subdir).is_symlink():
                    raise ValueError("core_source_symlink_directory_refused")
            for filename in names:
                member = Path(root) / filename
                if member.is_symlink() or not member.is_file():
                    raise ValueError("core_source_nonregular_file_refused")
                actual.add(member.relative_to(core))
    if actual != approved:
        raise ValueError("core_source_unreviewed_or_missing_files")
    return commit


def verify_program(path: Path, expected_sha: str, label: str) -> Path:
    if not re.fullmatch("[a-f0-9]{64}", expected_sha.lower()):
        raise ValueError("invalid_" + label + "_sha256")
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(label + "_not_regular_executable")
    if not os.access(resolved, os.X_OK):
        raise ValueError(label + "_not_executable")
    if sha256(resolved.read_bytes()) != expected_sha.lower():
        raise ValueError(label + "_binary_hash_changed")
    return resolved


def sandbox_profile(work: Path) -> str:
    # macOS Seatbelt local QA only. file-read is broad and this is NOT
    # a proof of PHI confidentiality or descendant/process confinement.
    if not work.is_absolute() or work.is_symlink() or not work.is_dir():
        raise ValueError("sandbox_private_work_directory_missing")
    actual = work.resolve(strict=True)
    if actual.stat().st_mode & 0o077:
        raise ValueError("sandbox_work_directory_permissions_refused")
    quoted = str(actual).replace("\\", "\\\\").replace('"', '\\"')
    return (
        "(version 1) (deny default) (allow process*) (allow file-read*) "
        "(allow sysctl-read) (allow mach-lookup) "
        f'(allow file-write* (subpath "{quoted}"))'
    )


def run_sandboxed(
    profile: str, cmd: list[str], work: Path, *, stdin: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["/usr/bin/sandbox-exec", "-p", profile, *cmd],
        cwd=work,
        input=stdin,
        capture_output=True,
        timeout=20,
        env={
            "HOME": str(work),
            "TMPDIR": str(work),
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        check=False,
    )
    if len(result.stdout) > MAX_OUTPUT or len(result.stderr) > MAX_OUTPUT:
        raise ValueError("sandbox_subprocess_output_over_limit")
    return result


def prove_restrictive_mac_policy(profile: str, work: Path, python: Path) -> None:
    # Real unconfined loopback positive control + sandbox EPERM negative.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(2)
        port = listener.getsockname()[1]
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass
        negative = run_sandboxed(
            profile, [str(python), "-I", "-S", "-B", "-c", NETWORK_CANARY, str(port)], work
        )
        if (
            negative.returncode == 0
            or b"PermissionError: [Errno 1]" not in negative.stderr
            or b"ConnectionRefusedError" in negative.stderr
        ):
            raise ValueError("macos_loopback_os_deny_not_proven")
    # Private sibling owned by this harness: unconfined write succeeds, the
    # same write from confined process must fail, without altering user files.
    sibling = work.parent / (work.name + "-write-control")
    sibling.mkdir(mode=0o700)
    try:
        target = sibling / "probe"
        target.write_bytes(b"synthetic-only")
        target.unlink()
        script = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(b'X')"
        refusal = run_sandboxed(
            profile, [str(python), "-I", "-S", "-B", "-c", script, str(target)], work
        )
        if refusal.returncode == 0 or target.exists():
            raise ValueError("macos_file_write_scope_not_enforced")
    finally:
        if sibling.exists():
            sibling.rmdir()


def expected_inputs(core: Path) -> dict[str, bytes]:
    fixture = core / "examples/synthetic_fhir_developer_beta/synthetic_structure_definition.json"
    if fixture.is_symlink() or not fixture.is_file() or fixture.stat().st_size > 2048:
        raise ValueError("pinned_core_synthetic_fixture_missing")
    known = json.loads(fixture.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    unknown = {"id": "fictional-negative-control", "resourceType": "UnknownFictionalResource"}
    result = {"known": canonical(known), "unknown": canonical(unknown)}
    for label, blob in result.items():
        if sha256(blob.rstrip(b"\n")) != PINNED_CASES[label][0]:
            raise ValueError("source_core_synthetic_fixture_hash_changed")
    return result


def qualify(core: Path, python: Path, python_sha: str, rust: Path, rust_sha: str) -> None:
    if sys.platform != "darwin" or platform.machine().lower() != "arm64":
        raise ValueError("real_apple_silicon_seatbelt_host_required")
    if not Path("/usr/bin/sandbox-exec").is_file():
        raise ValueError("macos_sandbox_policy_unavailable")
    core = core.resolve(strict=True)
    source_commit(core)
    python = verify_program(python, python_sha, "python")
    rust = verify_program(rust, rust_sha, "rust_reader")
    inputs = expected_inputs(core)
    with TemporaryDirectory(prefix="medorigin-d2-sandbox-core-") as tmp:
        work = Path(tmp).resolve()
        work.chmod(0o700)
        profile = sandbox_profile(work)
        prove_restrictive_mac_policy(profile, work, python)
        for label, input_bytes in inputs.items():
            inp = work / (label + ".json")
            inp.write_bytes(input_bytes)
            out = work / (label + "-output")
            out.mkdir(mode=0o700)
            proc = run_sandboxed(
                profile,
                [
                    str(python),
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    CORE_CODE,
                    str(core / "src"),
                    "validate",
                    str(inp),
                    "--created-at",
                    TIMESTAMP,
                    "--output-dir",
                    str(out),
                ],
                work,
            )
            if proc.returncode != 2 or not proc.stdout.endswith(b"\n\n"):
                raise ValueError("core_cli_did_not_refuse_validation_claim")
            raw = proc.stdout[:-1]
            check_core_report(raw, PINNED_CASES[label][0])
            receipts = list(out.rglob("report.json"))
            if (
                len(receipts) != 1
                or receipts[0].is_symlink()
                or not receipts[0].is_file()
                or receipts[0].read_bytes() != raw
            ):
                raise ValueError("core_output_file_report_mismatch")
            accepted = run_sandboxed(profile, [str(rust)], work, stdin=raw)
            expected = (
                f"D2_CORE_SYNTHETIC_ONLY case={PINNED_CASES[label][1]} "
                f"status=not_validated report_sha256={sha256(raw)} "
                "FHIR_R4_NOT_VALIDATED\n"
            ).encode()
            if accepted.returncode != 0 or accepted.stdout != expected:
                raise ValueError("rust_d2_core_report_admission_refused")
            # Deliberately check a forged FHIR-valid receipt is REJECTED by D2.
            tampered = json.loads(raw)
            tampered["status"] = "valid"
            negative = run_sandboxed(profile, [str(rust)], work, stdin=canonical(tampered))
            if negative.returncode == 0:
                raise ValueError("d2_accepted_false_clinical_validation")
            print("CORE_D2_SANDBOXED_FIXED_CASE_PASS " + label)
        verify_program(python, python_sha, "python")
        verify_program(rust, rust_sha, "rust_reader")
    print(READONLY_STATUS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-source", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--python-sha256", required=True)
    parser.add_argument("--d2-reader", type=Path, required=True)
    parser.add_argument("--d2-reader-sha256", required=True)
    args = parser.parse_args()
    try:
        qualify(
            args.core_source,
            args.python,
            args.python_sha256,
            args.d2_reader,
            args.d2_reader_sha256,
        )
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        print("D2_CORE_SANDBOX_QA_NO_GO: " + str(e), file=sys.stderr)
        sys.exit(2)
