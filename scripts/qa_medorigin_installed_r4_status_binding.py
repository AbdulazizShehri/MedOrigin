"""Verify real installed Core CLIs enforce HL7 FHIR R4 status admission.

Runs unchanged installed Core executable paths in independent 3.11/3.12
environments, not editable source imports or simulated CLI calls. These
invented three-resource Bundles carry no real patient or EHR information.
Exact required-code binding is only a *narrow* local preflight; not full
FHIR R4 conformance, a production patient-data gateway or release approval.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

_PRIVATE = "NEVER_ECHO_FICTIONAL_PATIENT_SENTINEL"
_PATIENT = "urn:uuid:00000000-0000-4000-8000-000000000002"
_ENCOUNTER = "urn:uuid:00000000-0000-4000-8000-000000000003"
_ENCOUNTER_R4 = (
    "planned", "arrived", "triaged", "in-progress", "onleave",
    "finished", "cancelled", "entered-in-error", "unknown",
)
_OBSERVATION_R4 = (
    "registered", "preliminary", "final", "amended", "corrected",
    "cancelled", "entered-in-error", "unknown",
)
_NEGATIVE: tuple[tuple[str, str], ...] = (
    ("Encounter", "completed"),  # R5 not R4
    ("Encounter", "on-hold"),  # R5 not R4
    ("Encounter", "discharged"),  # R5 not R4
    ("Encounter", "FINISHED"),
    ("Encounter", "finished "),
    ("Observation", "completed"),
    ("Observation", "FINAL"),
    ("Observation", "final "),
    ("Observation", "ｆｉｎａｌ"),
    ("Observation", "unknown-code"),
)


def _fictional_bundle() -> dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {
            "tag": [{
                "system": "urn:medorigin:fixture-classification",
                "code": "synthetic",
            }]
        },
        "entry": [
            {
                "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000001",
                "resource": {
                    "resourceType": "Observation",
                    "id": "fictional-observation-001",
                    "status": "final",
                    "code": {"text": "invented-only-test"},
                    "subject": {"reference": _PATIENT},
                    "encounter": {"reference": _ENCOUNTER},
                },
            },
            {
                "fullUrl": _PATIENT,
                "resource": {
                    "resourceType": "Patient",
                    "id": "fictional-patient-001",
                    "name": [{"text": _PRIVATE}],
                },
            },
            {
                "fullUrl": _ENCOUNTER,
                "resource": {
                    "resourceType": "Encounter",
                    "id": "fictional-encounter-001",
                    "status": "finished",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                    },
                    "subject": {"reference": _PATIENT},
                },
            },
        ],
    }


def _version(cli: Path, root: Path) -> None:
    response = subprocess.run(
        [str(cli), "--version"],
        cwd=root, capture_output=True, text=True, timeout=30, check=False
    )
    if response.returncode != 0 or response.stdout.strip() != "medscale 0.3.0":
        raise AssertionError("installed Core runtime version identity refused")


def _run(
    cli: Path, root: Path, payload: dict[str, Any], label: str,
    *, synthetic_flag: bool = True,
) -> subprocess.CompletedProcess[str]:
    source = root / (label + "-" + _PRIVATE + ".json")
    source.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    argv = [str(cli), "fhir", "bundle-preflight", str(source)]
    if synthetic_flag:
        argv.append("--synthetic-only")
    result = subprocess.run(
        argv, cwd=root, capture_output=True, text=True, timeout=45, check=False
    )
    # The installed CLI must NEVER include the fictional patient's name,
    # IDs or the caller-selected absolute path in any receipt or refusal.
    visible = result.stdout + result.stderr
    if (
        _PRIVATE in visible
        or str(source) in visible
        or _PATIENT in visible
        or _ENCOUNTER in visible
        or "fictional-patient-001" in visible
    ):
        raise AssertionError("installed Core echoed forbidden fictional source content")
    return result


def _assert_positive(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode != 0 or result.stderr:
        raise AssertionError("actual installed R4 status preflight refused valid status")
    try:
        report = json.loads(result.stdout)
    except ValueError as exc:
        raise AssertionError("installed R4 preflight did not return JSON") from exc
    expected = {
        "schema": "medorigin-synthetic-fhir-bundle-preflight/v1",
        "status": "local_relationship_preflight_only",
        "data_class": "SYNTHETIC_ASSERTED_NOT_VERIFIED",
        "resource_count": 3,
        "resource_counts": {"Encounter": 1, "Observation": 1, "Patient": 1},
        "local_references_checked": 3,
        "payload_content_included": False,
        "input_persisted": False,
        "network_access_performed": False,
        "full_fhir_r4_conformance_established": False,
        "terminology_profiles_invariants_verified": False,
        "all_possible_reference_fields_verified": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
    }
    if (
        not isinstance(report, dict)
        or set(report) != set(expected) | {"source_content_sha256"}
        or any(type(report[key]) is not type(value) or report[key] != value
               for key, value in expected.items())
        or type(report["source_content_sha256"]) is not str
        or len(report["source_content_sha256"]) != 64
        or any(ch not in "0123456789abcdef" for ch in report["source_content_sha256"])
    ):
        raise AssertionError("installed status receipt exceeded narrow nonclinical contract")
    return json.dumps(report, sort_keys=True, separators=(",", ":"))


def _assert_negative(
    result: subprocess.CompletedProcess[str], code: str
) -> None:
    if (
        result.returncode != 2
        or result.stdout != ""
        or result.stderr.strip() != "bundle preflight refused: " + code
    ):
        raise AssertionError("installed Core failed closed without exact redacted reason")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli311", type=Path, required=True)
    parser.add_argument("--cli312", type=Path, required=True)
    args = parser.parse_args(argv)
    clis = (args.cli311, args.cli312)
    if any(not c.is_file() for c in clis) or clis[0].resolve() == clis[1].resolve():
        parser.error("two independent installed Core command paths required")

    cases = 0
    with TemporaryDirectory(prefix="medorigin-installed-r4-status-only-") as td:
        root = Path(td)
        for cli in clis:
            _version(cli, root)
        for kind, statuses in (
            ("Encounter", _ENCOUNTER_R4),
            ("Observation", _OBSERVATION_R4),
        ):
            index = 2 if kind == "Encounter" else 0
            for number, status in enumerate(statuses):
                payload = _fictional_bundle()
                payload["entry"][index]["resource"]["status"] = status
                a = _assert_positive(
                    _run(clis[0], root, payload, f"valid-{kind}-{number}-311")
                )
                b = _assert_positive(
                    _run(clis[1], root, payload, f"valid-{kind}-{number}-312")
                )
                if a != b:
                    raise AssertionError("real installed R4 status result differs across runtimes")
                cases += 1
        for number, (kind, status) in enumerate(_NEGATIVE):
            source = _fictional_bundle()
            index = 2 if kind == "Encounter" else 0
            source["entry"][index]["resource"]["status"] = status
            reason = (
                "encounter_status_not_in_r4_required_codes"
                if kind == "Encounter"
                else "observation_status_not_in_r4_required_codes"
            )
            for label, cli in enumerate(clis):
                _assert_negative(
                    _run(cli, root, source, f"bad-{kind}-{number}-{label}"),
                    reason,
                )
            cases += 1
        for label, cli in enumerate(clis):
            # Missing caller synthetic assertion has a separately specified
            # refusal prefix, not a resource-validation error.
            denied = _run(
                cli, root, _fictional_bundle(), f"missing-flag-{label}",
                synthetic_flag=False,
            )
            if (
                denied.returncode != 2 or denied.stdout
                or denied.stderr.strip()
                != "bundle preflight refused: synthetic_only_attestation_required"
            ):
                raise AssertionError("installed Core bypassed explicit fictional-only consent")
    print("MEDORIGIN_INSTALLED_R4_STATUS_BINDINGS_PASS_NOT_RELEASE")
    print(f"R4_KNOWN_CODE_CLASSES={len(_ENCOUNTER_R4)}+{len(_OBSERVATION_R4)}")
    print(f"INDEPENDENT_RUNTIME_POSITIVE_NEGATIVE_CASES={cases}")
    print("FHIR_CONFORMANCE_VALIDATED=false CLINICAL_USE_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
