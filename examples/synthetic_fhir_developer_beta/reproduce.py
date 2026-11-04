"""Reproducible local synthetic FHIR check of an *installed* medscale CLI.

Developer-preview evidence only; not HL7 conformance or clinical validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
GOOD = HERE / "synthetic_structure_definition.json"
BAD = HERE / "malformed.json"
VERSION = "medscale 0.3.0"
TIMESTAMP = "2026-10-24T00:00:00Z"


def exact_json_contract(actual: object, expected: object) -> bool:
    """Match both value and JSON type; numerics must not masquerade as booleans."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            exact_json_contract(actual[key], value) for key, value in expected.items()
        )
    return actual == expected


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate keys at every depth rather than letting the final key win."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key in installed synthetic CLI output")
        result[key] = value
    return result


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def call(cli: Path, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(cli), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=45,
        check=False,
    )


def run_one(cli: Path, directory: Path, label: str) -> dict[str, Any]:
    version = call(cli, ["--version"], directory)
    if version.returncode or version.stdout.strip() != VERSION:
        raise ValueError(f"{label}: expected installed {VERSION}")
    output = directory / ("reports_" + label)
    validated = call(
        cli,
        ["fhir", "validate", str(GOOD), "--created-at", TIMESTAMP, "--output-dir", str(output)],
        directory,
    )
    if validated.returncode:
        raise ValueError(f"{label}: FHIR command refused or was not validated")
    reports = list(output.rglob("report.json"))
    if len(reports) != 1:
        raise ValueError(f"{label}: expected one report, got {len(reports)}")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    if report.get("status") != "valid":
        raise ValueError(f"{label}: local structural check returned non-valid")
    expected = json.loads(GOOD.read_text(encoding="utf-8"))
    for option in (["fhir", "validate"], ["fhir"]):
        result = call(cli, [*option, str(GOOD), "--summary-only"], directory)
        if result.returncode or json.loads(result.stdout) != expected:
            raise ValueError(f"{label}: documented/legacy command mismatch")
    rejected = call(cli, ["fhir", "validate", str(BAD), "--summary-only"], directory)
    if rejected.returncode != 1 or len(list(output.rglob("report.json"))) != 1:
        raise ValueError(f"{label}: malformed input not safely rejected")
    return {
        "label": label,
        "installed_version": VERSION,
        "fixture_sha256": digest(GOOD),
        "report_sha256": digest(reports[0]),
        "report_path": reports[0].relative_to(directory).as_posix(),
        "structural_status": report["status"],
        "valid_exit": validated.returncode,
        "malformed_exit": rejected.returncode,
    }


def verify_workspace_shell(interpreter: Path, directory: Path) -> dict[str, object]:
    """Admit only the installed Workspace's non-object synthetic shell status."""
    metadata = call(
        interpreter,
        ["-I", "-c", "import importlib.metadata as m; print(m.version('medscale-workspace'))"],
        directory,
    )
    if metadata.returncode != 0 or metadata.stdout.strip() != "0.1.0.dev1":
        raise ValueError("installed Workspace distribution must be medscale-workspace 0.1.0.dev1")
    shell = call(interpreter, ["-I", "-m", "medscale_workspace"], directory)
    if shell.returncode != 0 or len(shell.stdout) > 2048:
        raise ValueError("synthetic Workspace shell failed or returned oversized output")
    try:
        payload = json.loads(shell.stdout, object_pairs_hook=unique_json_object)
    except json.JSONDecodeError as exc:
        raise ValueError("Workspace shell did not return valid JSON") from exc
    allowed = {
        "application": "medscale-workspace",
        "data_class": "SYNTHETIC",
        "mode": "offline-shell",
        "ready": True,
    }
    if not exact_json_contract(payload, allowed):
        # Never include untrusted payload or stderr in a failure message.
        raise ValueError("Workspace shell status is not the safe synthetic-only contract")
    return {
        "application": allowed["application"],
        "version": "0.1.0.dev1",
        "data_class": allowed["data_class"],
        "mode": allowed["mode"],
        "ready": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--core-provenance-only",
        action="store_true",
        help=(
            "Explicit Core-only negative-truth rehearsal; checks installed CLI "
            "not_validated/exit2 and DOES NOT run the legacy false-valid preview."
        ),
    )
    parser.add_argument("--cli", required=True, type=Path, help="Installed medscale executable")
    parser.add_argument(
        "--workspace-python",
        type=Path,
        help="Optional Python from a separately installed synthetic Workspace environment",
    )
    parser.add_argument(
        "--alt-cli", type=Path, help="Optional installed medscale on a second Python runtime"
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="New, nonexistent evidence directory"
    )
    args = parser.parse_args(argv)
    clis = [args.cli.resolve()]
    if args.alt_cli is not None:
        clis.append(args.alt_cli.resolve())
    for cli in clis:
        if not cli.is_file():
            parser.error("installed CLI not found")
    workspace_python = args.workspace_python.resolve() if args.workspace_python else None
    if workspace_python is not None and not workspace_python.is_file():
        parser.error("installed Workspace Python interpreter not found")
    for fixture in (GOOD, BAD):
        if not fixture.is_file():
            parser.error(f"missing synthetic fixture: {fixture}")
    output = args.out.resolve()
    if output.exists():
        parser.error("refusing to overwrite existing evidence directory")
    if args.core_provenance_only:
        if workspace_python is not None:
            print("MEDORIGIN_CORE_FHIR_PROVENANCE_ONLY_BLOCKED", file=sys.stderr)
            return 2
        try:
            helper = runpy.run_path(str(HERE / "core_only.py"))
            safe = helper["qualified_receipt"](clis)
            helper["commit_new_receipt"](output, safe)
        except (OSError, RuntimeError, TypeError, ValueError, KeyError):
            # The source-gated installed CLI can include paths or patient-like
            # text in failures; do not forward any exception or raw output.
            print("MEDORIGIN_CORE_FHIR_PROVENANCE_ONLY_BLOCKED", file=sys.stderr)
            return 2
        print("MEDORIGIN_CORE_FHIR_PROVENANCE_ONLY_PASS")
        print("fhir_conformance_validated=false")
        print("prepublication_rehearsal_qualified=false")
        return 0
    output.mkdir(parents=True)
    try:
        runs = [run_one(cli, output, f"run_{i + 1}") for i, cli in enumerate(clis)]
        if len(runs) == 2 and runs[0]["report_sha256"] != runs[1]["report_sha256"]:
            raise ValueError("cross-runtime report hashes differ")
        receipt = {
            "schema": "medorigin-local-synthetic-fhir-example/v1",
            "scope": "synthetic structural validation, not full HL7 conformance",
            "publication_authorized": False,
            "clinical_authorized": False,
            "independent_review_completed": False,
            "runs": runs,
        }
        if workspace_python is not None:
            receipt["workspace"] = verify_workspace_shell(workspace_python, output)
        record = output / "evidence.json"
        record.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        preview = subprocess.run(
            [
                sys.executable,
                str(HERE / "preview.py"),
                "--receipt",
                str(record),
                "--out",
                str(output / "preview.html"),
            ],
            cwd=output,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if preview.returncode != 0:
            raise ValueError("legacy static preview did not qualify")
        print("MEDORIGIN_SYNTHETIC_FHIR_DEMO_PASS")
        print(f"report_sha256={runs[0]['report_sha256']}")
        print(f"receipt_sha256={digest(record)}")
        return 0
    except (
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
    ):
        print("MEDORIGIN_SYNTHETIC_FHIR_DEMO_FAIL: legacy_rehearsal_not_qualified", file=sys.stderr)
        print("Any partial output is nonqualifying; use a new --out directory.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
