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
PREVIEW_BOUNDARY_NAMES = (
    "patient-invalid-utf8", "patient-over-limit", "patient-exact-limit",
)
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
    body = m.group(1)
    entries = list(pattern.finditer(body))
    # finditer() only recognizes good entries. Without inspecting the gaps,
    # extra source tokens (e.g. an unrecognized FixtureSpec) could be
    # silently ignored while the twelve recognized hashes still match.
    # Every gap must be Rust's one optional comma plus whitespace only.
    previous_end = 0
    for entry in entries:
        require(re.fullmatch(r"\s*,?\s*", body[previous_end:entry.start()]) is not None,
                "UNPARSED_FIXTURE_CATALOG_CONTENT")
        previous_end = entry.end()
    require(re.fullmatch(r"\s*,?\s*", body[previous_end:]) is not None,
            "UNPARSED_FIXTURE_CATALOG_CONTENT")
    result: dict[str, tuple[int, str, str]] = {}
    for entry in entries:
        name, length, digest, status = entry.groups()
        require(name not in result, f"DUPLICATE_FIXTURE_{name}")
        result[name] = (int(length), digest, status)
    require(len(entries) == 12 and set(result) == set(EXPECTED_STATUS),
            "INCOMPLETE_OR_UNREVIEWED_FIXTURE_SET")
    # Fixture indices are a native keyboard and UIA selection contract.
    # Hash-correct entries reordered into different indices are not safe.
    require(tuple(result) == tuple(EXPECTED_STATUS),
            "CHANGED_FICTIONAL_FIXTURE_ORDER")
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
    # Freeze the D0 provider dispatch, not only literal bytes and D2 SHA.
    # A future refactor must not silently route a fixed id to another vector.
    names_to_const = {
        "patient-minimal": "PATIENT",
        "observation-minimal": "OBSERVATION",
        "observation-bad-subject": "OBSERVATION_BAD_SUBJECT",
        **{name: name.upper().replace("-", "_") for name in BUNDLE_NAMES},
    }
    try:
        hash_dispatch = source.split(
            "let (identity, required_bytes) = match fixture_id {", 1
        )[1].split("\n    };", 1)[0]
        byte_dispatch = source.split("let bytes = match identity {", 1)[1].split(
            "\n    };", 1
        )[0]
        preview_dispatch = source.split("pub fn fictional_json_preview_v1(", 1)[1].split(
            "const MAX_VISIBLE_FICTIONAL_JSON_BYTES", 1
        )[0]
    except IndexError as exc:
        raise ValueError("CHANGED_D0_DISPATCH_LAYOUT") from exc
    for name, const in names_to_const.items():
        require(hash_dispatch.count(f'"{name}" => ("{name}", {const}.len()),') == 1,
                f"CHANGED_D0_HASH_DISPATCH_{name}")
        require(byte_dispatch.count(f'"{name}" => {const}.to_vec(),') == 1,
                f"CHANGED_D0_BYTE_DISPATCH_{name}")
        require(preview_dispatch.count(f'"{name}" => ("{name}", {const}),') == 1,
                f"CHANGED_D0_PREVIEW_DISPATCH_{name}")
    # These three negative/boundary vectors are constructed inside D0
    # instead of residing in include_bytes! files. Do not audit assumed
    # bytes without verifying D0 still constructs *those same bytes*.
    require(source.count("const FHIR_RESOURCE_LIMIT_BYTES: usize = 32_768;") == 1,
            "CHANGED_D0_RESOURCE_LIMIT")
    boundary_size_arms = (
        '"patient-invalid-utf8" => ("patient-invalid-utf8", 1),',
        '"patient-over-limit" => ("patient-over-limit", FHIR_RESOURCE_LIMIT_BYTES + 1),',
        '"patient-exact-limit" => ("patient-exact-limit", FHIR_RESOURCE_LIMIT_BYTES),',
    )
    for name, arm in zip(PREVIEW_BOUNDARY_NAMES, boundary_size_arms):
        require(hash_dispatch.count(arm) == 1, f"CHANGED_D0_BOUNDARY_SIZE_{name}")
    boundary_byte_arms = {
        "patient-invalid-utf8": '"patient-invalid-utf8" => vec![0xff],',
        "patient-over-limit": '''"patient-over-limit" => vec![b' '; required_bytes],''',
    }
    for name, arm in boundary_byte_arms.items():
        require(byte_dispatch.count(arm) == 1, f"CHANGED_D0_BOUNDARY_BYTES_{name}")
    exact_limit = re.findall(
        r'"patient-exact-limit"\s*=>\s*\{(.*?)\}',
        byte_dispatch, re.DOTALL,
    )
    require(len(exact_limit) == 1 and re.sub(r"\s+", " ", exact_limit[0]).strip()
            == "let mut padded = PATIENT.to_vec(); "
               "padded.resize(required_bytes, b' '); padded",
            "CHANGED_D0_BOUNDARY_BYTES_patient-exact-limit")
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
