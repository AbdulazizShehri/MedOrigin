"""Verify source-bound, raw-byte synthetic fixtures for future Rust desktop parity.

This zero-dependency, read-only check is NOT a Rust implementation, benchmark,
FHIR validator, publisher, or approval of patient-data processing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final

_ROOT: Final = Path(__file__).resolve().parents[1]
_SOURCE: Final = _ROOT / "tests/test_clinical_workspace_fhir_payload_bytes_contract.py"
_MANIFEST: Final = _ROOT / "docs/evidence/medorigin_desktop_d0_vectors_v1.json"
_SOURCE_COMMIT: Final = "dd84bb7b4177fbc169a04370772610ec66fa41df"
_PATIENT: Final = b'{"resourceType":"Patient","id":"synthetic","active":true}'
_FHIR_LIMIT: Final = 32768
_SOURCE_PATIENT_LITERAL: Final = (
    "payload = b'{\"resourceType\":\"Patient\",\"id\":\"synthetic\",\"active\":true}'"
)


class FixtureContractError(ValueError):
    """The approved, synthetic-only source/manifest pair no longer agrees."""


def case_bytes() -> dict[str, bytes]:
    """The exact raw bytes, without JSON parsing or reserialization."""
    return {
        "patient-minimal": _PATIENT,
        "patient-invalid-utf8": bytes([0xFF]),
        "patient-over-limit": b" " * (_FHIR_LIMIT + 1),
        "patient-exact-limit": _PATIENT + b" " * (_FHIR_LIMIT - len(_PATIENT)),
    }


def expected_manifest() -> dict[str, object]:
    cases = case_bytes()
    status = {
        "patient-minimal": "accept",
        "patient-invalid-utf8": "reject-parse",
        "patient-over-limit": "reject-size",
        "patient-exact-limit": "accept",
    }
    return {
        "schema": "medorigin-desktop-d0-raw-sha256-v1",
        "status": "SYNTHETIC_ONLY_NOT_RELEASED",
        "algorithm": "SHA-256-of-raw-bytes",
        "source_commit": _SOURCE_COMMIT,
        "source_fixture": "tests/test_clinical_workspace_fhir_payload_bytes_contract.py",
        "fhir_resource_limit_bytes": _FHIR_LIMIT,
        "publication_authorized": False,
        "rust_parity_qualified": False,
        "vectors": [
            {
                "id": name,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "expected_python_fhir_parse": status[name],
            }
            for name, raw in cases.items()
        ],
    }


def verify_manifest(
    *,
    manifest_path: Path = _MANIFEST,
    source_path: Path = _SOURCE,
) -> dict[str, object]:
    """Reject stale source fixtures and any byte/expected-status manifest drift."""
    source = source_path.read_text(encoding="utf-8")
    if (
        _SOURCE_PATIENT_LITERAL not in source
        or 'fhir.MAXIMUM_RESOURCE_BYTES + 1' not in source
        or 'payload += b" " * (fhir.MAXIMUM_RESOURCE_BYTES - len(payload))' not in source
    ):
        raise FixtureContractError("source fixture expressions have changed")
    raw_manifest = manifest_path.read_text(encoding="utf-8")
    expected = expected_manifest()
    canonical = json.dumps(expected, sort_keys=True, indent=2) + "\n"
    if raw_manifest != canonical:
        raise FixtureContractError("committed synthetic vector manifest has drifted")
    return expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit",
        action="store_true",
        help="Print expected JSON for inspection; do not modify the manifest",
    )
    args = parser.parse_args(argv)
    if args.emit:
        print(json.dumps(expected_manifest(), sort_keys=True, indent=2))
        return 0
    try:
        result = verify_manifest()
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"DESKTOP_D0_VECTORS_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(
        "DESKTOP_D0_RAW_VECTORS_VERIFIED: "
        f"{len(result['vectors'])} synthetic cases; "
        "Rust parity and publication NOT qualified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
