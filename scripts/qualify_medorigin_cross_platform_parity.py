"""Nonpublishing cross-platform comparison of source-qualified Core-only artifacts.

Each platform builds the ADR-0045 *proposal* in isolated temporary storage,
runs both independent source and publication-scope verifiers, then records
payload digests separately from platform-dependent container headers.
No source edits, artifact repacking, registry uploads, tags or approvals.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

SCHEMA = "MEDORIGIN_CORE_PARITY_REVIEW_V1"
HEX = re.compile(r"[0-9a-f]{64}\Z")
EXPECTED = {"wheel": 255, "sdist": 258}
EXPECTED_FILES = {
    "wheel": "medscale-0.3.0-py3-none-any.whl",
    "sdist": "medscale-0.3.0.tar.gz",
}


class ParityError(ValueError):
    """Untrusted or mismatched content cannot be declared equivalent."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inventory(name: str, path: Path, members: dict[str, bytes]) -> dict[str, Any]:
    if len(members) != EXPECTED[name]:
        raise ParityError(f"{name}: incorrect member count")
    record: dict[str, Any] = {
        "archive_sha256": digest(path.read_bytes()),
        "member_count": len(members),
        "members": {key: digest(val) for key, val in sorted(members.items())},
    }
    if name == "wheel":
        with zipfile.ZipFile(path) as archive:
            record["zip_creator_systems"] = sorted(
                {entry.create_system for entry in archive.infolist()}
            )
    return record


SYNTHETIC_REPORT_SHA256 = "991d319d9c567db3a71985661a12abb67c8432ff43b439c08759f8ee1d52fbd9"


def _offline_command(args: list[str], repo: Path) -> None:
    """No shell, no package-index access, and no trust in tool stderr."""
    env = dict(os.environ)
    env["UV_OFFLINE"] = "1"
    env["UV_NO_PROGRESS"] = "1"
    try:
        proc = subprocess.run(
            args,
            cwd=repo,
            env=env,
            capture_output=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ParityError("offline runtime qualification command unavailable") from exc
    if proc.returncode:
        raise ParityError("offline runtime qualification command rejected")


def _verify_synthetic_evidence(path: Path) -> None:
    """Check the same real installed-CLI FHIR evidence contract on each host."""
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ParityError("missing or malformed installed synthetic evidence") from exc
    if (
        not isinstance(receipt, dict)
        or not isinstance(receipt.get("runs"), list)
        or len(receipt["runs"]) != 2
        or any(
            not isinstance(row, dict)
            or row.get("report_sha256") != SYNTHETIC_REPORT_SHA256
            or row.get("structural_status") != "valid"
            or type(row.get("malformed_exit")) is not int
            or row["malformed_exit"] != 1
            for row in receipt["runs"]
        )
    ):
        raise ParityError("installed synthetic FHIR identity or refusal drift")


def _verify_offline_install(repo: Path, wheel: Path, scratch: Path) -> dict[str, Any]:
    """Exercise two clean interpreter installs of exactly the verified Wheel."""
    from qualify_medorigin_developer_beta import installed_wheel_matches

    venvs: dict[int, Path] = {}
    scripts: dict[int, Path] = {}
    for minor in (11, 12):
        venv = scratch / f"python3{minor}"
        _offline_command(["uv", "venv", "--python", f"3.{minor}", str(venv)], repo)
        bin_path = venv / ("Scripts" if os.name == "nt" else "bin")
        python = bin_path / ("python.exe" if os.name == "nt" else "python")
        cli = bin_path / ("medscale.exe" if os.name == "nt" else "medscale")
        _offline_command(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--no-index",
                "--no-deps",
                str(wheel),
            ],
            repo,
        )
        if not cli.is_file():
            raise ParityError("installed Core CLI missing")
        count = installed_wheel_matches(wheel, python, minor)
        if count < 50:
            raise ParityError("incomplete installed Core source inventory")
        venvs[minor] = python
        scripts[minor] = cli
        if minor == 11:
            expected_count = count
        elif count != expected_count:
            raise ParityError("installed 3.11/3.12 source inventories diverged")
    evidence = scratch / "synthetic-fhir"
    _offline_command(
        [
            str(venvs[12]),
            str(repo / "examples" / "synthetic_fhir_developer_beta" / "reproduce.py"),
            "--cli",
            str(scripts[11]),
            "--alt-cli",
            str(scripts[12]),
            "--out",
            str(evidence),
        ],
        repo,
    )
    _verify_synthetic_evidence(evidence / "evidence.json")
    return {
        "installed_python_versions": ["3.11", "3.12"],
        "installed_python_source_count": expected_count,
        "synthetic_report_sha256": SYNTHETIC_REPORT_SHA256,
    }


def build_manifest(repo: Path) -> dict[str, Any]:
    # These imports intentionally happen only in build mode. The compare mode
    # remains standard-library-only and cannot build or publish anything.
    from check_base_core_publication_scope import inspect

    # Build backend exists only in the isolated packaging environment, not static CI.
    backend = importlib.import_module("hatchling.build")
    from stage_medorigin_base_only_proposal import propose
    from verify_medorigin_base_only_proposal import load_sdist, load_wheel, verify

    if Path.cwd().resolve() != repo.resolve():
        raise ParityError("run from the checked-out repository root")
    with tempfile.TemporaryDirectory(prefix="medorigin-parity-review-") as temp:
        root = Path(temp)
        stage = root / "staged"
        dist = root / "dist"
        proposed = propose(stage)
        if proposed["publication_authorized"] is not False:
            raise ParityError("proposal unexpectedly authorized publication")
        dist.mkdir()
        previous = Path.cwd()
        try:
            os.chdir(stage)
            wheel_name = backend.build_wheel(str(dist))
            sdist_name = backend.build_sdist(str(dist))
        finally:
            os.chdir(previous)
        if (wheel_name, sdist_name) != (EXPECTED_FILES["wheel"], EXPECTED_FILES["sdist"]):
            raise ParityError("unexpected artifact filenames")
        source_receipt = verify(repo, dist)
        admission = inspect(dist)
        if (
            source_receipt["status"] != "BASE_ONLY_PROPOSAL_SOURCE_BOUND_VERIFIED"
            or source_receipt["publication_authorized"] is not False
            or source_receipt["adr_0045_accepted"] is not False
            or admission["status"] != "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
            or admission["issues"]
            or admission["publication_authorized"] is not False
        ):
            raise ParityError("artifact source-bound or metadata verification failed")
        records = {
            "wheel": _inventory("wheel", dist / wheel_name, load_wheel(dist / wheel_name)),
            "sdist": _inventory("sdist", dist / sdist_name, load_sdist(dist / sdist_name)),
        }
        installed = _verify_offline_install(repo, dist / wheel_name, root)
        return {
            **installed,
            "schema": SCHEMA,
            "source_git_commit": source_receipt["source_git_commit"],
            "platform": platform.system().lower(),
            "build_backend": "hatchling==1.32.4",
            "publication_authorized": False,
            "adr_0045_accepted": False,
            "source_bound_verified": True,
            "archives": records,
        }


def _validate(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != {
        "schema",
        "source_git_commit",
        "platform",
        "build_backend",
        "publication_authorized",
        "adr_0045_accepted",
        "source_bound_verified",
        "installed_python_versions",
        "installed_python_source_count",
        "synthetic_report_sha256",
        "archives",
    }:
        raise ParityError("malformed evidence schema")
    if (
        record["schema"] != SCHEMA
        or not isinstance(record["source_git_commit"], str)
        or not re.fullmatch(r"[0-9a-f]{40}", record["source_git_commit"])
        or record["platform"] not in ("windows", "linux", "darwin")
        or record["build_backend"] != "hatchling==1.32.4"
        or record["publication_authorized"] is not False
        or record["adr_0045_accepted"] is not False
        or record["source_bound_verified"] is not True
        or record["installed_python_versions"] != ["3.11", "3.12"]
        or type(record["installed_python_source_count"]) is not int
        or record["installed_python_source_count"] < 50
        or record["synthetic_report_sha256"] != SYNTHETIC_REPORT_SHA256
    ):
        raise ParityError("unqualified cross-platform evidence")
    archives = record["archives"]
    if not isinstance(archives, dict) or set(archives) != set(EXPECTED):
        raise ParityError("missing or additional archive")
    for kind, expected_count in EXPECTED.items():
        archive = archives[kind]
        required = {"archive_sha256", "member_count", "members"}
        if kind == "wheel":
            required.add("zip_creator_systems")
        if not isinstance(archive, dict) or set(archive) != required:
            raise ParityError(f"{kind}: malformed archive inventory")
        if (
            not isinstance(archive["archive_sha256"], str)
            or not HEX.fullmatch(archive["archive_sha256"])
            or type(archive["member_count"]) is not int
            or archive["member_count"] != expected_count
            or not isinstance(archive["members"], dict)
            or len(archive["members"]) != expected_count
            or any(
                not isinstance(path, str)
                or not path
                or not isinstance(value, str)
                or not HEX.fullmatch(value)
                for path, value in archive["members"].items()
            )
        ):
            raise ParityError(f"{kind}: unqualified content digest")
        if kind == "wheel" and (
            not isinstance(archive["zip_creator_systems"], list)
            or not archive["zip_creator_systems"]
            or any(
                type(value) is not int or value not in range(0, 4)
                for value in archive["zip_creator_systems"]
            )
        ):
            raise ParityError("wheel: missing ZIP creator evidence")
    return record


def compare(left: Any, right: Any) -> dict[str, Any]:
    a, b = _validate(left), _validate(right)
    if a["platform"] == b["platform"]:
        raise ParityError("need independent host operating systems")
    if a["source_git_commit"] != b["source_git_commit"]:
        raise ParityError("cannot compare artifacts from different Git commits")
    if a["installed_python_source_count"] != b["installed_python_source_count"]:
        raise ParityError("installed Python source inventory counts differ across hosts")
    archives: dict[str, Any] = {}
    for kind in EXPECTED:
        first, second = a["archives"][kind], b["archives"][kind]
        if first["members"] != second["members"]:
            differing = sorted(
                k
                for k in set(first["members"]) | set(second["members"])
                if first["members"].get(k) != second["members"].get(k)
            )
            raise ParityError(f"{kind}: member bytes differ: {differing[:5]}")
        archives[kind] = {
            "members_byte_identical": True,
            "member_count": first["member_count"],
            "whole_archive_byte_identical": (first["archive_sha256"] == second["archive_sha256"]),
            "archive_sha256_by_platform": {
                a["platform"]: first["archive_sha256"],
                b["platform"]: second["archive_sha256"],
            },
        }
    all_archive_identical = all(item["whole_archive_byte_identical"] for item in archives.values())
    return {
        "status": (
            "CONTENT_AND_ARCHIVE_PARITY_VERIFIED"
            if all_archive_identical
            else "CONTENT_PARITY_VERIFIED_ARCHIVE_HEADERS_DIFFER"
        ),
        "source_git_commit": a["source_git_commit"],
        "platforms": sorted((a["platform"], b["platform"])),
        "offline_installed_python_versions": a["installed_python_versions"],
        "offline_installed_source_count": a["installed_python_source_count"],
        "synthetic_report_sha256": SYNTHETIC_REPORT_SHA256,
        "archives": archives,
        "publication_authorized": False,
        "adr_0045_accepted": False,
        "independent_security_review_completed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--output", type=Path, required=True)
    compare_command = commands.add_parser("compare")
    compare_command.add_argument("--left", type=Path, required=True)
    compare_command.add_argument("--right", type=Path, required=True)
    compare_command.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build_manifest(Path(__file__).resolve().parents[1])
            # Exclusive creation: no overwrite of prior audit evidence.
            with args.output.open("x", encoding="utf-8", newline="\n") as output:
                json.dump(result, output, sort_keys=True, indent=2)
                output.write("\n")
        else:
            result = compare(
                json.loads(args.left.read_text(encoding="utf-8")),
                json.loads(args.right.read_text(encoding="utf-8")),
            )
            if args.output is not None:
                with args.output.open("x", encoding="utf-8", newline="\n") as output:
                    json.dump(result, output, sort_keys=True, indent=2)
                    output.write("\n")
        if args.command == "build":
            summary = {
                "status": "SOURCE_BOUND_ARTIFACT_MANIFEST_VERIFIED",
                "source_git_commit": result["source_git_commit"],
                "platform": result["platform"],
                "member_counts": {
                    name: entry["member_count"] for name, entry in result["archives"].items()
                },
                "archive_sha256": {
                    name: entry["archive_sha256"] for name, entry in result["archives"].items()
                },
                "publication_authorized": False,
            }
            print(json.dumps(summary, sort_keys=True))
        else:
            print(json.dumps(result, sort_keys=True))
    except (ParityError, OSError, ValueError, KeyError, RuntimeError) as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": str(exc),
                    "publication_authorized": False,
                }
            )
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
