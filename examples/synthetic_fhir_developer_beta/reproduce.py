"""Reproducible local synthetic FHIR check of an *installed* medscale CLI.

Developer-preview evidence only; not HL7 conformance or clinical validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
GOOD = HERE / "synthetic_structure_definition.json"
BAD = HERE / "malformed.json"
VERSION = "medscale 0.3.0"
TIMESTAMP = "2026-10-24T00:00:00Z"


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
        raise ValueError(f"{label}: FHIR command failed: {validated.stderr[:250]}")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True, type=Path, help="Installed medscale executable")
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
            parser.error(f"installed CLI not found: {cli}")
    for fixture in (GOOD, BAD):
        if not fixture.is_file():
            parser.error(f"missing synthetic fixture: {fixture}")
    output = args.out.resolve()
    if output.exists():
        parser.error(f"refusing to overwrite existing evidence directory: {output}")
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
        record = output / "evidence.json"
        record.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
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
    ) as exc:
        print(f"MEDORIGIN_SYNTHETIC_FHIR_DEMO_FAIL: {exc}", file=sys.stderr)
        print("Any partial output is nonqualifying; use a new --out directory.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
