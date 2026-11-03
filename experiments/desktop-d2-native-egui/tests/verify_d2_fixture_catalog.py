#!/usr/bin/env python3
"""Fail-closed source-only audit of MedOrigin's 12 built-in fictional D2 fixtures.

Independent of Rust hash code. This checks source bytes and catalog identity,
NOT native execution, clinical data, network isolation, or release eligibility.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

BUNDLE_NAMES = (
    "bundle-valid", "bundle-bad-reference", "bundle-duplicate",
    "bundle-wrong-type", "bundle-linked", "bundle-dangling",
)
EXPECTED_STATUS = {
    "patient-minimal": "FHIR_ENVELOPE_OK",
    "patient-invalid-utf8": "INVALID_UTF8",
    "patient-over-limit": "RESOURCE_TOO_LARGE",
    "patient-exact-limit": "FHIR_ENVELOPE_OK",
    "observation-minimal": "FHIR_ENVELOPE_OK",
    "observation-bad-subject": "INVALID_REFERENCE",
    "bundle-valid": "BUNDLE_GRAPH_OK",
    "bundle-bad-reference": "INVALID_REFERENCE",
    "bundle-duplicate": "DUPLICATE_ENTRY",
    "bundle-wrong-type": "INVALID_BUNDLE_TYPE",
    "bundle-linked": "BUNDLE_GRAPH_OK",
    "bundle-dangling": "INVALID_REFERENCE",
}
PREVIEW_EXCLUDED = frozenset((
    "patient-invalid-utf8", "patient-over-limit", "patient-exact-limit",
))


def require(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError(why)


def fixed_literal(source: str, name: str) -> bytes:
    pattern = rf'^const {name}: &\[u8\] = br#"(.*?)"#;$'
    matches = re.findall(pattern, source, re.MULTILINE | re.DOTALL)
    require(len(matches) == 1, f"MISSING_OR_DUPLICATE_LITERAL_{name}")
    return matches[0].encode("utf-8")


def catalog(source: str) -> dict[str, tuple[int, str, str]]:
    m = re.search(
        r'pub const FIXTURES: \[FixtureSpec; 12\] = \[(.*?)^\];',
        source, re.MULTILINE | re.DOTALL,
    )
    require(m is not None, "MISSING_12_FIXTURE_CATALOG")
    pattern = re.compile(
        r'FixtureSpec\s*\{\s*id:\s*"([^"]+)",\s*'
        r'bytes:\s*(\d+),\s*sha256:\s*"([0-9a-f]{64})",\s*'
        r'status:\s*"([^"]+)",\s*\}', re.DOTALL,
    )
    entries = list(pattern.finditer(m.group(1)))
    result: dict[str, tuple[int, str, str]] = {}
    for entry in entries:
        name, length, digest, status = entry.groups()
        require(name not in result, f"DUPLICATE_FIXTURE_{name}")
        result[name] = (int(length), digest, status)
    require(len(entries) == 12 and set(result) == set(EXPECTED_STATUS),
            "INCOMPLETE_OR_UNREVIEWED_FIXTURE_SET")
    return result


def check_one(name: str, raw: bytes, claimed: tuple[int, str, str]) -> None:
    count, digest, status = claimed
    require(len(raw) == count, f"BYTES_MISMATCH_{name}")
    require(hashlib.sha256(raw).hexdigest() == digest, f"SHA256_MISMATCH_{name}")
    require(status == EXPECTED_STATUS[name], f"STATUS_MISMATCH_{name}")
    if name not in PREVIEW_EXCLUDED:
        require(len(raw) <= 2048, f"OVERSIZE_PREVIEW_{name}")
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise ValueError(f"INVALID_FICTIONAL_PREVIEW_{name}") from exc
        require(isinstance(parsed, dict) and "resourceType" in parsed,
                f"MISSING_FICTIONAL_RESOURCE_TYPE_{name}")


def verify(experiments_root: Path) -> dict:
    d0 = experiments_root / "desktop-d0-rust"
    d2 = experiments_root / "desktop-d2-native-egui"
    source = (d0 / "src" / "lib.rs").read_text(encoding="utf-8")
    records = catalog((d2 / "src" / "app.rs").read_text(encoding="utf-8"))
    patient = fixed_literal(source, "PATIENT")
    vectors = {
        "patient-minimal": patient,
        "patient-invalid-utf8": b"\xff",
        "patient-over-limit": b" " * 32769,
        "patient-exact-limit": patient.ljust(32768, b" "),
        "observation-minimal": fixed_literal(source, "OBSERVATION"),
        "observation-bad-subject": fixed_literal(source, "OBSERVATION_BAD_SUBJECT"),
    }
    for name in BUNDLE_NAMES:
        const = name.upper().replace("-", "_")
        declaration = (f'const {const}: &[u8] = '
                       f'include_bytes!("../fixtures/{name}.json");')
        require(source.count(declaration) == 1, f"CHANGED_BUNDLE_INCLUDE_{name}")
        file = d0 / "fixtures" / f"{name}.json"
        require(file.is_file() and not file.is_symlink(),
                f"MISSING_OR_LINKED_FICTIONAL_FIXTURE_{name}")
        vectors[name] = file.read_bytes()
    for name, claimed in records.items():
        check_one(name, vectors[name], claimed)
    return {
        "contract": "medorigin-d2-fictional-fixtures-source-only-v1",
        "result": "SOURCE_CATALOG_INTEGRITY_PASS_NOT_RELEASE",
        "fixtures_verified": len(records),
        "preview_fixtures_verified": len(records) - len(PREVIEW_EXCLUDED),
        "release_authorized": False,
        "runtime_network_isolation_proven": False,
        "clinical_fhir_validated": False,
    }


def main() -> int:
    try:
        result = verify(Path(__file__).resolve().parents[2])
        code = 0  # Source-only integrity, NEVER a release PASS.
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        result = {
            "contract": "medorigin-d2-fictional-fixtures-source-only-v1",
            "result": "REFUSE_SOURCE_CATALOG",
            "reason": str(exc)[:180],
            "release_authorized": False,
            "runtime_network_isolation_proven": False,
            "clinical_fhir_validated": False,
        }
        code = 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
