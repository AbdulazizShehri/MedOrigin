"""Two genuinely installed Core CLI versions: read-only fictional import planning.

Use only invented local files and separately installed source-bound
Python 3.11/3.12 medscale console entrypoints. No PHI, EHR, telemetry,
database, network or conformance/release approval.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from qa_medorigin_installed_r4_status_binding import _fictional_bundle

_SECRET = "FICTIONAL_PRIVATE_TEXT_NEVER_DISPLAY"
_ALLOWED_FAILURE = "file readiness refused: source_or_timeline_preflight_refused"


def _two() -> list[dict[str, Any]]:
    first = _fictional_bundle()
    first["entry"][1]["resource"]["name"] = [{"text": _SECRET}]
    second = copy.deepcopy(first)
    substitutions = {
        f"urn:uuid:00000000-0000-4000-8000-{i:012d}":
        f"urn:uuid:00000000-0000-4000-8000-{i+3:012d}"
        for i in (1, 2, 3)
    }
    for entry in second["entry"]:
        entry["fullUrl"] = substitutions[entry["fullUrl"]]
        r = entry["resource"]
        r["id"] = r["id"].replace("-001", "-002")
        if "subject" in r:
            r["subject"]["reference"] = substitutions[r["subject"]["reference"]]
        if "encounter" in r:
            r["encounter"]["reference"] = substitutions[r["encounter"]["reference"]]
    second["entry"][0]["resource"]["effectiveDateTime"] = "2026-11-05T00:10:00Z"
    second["entry"][2]["resource"]["period"] = {
        "start": "2026-11-04T22:20:00Z",
        "end": "2026-11-04T23:00:00Z",
    }
    return [first, second]


def _files(root: Path, docs: list[dict[str, Any]]) -> list[Path]:
    out: list[Path] = []
    for index, doc in enumerate(docs, 1):
        path = root / f"{_SECRET}-{index}.json"
        path.write_text(
            json.dumps(doc, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        out.append(path)
    return out


def _call(cli: Path, root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(cli), "fhir", *args],
        cwd=root, capture_output=True, text=True, check=False, timeout=75
    )
    visible = result.stdout + result.stderr
    if (
        _SECRET in visible
        or "urn:uuid:" in visible
        or str(root) in visible
        or "fictional-patient-001" in visible
    ):
        raise AssertionError("installed Core leaked a source path or identity")
    return result


def _positive(result: subprocess.CompletedProcess[str], *, official: bool) -> dict:
    if result.returncode != 2 or result.stderr:
        raise AssertionError("installed Core did not return truthful read-only readiness")
    try:
        report = json.loads(result.stdout)
    except ValueError as exc:
        raise AssertionError("installed Core readiness JSON missing") from exc
    required = {
        "schema": "medorigin-core-fictional-file-batch-readiness/v1",
        "status": "SYNTHETIC_READ_ONLY_IMPORT_READINESS_NOT_VALIDATED",
        "source_count": 2,
        "total_resource_count": 6,
        "total_timeline_events": 4,
        "total_dated_events": 2,
        "total_undated_events": 2,
        "official_r4_structural_status": (
            "official_r4_structure_only_not_validated" if official else "not_requested"
        ),
    }
    if not isinstance(report, dict) or any(
        report.get(key) != value for key, value in required.items()
    ):
        raise AssertionError("installed Core readiness aggregate inconsistent")
    for key in (
        "source_filenames_included", "patient_identity_included",
        "precise_timestamps_included", "cross_source_patient_join_performed",
        "payload_included", "workspace_allocated", "output_persisted",
        "network_access_performed", "fhir_r4_conformance_validated",
        "clinical_use_authorized", "publication_authorized",
    ):
        if report.get(key) is not False:
            raise AssertionError("installed Core readiness asserted forbidden authority")
    docs = report.get("sources")
    if (
        type(docs) is not list
        or len(docs) != 2
        or [d.get("source_ordinal") for d in docs] != [1, 2]
        or [d.get("dated_event_count") for d in docs] != [0, 2]
        or [d.get("undated_event_count") for d in docs] != [2, 0]
        or [d.get("first_day_utc") for d in docs] != [None, "2026-11-04"]
        or [d.get("last_day_utc") for d in docs] != [None, "2026-11-05"]
        or len({d.get("source_content_sha256") for d in docs}) != 2
    ):
        raise AssertionError("installed Core per-source dates/identity contract invalid")
    return report


def _negative(result: subprocess.CompletedProcess[str], message: str) -> None:
    if result.returncode != 2 or result.stdout or result.stderr.strip() != message:
        raise AssertionError("installed Core did not fail closed without partial output")


def _triage(
    result: subprocess.CompletedProcess[str],
    *, stage: str | None = None, reason: str | None = None,
) -> dict:
    if result.returncode != 2 or result.stderr:
        raise AssertionError("installed Core failed truthful read-only file triage")
    try:
        report = json.loads(result.stdout)
    except ValueError as exc:
        raise AssertionError("actual installed Core triage missing JSON") from exc
    if (
        type(report) is not dict
        or report.get("schema") != "medorigin-core-fictional-prestorage-file-triage/v1"
        or report.get("status") != "SYNTHETIC_FILE_TRIAGE_ONLY_NOT_VALIDATED"
        or report.get("source_count") != 2
        or type(report.get("sources")) is not list
        or len(report["sources"]) != 2
    ):
        raise AssertionError("actual installed Core triage contract drifted")
    for flag in (
        "source_filenames_included", "patient_identity_included",
        "precise_timestamps_included", "payload_included", "workspace_allocated",
        "output_persisted", "network_access_performed",
        "cross_source_patient_join_performed", "official_r4_schema_checked",
        "fhir_r4_conformance_validated", "clinical_use_authorized",
        "publication_authorized",
    ):
        if report.get(flag) is not False:
            raise AssertionError("actual installed Core triage claimed unsafe authority")
    if (
        type(report["sources"][0]) is not dict
        or report["sources"][0].get("status") != "ready_for_synthetic_readiness_only"
        or report["sources"][0].get("source_ordinal") != 1
    ):
        raise AssertionError("actual installed Core first source lost verified result")
    second = report["sources"][1]
    if type(second) is not dict or second.get("source_ordinal") != 2:
        raise AssertionError("actual installed Core lost source ordinal")
    if stage is None:
        if (
            report.get("source_ready_count") != 2
            or report.get("source_blocked_count") != 0
            or report.get("all_sources_locally_ready") is not True
            or second.get("status") != "ready_for_synthetic_readiness_only"
            or second.get("reason_code") is not None
            or second.get("dated_event_count") != 2
            or second.get("first_day_utc") != "2026-11-04"
            or second.get("last_day_utc") != "2026-11-05"
        ):
            raise AssertionError("installed Core positive triage disagrees with readiness")
    elif (
        report.get("source_ready_count") != 1
        or report.get("source_blocked_count") != 1
        or report.get("all_sources_locally_ready") is not False
        or second.get("status") != "blocked"
        or second.get("stage") != stage
        or second.get("reason_code") != reason
        or second.get("source_content_sha256") is not None
    ):
        raise AssertionError("installed Core triage did not identify fixed second-file cause")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli311", type=Path, required=True)
    parser.add_argument("--cli312", type=Path, required=True)
    parser.add_argument("--official-r4-schema", type=Path, required=True)
    args = parser.parse_args(argv)
    clis = (args.cli311, args.cli312)
    if (
        any(not path.is_file() for path in clis)
        or clis[0].resolve() == clis[1].resolve()
        or not args.official_r4_schema.is_file()
    ):
        parser.error("two independent installed CLIs and the official source ZIP required")

    with TemporaryDirectory(prefix="medorigin-installed-fhir-readiness-only-") as tmp:
        root = Path(tmp)
        sources = _files(root, _two())
        plain = ["file-batch-readiness", "--synthetic-only", *(str(p) for p in sources)]
        official = [
            "file-batch-readiness", "--synthetic-only",
            "--offline-r4-schema", str(args.official_r4_schema),
            *(str(p) for p in sources),
        ]
        first = _positive(_call(clis[0], root, plain), official=False)
        second = _positive(_call(clis[1], root, plain), official=False)
        if first != second:
            raise AssertionError("readiness varies by installed interpreter version")
        official_a = _positive(_call(clis[0], root, official), official=True)
        official_b = _positive(_call(clis[1], root, official), official=True)
        if official_a != official_b:
            raise AssertionError("official schema readiness differs by interpreter")
        if first["sources"] != official_a["sources"]:
            raise AssertionError("schema option altered source identities or date counts")

        # Source-ordinal triage is distinct from existing relationship-only
        # triage: it must agree with actual no-store readiness when ready.
        triage_args = ["file-batch-triage", "--synthetic-only", *(str(p) for p in sources)]
        triage_311 = _triage(_call(clis[0], root, triage_args))
        triage_312 = _triage(_call(clis[1], root, triage_args))
        if triage_311 != triage_312:
            raise AssertionError("actual installed pre-storage triage differs by Python")

        broken = _two()
        broken[1]["entry"][2]["resource"]["period"] = {
            "start": "2026-11-06T06:00:00Z",
            "end": "2026-11-05T06:00:00Z",
        }
        invalid = _files(root, broken)
        for cli in clis:
            _triage(
                _call(cli, root, [
                    "file-batch-triage", "--synthetic-only",
                    *(str(p) for p in invalid),
                ]),
                stage="timeline",
                reason="timeline_encounter_period_reversed",
            )
            _negative(
                _call(cli, root, [
                    "file-batch-readiness", "--synthetic-only",
                    *(str(p) for p in invalid),
                ]),
                _ALLOWED_FAILURE,
            )
            _negative(
                _call(cli, root, [
                    "file-batch-encrypted-demo", "--synthetic-only", "--ephemeral-demo",
                    *(str(p) for p in invalid),
                ]),
                "file batch demo refused: verified_encrypted_fictional_batch_refused",
            )
            _negative(
                _call(cli, root, ["file-batch-readiness", *(str(p) for p in sources)]),
                "file readiness refused: explicit_fictional_readonly_batch_required",
            )
        # A distinct invalid relationship also carries a source-ordinal
        # finite reason; a completely unmarked source blocks ALL output.
        invalid_rel = _two()
        invalid_rel[1]["entry"][0]["resource"]["status"] = "FINAL"
        invalid_files = _files(root, invalid_rel)
        for cli in clis:
            _triage(
                _call(cli, root, [
                    "file-batch-triage", "--synthetic-only",
                    *(str(p) for p in invalid_files),
                ]),
                stage="local_relationship",
                reason="observation_status_not_in_r4_required_codes",
            )
        invalid_rel[1].pop("meta")
        unmarked = _files(root, invalid_rel)
        for cli in clis:
            _negative(
                _call(cli, root, [
                    "file-batch-triage", "--synthetic-only",
                    *(str(p) for p in unmarked),
                ]),
                "file triage refused: unqualified_batch_or_marker",
            )
        if {p.name for p in root.iterdir()} != {p.name for p in sources}:
            # Invalid version overwrites same named temporary caller inputs,
            # but neither workflow may create any SQLite/Workspace or output.
            raise AssertionError("readiness or refused import created unexpected files")
    print("MEDORIGIN_REAL_INSTALLED_FHIR_BATCH_READINESS_PASS_NOT_RELEASE")
    print("MEDORIGIN_REAL_INSTALLED_FHIR_PRESTORE_TRIAGE_PASS_NOT_RELEASE")
    print("INSTALLED_PYTHON_RUNTIMES=3.11,3.12")
    print("OFFICIAL_HL7_R4_SCHEMA_STRUCTURE_ONLY_NOT_VALIDATED=true")
    print("READONLY_SOURCES=2 DATED_EVENTS=2 UNDATED_EVENTS=2")
    print("FHIR_CONFORMANCE_VALIDATED=false CLINICAL_USE_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
