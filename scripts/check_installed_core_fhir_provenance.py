"""Offline, installed-CLI FHIR provenance smoke. Never asserts FHIR conformance.

The previous synthetic release demo requires status=valid/exit 0 and is
incompatible with the corrected fail-closed Core FHIR boundary. This
read-only Core-only smoke verifies the new installed behavior without
approving a release or changing the desktop/static-preview contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "synthetic_fhir_developer_beta"
KNOWN = FIXTURES / "synthetic_structure_definition.json"
MALFORMED = FIXTURES / "malformed.json"
TIMESTAMP = "2026-10-24T00:00:00Z"
WARNING = (
    "FHIR R4 schema, terminology, and profile validation were not performed; "
    "this local report records deterministic provenance only."
)
VERSION = "medscale 0.3.0"
MAX_OUTPUT = 64_000
STATUS = "LOCAL_FHIR_PROVENANCE_ONLY"
REPORT_KEYS = frozenset(
    {
        "created_at",
        "errors",
        "format_version",
        "input_hash",
        "report_id",
        "status",
        "validator_name",
        "validator_version",
        "warnings",
    }
)


class QualificationError(ValueError):
    """No locally installed CLI result can justify a validation or release claim."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise QualificationError("duplicate JSON member")
        result[key] = value
    return result


def _object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError) as exc:
        raise QualificationError("unreadable or ambiguous JSON") from exc
    if not isinstance(value, dict):
        raise QualificationError("expected JSON object")
    return value


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _input_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return _hash(encoded)


def call(cli: Path, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Bound the fixed, local CLI invocation; never include its output on failure."""
    offline_env = {
        **os.environ,
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PIP_NO_INDEX": "1",
    }
    try:
        result = subprocess.run(
            [str(cli), *args],
            cwd=cwd,
            env=offline_env,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QualificationError("installed CLI could not complete") from exc
    if len(result.stdout) > MAX_OUTPUT or len(result.stderr) > MAX_OUTPUT:
        raise QualificationError("installed CLI output exceeds bounds")
    return result


def _report_case(
    cli: Path, fixture: Path, payload: dict[str, Any], parent: Path, label: str
) -> str:
    destination = parent / label
    completed = call(
        cli,
        [
            "fhir",
            "validate",
            str(fixture),
            "--created-at",
            TIMESTAMP,
            "--output-dir",
            str(destination),
        ],
        parent,
    )
    if completed.returncode != 2:
        raise QualificationError("local FHIR CLI must exit 2 without real validation")
    data = _object(completed.stdout)
    if (
        set(data) != REPORT_KEYS
        or data["status"] != "not_validated"
        or data["warnings"] != [WARNING]
        or data["errors"] != []
        or data["created_at"] != TIMESTAMP
        or data["format_version"] != "fhirkit-validation-report/v1"
        or data["validator_name"] != "medscale-fhirkit-local"
        or data["validator_version"] != "0.1.0"
        or data["report_id"] != ""
        or data["input_hash"] != _input_hash(payload)
    ):
        raise QualificationError("FHIR local report claims an unperformed validation")
    reports = list(destination.rglob("report.json"))
    if len(reports) != 1 or reports[0].is_symlink():
        raise QualificationError("one local content-addressed report required")
    stored = reports[0].read_bytes()
    if stored != completed.stdout.encode("utf-8"):
        raise QualificationError("saved report differs from installed CLI receipt")
    return _hash(stored)


def _run_one(cli: Path, root: Path, label: str) -> dict[str, str]:
    if not cli.is_file():
        raise QualificationError("installed CLI executable not found")
    version = call(cli, ["--version"], root)
    if version.returncode != 0 or version.stdout.strip() != VERSION:
        raise QualificationError("installed CLI version is not qualified")
    known_payload = _object(KNOWN.read_text(encoding="utf-8"))
    unknown_payload = {
        "resourceType": "UnknownFictionalResource",
        "id": "fictional-negative-control",
    }
    unknown = root / ("unknown-" + label + ".json")
    unknown.write_text(
        json.dumps(unknown_payload, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    known_sha = _report_case(cli, KNOWN, known_payload, root, label + "-known")
    unknown_sha = _report_case(cli, unknown, unknown_payload, root, label + "-unknown")
    if known_sha == unknown_sha:
        raise QualificationError("different fictional inputs share a report digest")

    summary = call(cli, ["fhir", "validate", str(KNOWN), "--summary-only"], root)
    if summary.returncode != 0 or _object(summary.stdout) != known_payload:
        raise QualificationError("explicit summary-only behavior regressed")
    malformed = call(cli, ["fhir", "validate", str(MALFORMED), "--summary-only"], root)
    if malformed.returncode != 1 or malformed.stdout.strip():
        raise QualificationError("malformed JSON is not safely rejected")
    return {"known_report_sha256": known_sha, "unknown_report_sha256": unknown_sha}


def qualify(clis: list[Path]) -> dict[str, Any]:
    """Verify one or two source-bound *externally qualified* installed CLIs."""
    if not 1 <= len(clis) <= 2:
        raise QualificationError("one or two installed CLIs required")
    if len({cli.resolve() for cli in clis}) != len(clis):
        raise QualificationError("independent installed CLI paths required")
    if not KNOWN.is_file() or not MALFORMED.is_file():
        raise QualificationError("synthetic fixtures missing")
    with tempfile.TemporaryDirectory(prefix="medorigin-fhir-local-qa-") as directory:
        temp = Path(directory)
        receipts = [_run_one(cli, temp, f"run_{i + 1}") for i, cli in enumerate(clis)]
    if len(receipts) == 2 and receipts[0] != receipts[1]:
        raise QualificationError("installed runtimes disagree on deterministic local receipts")
    return {
        "status": STATUS,
        "installed_cli_count": len(clis),
        "known_report_sha256": receipts[0]["known_report_sha256"],
        "unknown_report_sha256": receipts[0]["unknown_report_sha256"],
        "fhir_conformance_validated": False,
        "publication_authorized": False,
        "clinical_use_authorized": False,
        "independent_security_review_complete": False,
        "prepublication_rehearsal_qualified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--alt-cli", type=Path)
    args = parser.parse_args(argv)
    try:
        result = qualify([args.cli, *([args.alt_cli] if args.alt_cli else [])])
    except (QualificationError, OSError, ValueError):
        # Avoid forwarding installed CLI output, report JSON, or filesystem paths.
        print("CORE_FHIR_PROVENANCE_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
