"""Prepare/verify one SHA-pinned MedOrigin v0.3.0 UNPUBLISHED QA ZIP.

Standard-library-only. No deployment, network access, package install,
tag creation, protected branch changes, model loading or patient data.
This handoff is deliberately distinct from the older dual-SHA QA bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

SOURCE_SHA = "62870f7f55848d289f78941b862092b9a0f366a0"
WHEEL = "medscale-0.3.0-py3-none-any.whl"
SDIST = "medscale-0.3.0.tar.gz"
PINNED = {
    WHEEL: "a718b77794c817dfcf6a711cd97324b3626e4d65382ba39c670a7c303fae07e7",
    SDIST: "85aae79bf41a935e967cde5c111b5c3f652430a25a03b43655fc7bd339a1d72a",
}
SOURCE_ROOT = Path(__file__).resolve().parents[1]
# Core #617 source is intentionally pinned independently of the QA-tool commit.
# The owner must requalify *new* release sources and hashes before revising this.

ZIP_NAME = "MedOrigin-v0.3.0-62870f7f-Developer-Beta-UNPUBLISHED.zip"
EXAMPLE_ROOT = "examples/synthetic_fhir_developer_beta/"
EXAMPLES = (
    "README.md",
    "desktop.py",
    "evidence_export.py",
    "malformed.json",
    "preview.py",
    "reproduce.py",
    "synthetic_cases.py",
    "synthetic_structure_definition.json",
)
MANIFEST = "BUNDLE_MANIFEST.json"
CHECKSUMS = "SHA256SUMS.txt"
PROVENANCE = "provenance/MEDORIGIN_SOURCE_PROVENANCE.json"
README = "README_UNPUBLISHED_QA.md"
MEMBERS = frozenset(
    {
        MANIFEST,
        CHECKSUMS,
        PROVENANCE,
        README,
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        *(f"artifacts/{name}" for name in (WHEEL, SDIST)),
        *(EXAMPLE_ROOT + name for name in EXAMPLES),
    }
)
# Every non-checksum member, including executable examples and provenance,
# is independently pinned to the already-qualified immutable #617 source.
# The ZIP's own SHA256SUMS is not a trust anchor.
SOURCE_MEMBER_SHA256 = {
    "BUNDLE_MANIFEST.json": "5e6cc422d1adf378d2d21dc847774f29379535fe1e4dee62f5831a0b39c156f0",
    "LICENSE": "5da5b11f7d224c2a2e2a3d11c37d5ae9a6fd2d1d3d6229354b992c4dd58c3792",
    "README_UNPUBLISHED_QA.md": "80070c1501cbb6d00c32fba96cb3c9e8241fd28e83cf8274d630fe4303b9d132",
    "THIRD_PARTY_NOTICES.md": "ce6d3251138cd27d90bf27518e06cc50b0bc4dbb7dcf203e8ddb8695456019d7",
    "artifacts/medscale-0.3.0-py3-none-any.whl": (
        "a718b77794c817dfcf6a711cd97324b3626e4d65382ba39c670a7c303fae07e7"
    ),
    "artifacts/medscale-0.3.0.tar.gz": (
        "85aae79bf41a935e967cde5c111b5c3f652430a25a03b43655fc7bd339a1d72a"
    ),
    "examples/synthetic_fhir_developer_beta/README.md": (
        "c3a75e9e3dd9aac3ea06333af66f10baf86ebc3a17d3a57a69c6301e3436e203"
    ),
    "examples/synthetic_fhir_developer_beta/desktop.py": (
        "6eb01ae36dd63b8112062bdc8b43e3b26c78c0d2d63ad4cf7b589746a39005b5"
    ),
    "examples/synthetic_fhir_developer_beta/evidence_export.py": (
        "3dcda237b734b98c26061f16d8c92eec6b799ef925c936d828fa6b83dd767ffc"
    ),
    "examples/synthetic_fhir_developer_beta/malformed.json": (
        "86158a37c4021be8fbfa95733f98ac90b4bc8da2595bd164452b3f750c78a378"
    ),
    "examples/synthetic_fhir_developer_beta/preview.py": (
        "ab8c4dfb976265729e9073d01804c60788413f8358f47535522b24ad4f1b5bb0"
    ),
    "examples/synthetic_fhir_developer_beta/reproduce.py": (
        "ae98851ffe5bf1c6a795ee44310f5717a53c7ec3261d987fc33eadcd006d8eed"
    ),
    "examples/synthetic_fhir_developer_beta/synthetic_cases.py": (
        "9a551d1002c88ae947ecfd96da9b024d8c329bf466a932c78c98cdc77d4978c4"
    ),
    "examples/synthetic_fhir_developer_beta/synthetic_structure_definition.json": (
        "8a3703ef9938438eee8544c9083246b7b42f15e95dbc9847df2f1deb18087b14"
    ),
    "provenance/MEDORIGIN_SOURCE_PROVENANCE.json": (
        "f6fe1e8c40157b735a5abe002653abad50eb8edf3d88ed6050208f83b7d6a26c"
    ),
}
MAX_ZIP = 5_000_000
MAX_FILE = 2_000_000
STAMP = (2020, 1, 1, 0, 0, 0)
SHA_LINE = re.compile(r"([a-f0-9]{64})  ([A-Za-z0-9_./-]+)\Z")
FROZEN_PYPROJECT = "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
FROZEN_UV_LOCK = "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"


class ExactHeadQualificationError(ValueError):
    """Fail closed; no publication authorization."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def duplicate_safe(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise ExactHeadQualificationError("ambiguous JSON object")
        result[name] = value
    return result


def json_map(data: bytes) -> dict[str, object]:
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=duplicate_safe)
    except (ValueError, UnicodeError) as exc:
        raise ExactHeadQualificationError("invalid JSON document") from exc
    if not isinstance(result, dict):
        raise ExactHeadQualificationError("JSON object required")
    return result


def manifest_contract() -> dict[str, object]:
    return {
        "schema": "MEDORIGIN_UNPUBLISHED_QA_EXACT_HEAD_V2",
        "project": "MedOrigin",
        "distribution": "medscale",
        "version": "0.3.0",
        "core_source_git_commit": SOURCE_SHA,
        "example_source_git_commit": SOURCE_SHA,
        "artifacts_sha256": PINNED,
        "qualified_full_ci_run": 40122889319,
        "qualified_codeql_run": 40122891353,
        "qualified_core_projection_run": 40122893490,
        "qualified_two_os_rehearsal_run": 40122803802,
        "independent_security_review_completed": False,
        "adr_0044_accepted": False,
        "publication_authorized": False,
        "protected_main_merged": False,
        "signed_desktop_installer_present": False,
        "clinical_use_authorized": False,
    }


def check_provenance(raw: bytes) -> None:
    receipt = json_map(raw)
    if (
        receipt.get("source_git_commit") != SOURCE_SHA
        or receipt.get("publication_authorized") is not False
        or receipt.get("frozen_pyproject_sha256") != FROZEN_PYPROJECT
        or receipt.get("frozen_lock_sha256") != FROZEN_UV_LOCK
    ):
        raise ExactHeadQualificationError("Core source provenance or frozen inputs differ")


def check_members(files: dict[str, bytes]) -> dict[str, object]:
    if set(files) != MEMBERS or sum(len(v) for v in files.values()) > MAX_ZIP:
        raise ExactHeadQualificationError("missing/extra members or content exceeds budget")
    if any(len(data) > MAX_FILE for data in files.values()):
        raise ExactHeadQualificationError("member too large")
    try:
        sumlines = files[CHECKSUMS].decode("ascii").splitlines()
    except UnicodeError as exc:
        raise ExactHeadQualificationError("checksum file not ASCII") from exc
    if len(sumlines) != len(MEMBERS) - 1:
        raise ExactHeadQualificationError("checksum count differs")
    actual: dict[str, str] = {}
    for line in sumlines:
        match = SHA_LINE.fullmatch(line)
        if match is None:
            raise ExactHeadQualificationError("checksum format invalid")
        hexsum, name = match.groups()
        if name in actual or name not in MEMBERS or name == CHECKSUMS:
            raise ExactHeadQualificationError("duplicated or unexpected checksum")
        actual[name] = hexsum
    if set(actual) != MEMBERS - {CHECKSUMS}:
        raise ExactHeadQualificationError("checksum coverage incomplete")
    for name, expected in actual.items():
        if sha(files[name]) != expected:
            raise ExactHeadQualificationError("checksum mismatch")
    # The member checksum list is attacker-editable together with the ZIP.
    # Pin the expected source and provenance against independent local constants.
    if set(SOURCE_MEMBER_SHA256) != MEMBERS - {CHECKSUMS}:
        raise ExactHeadQualificationError("source hash trust inventory incomplete")
    for name, expected in SOURCE_MEMBER_SHA256.items():
        if sha(files[name]) != expected:
            raise ExactHeadQualificationError("independently pinned source member differs")
    manifest = json_map(files[MANIFEST])
    contract = manifest_contract()
    if manifest != contract or any(type(manifest[k]) is not type(v) for k, v in contract.items()):
        raise ExactHeadQualificationError("manifest does not match unpublished exact-head contract")
    for name, expected in PINNED.items():
        if actual[f"artifacts/{name}"] != expected:
            raise ExactHeadQualificationError("unqualified Core artifact hash")
    check_provenance(files[PROVENANCE])
    return {
        "status": "MEDORIGIN_EXACT_HEAD_UNPUBLISHED_QA_PASS",
        "source_git_commit": SOURCE_SHA,
        "member_count": len(files),
        "wheel_sha256": PINNED[WHEEL],
        "sdist_sha256": PINNED[SDIST],
        "publication_authorized": False,
        "independent_review_completed": False,
        "signed": False,
    }


def read_zip(path: Path) -> dict[str, bytes]:
    if path.is_symlink() or path.stat().st_size > MAX_ZIP:
        raise ExactHeadQualificationError("oversized or linked archive")
    files: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                name = info.filename
                kind = stat.S_IFMT(info.external_attr >> 16)
                if (
                    info.is_dir()
                    or name not in MEMBERS
                    or name in files
                    or "\\" in name
                    or ":" in name
                    or ".." in name.split("/")
                    or kind not in {0, stat.S_IFREG}
                    or info.flag_bits & 1
                    or info.file_size > MAX_FILE
                ):
                    raise ExactHeadQualificationError("unsafe, duplicate or unexpected member")
                files[name] = archive.read(info)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise ExactHeadQualificationError("corrupt archive") from exc
    return files


def read_pinned(path: Path, expected: str) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ExactHeadQualificationError("missing, linked or oversized source input")
    content = path.read_bytes()
    if sha(content) != expected:
        raise ExactHeadQualificationError("source-bound input bytes differ")
    return content


def git(*args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(SOURCE_ROOT), *args],
        check=False,
        capture_output=True,
        timeout=30,
    )
    if result.returncode or len(result.stdout) > MAX_FILE:
        raise ExactHeadQualificationError("pinned Git source inaccessible")
    return result.stdout


def construct(artifacts: Path, provenance_file: Path) -> dict[str, bytes]:
    # The source is read solely from the immutable audited Git revision;
    # this script may be committed on a later tool-only stacked PR.
    if git("status", "--porcelain"):
        raise ExactHeadQualificationError("Git checkout is not clean")
    if git("rev-parse", "--verify", SOURCE_SHA).decode().strip() != SOURCE_SHA:
        raise ExactHeadQualificationError("qualified release source is not available locally")
    wheel = read_pinned(artifacts / WHEEL, PINNED[WHEEL])
    sdist = read_pinned(artifacts / SDIST, PINNED[SDIST])
    if provenance_file.is_symlink() or not provenance_file.is_file():
        raise ExactHeadQualificationError("staging provenance missing")
    if provenance_file.stat().st_size > MAX_FILE:
        raise ExactHeadQualificationError("staging provenance oversized")
    provenance = provenance_file.read_bytes()
    check_provenance(provenance)
    files: dict[str, bytes] = {
        f"artifacts/{WHEEL}": wheel,
        f"artifacts/{SDIST}": sdist,
        PROVENANCE: provenance,
    }
    for name in EXAMPLES:
        files[EXAMPLE_ROOT + name] = git("show", f"{SOURCE_SHA}:{EXAMPLE_ROOT}{name}")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        files[name] = git("show", f"{SOURCE_SHA}:{name}")
    files[README] = (
        "# MedOrigin v0.3.0 — unpublished exact-source Developer Beta QA\n\n"
        "Core Wheel, Core sdist, provenance, license and synthetic examples all\n"
        "come from the same committed source identity: " + SOURCE_SHA + ".\n"
        "The Python distribution and CLI intentionally remain named medscale.\n"
        "The Tkinter desktop example is separate source, not a signed installer.\n"
        "Verify the ZIP against an externally trusted SHA-256 before use.\n"
        "Only local synthetic FHIR validation has been qualified for this beta.\n"
        "Optional external validator mode and historic v0.2.0 persisted-data\n"
        "migration/compatibility are not supported. Do not use real patient data.\n"
        "Independent #603 review and ADR decision #574 remain open.\n"
        "Not released or authorized for tag, publishing, clinical deployment,\n"
        "protected main merge, hosted models, or other public distribution.\n"
    ).encode("utf-8")
    files[MANIFEST] = (json.dumps(manifest_contract(), sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    files[CHECKSUMS] = (
        "\n".join(f"{sha(files[name])}  {name}" for name in sorted(files)) + "\n"
    ).encode("ascii")
    check_members(files)
    return files


def build(out: Path, artifacts: Path, provenance_file: Path) -> dict[str, object]:
    if out.name != ZIP_NAME or not out.parent.is_dir() or out.exists():
        raise ExactHeadQualificationError("refusing noncanonical or existing output")
    files = construct(artifacts, provenance_file)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w") as archive:
        for name in sorted(files):
            item = zipfile.ZipInfo(name, STAMP)
            item.create_system = 3
            item.external_attr = (stat.S_IFREG | 0o644) << 16
            item.compress_type = zipfile.ZIP_STORED
            archive.writestr(item, files[name])
    blob = mem.getvalue()
    if len(blob) > MAX_ZIP:
        raise ExactHeadQualificationError("ZIP exceeds size budget")
    with out.open("xb") as stream:
        stream.write(blob)
    checked = verify(out, sha(blob))
    return {**checked, "zip_sha256": sha(blob)}


def verify(path: Path, trusted_sha256: str | None = None) -> dict[str, object]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ZIP:
        raise ExactHeadQualificationError("unsafe or oversized ZIP")
    if trusted_sha256 is not None:
        if re.fullmatch(r"[0-9a-f]{64}", trusted_sha256) is None:
            raise ExactHeadQualificationError("trusted ZIP hash malformed")
        if sha(path.read_bytes()) != trusted_sha256:
            raise ExactHeadQualificationError("ZIP hash does not match external expectation")
    return check_members(read_zip(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["build", "verify"])
    parser.add_argument("zip", type=Path)
    parser.add_argument("--expected-sha256", default=None)
    parser.add_argument(
        "--artifacts", type=Path, help="Existing qualified offline Core artifact directory"
    )
    parser.add_argument("--provenance", type=Path, help="Existing source-bound projection JSON")
    args = parser.parse_args(argv)
    try:
        if args.operation == "build":
            if args.artifacts is None or args.provenance is None:
                raise ExactHeadQualificationError("build requires --artifacts and --provenance")
            result = build(args.zip, args.artifacts, args.provenance)
        else:
            result = verify(args.zip, args.expected_sha256)
    except (ExactHeadQualificationError, OSError, ValueError, subprocess.TimeoutExpired):
        print("MEDORIGIN_EXACT_HEAD_QA_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
