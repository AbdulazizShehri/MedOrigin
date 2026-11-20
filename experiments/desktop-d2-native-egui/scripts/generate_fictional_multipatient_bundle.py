"""Emit canonical, identity-only dummy FHIR-shaped Bundles for native D2.

This generator contains NO patient demographics, codes, values, or notes.
Output is stdout bytes only; caller chooses explicit synthetic preview flag.
It never reads user files, opens a browser/network, or launches native GUI.
"""

from __future__ import annotations

import argparse
import json
import sys


def make_fictional_bundle(patients: int, observations_per_patient: int) -> bytes:
    if not 1 <= patients <= 16 or not 1 <= observations_per_patient <= 3:
        raise ValueError("fictional_patient_or_observation_count_out_of_range")
    count = patients * (2 + observations_per_patient)
    if count > 48:
        raise ValueError("fictional_bundle_exceeds_48_resource_limit")

    def urn(number: int) -> str:
        return f"urn:uuid:00000000-0000-4000-8000-{number:012d}"

    entries: list[dict[str, object]] = []
    for number in range(1, patients + 1):
        patient = urn(number)
        encounter = urn(number + patients)
        entries.append(
            {
                "fullUrl": patient,
                "resource": {
                    "resourceType": "Patient",
                    "id": f"fictional-patient-{number:03d}",
                },
            }
        )
        entries.append(
            {
                "fullUrl": encounter,
                "resource": {
                    "resourceType": "Encounter",
                    "id": f"fictional-encounter-{number:03d}",
                    "subject": {"reference": patient},
                },
            }
        )
        for index in range(1, observations_per_patient + 1):
            observation_number = (number - 1) * observations_per_patient + index
            entries.append(
                {
                    "fullUrl": urn(2 * patients + observation_number),
                    "resource": {
                        "resourceType": "Observation",
                        "id": f"fictional-observation-{observation_number:03d}",
                        "subject": {"reference": patient},
                        "encounter": {"reference": encounter},
                    },
                }
            )
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {
            "tag": [
                {
                    "system": "https://medorigin.si/synthetic-only",
                    "code": "fictional-structural-demo-no-phi",
                }
            ]
        },
        "entry": entries,
    }
    raw = json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    if len(raw) > 32_768:
        raise ValueError("fictional_bundle_exceeds_byte_limit")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict dummy-only canonical FHIR-shaped Bundle")
    parser.add_argument("--patients", type=int, default=2)
    parser.add_argument("--observations-per-patient", type=int, default=2)
    args = parser.parse_args()
    try:
        raw = make_fictional_bundle(args.patients, args.observations_per_patient)
    except ValueError as exc:
        parser.error(str(exc))
    sys.stdout.buffer.write(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
