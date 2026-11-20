#!/usr/bin/env python3
"""Reject known fixed-version regressions in the offline Python lock.

Scoped to exact current GH Dependabot minimum patches, 2026-11-05.
This is NOT a vulnerability scanner and does NOT attest production release.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

# Minimum versions for distinct packages in open GH Dependabot advisories
# with an available fix on 2026-11-05. Accelerate and diskcache have no
# published fixed version in the currently retrieved advisories.
PATCH_FLOORS: dict[str, str] = {
    "pillow": "13.0.0",
    "filelock": "4.2.1",
    "aiohttp": "3.14.4",
    "multidict": "6.9.1",
    "urllib3": "2.8.0",
    "certifi": "2026.10.18",
    "setuptools": "84.1.0",
}
SIMPLE_VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+)*$")


def version_tuple(value: str) -> tuple[int, ...]:
    """Fail closed on prerelease, opaque, malformed or unparseable versions."""
    if SIMPLE_VERSION.fullmatch(value) is None:
        raise ValueError("Unreviewed version syntax")
    return tuple(int(part) for part in value.split("."))


def patched_at_least(actual: str, minimum: str) -> bool:
    left, right = version_tuple(actual), version_tuple(minimum)
    padded = max(len(left), len(right))
    return left + (0,) * (padded - len(left)) >= right + (0,) * (padded - len(right))


def verify_lock(lock: dict, pyproject: dict) -> list[str]:
    violations: list[str] = []
    rows = lock.get("package")
    if not isinstance(rows, list):
        return ["Missing or malformed uv lock package table"]
    found: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            violations.append("Malformed lock package record")
            continue
        name, version = row.get("name"), row.get("version")
        if not isinstance(name, str) or not name:
            violations.append("Lock record lacks package name")
            continue
        package = name.lower()
        # uv can represent local/workspace projects without a fixed registry
        # version. Only the seven reviewed external dependencies require one.
        if package not in PATCH_FLOORS:
            continue
        if not isinstance(version, str):
            violations.append(f"{package} lacks an immutable locked version")
            continue
        found.add(package)
        try:
            if not patched_at_least(version, PATCH_FLOORS[package]):
                violations.append(f"{package} {version} is below reviewed {PATCH_FLOORS[package]}")
        except ValueError:
            violations.append(f"{package} has an unreviewed version")
    for package in PATCH_FLOORS.keys() - found:
        violations.append(f"Expected reviewed dependency {package} missing from lock")

    optional = pyproject.get("project", {}).get("optional-dependencies", {})
    deps = optional.get("rq1-runtime-feasibility")
    if not isinstance(deps, list):
        violations.append("Missing reviewed rq1-runtime-feasibility dependency list")
    else:
        pillow = [
            value
            for value in deps
            if isinstance(value, str) and re.match(r"(?i)^pillow(?:[><=!~]|$)", value)
        ]
        if len(pillow) != 1:
            violations.append("Exactly one explicit Pillow runtime constraint required")
        else:
            match = re.fullmatch(r"(?i)pillow(?:==|>=)([0-9]+(?:\.[0-9]+)*)", pillow[0])
            if not match:
                violations.append("Pillow runtime constraint is unreviewed")
            else:
                try:
                    if not patched_at_least(match.group(1), PATCH_FLOORS["pillow"]):
                        violations.append("Pillow runtime manifest permits a vulnerable version")
                except ValueError:
                    violations.append("Pillow runtime constraint is not a supported version")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    root = args.root
    if not root.is_dir() or root.is_symlink():
        print("PYTHON_LOCK_SECURITY_FLOOR_REFUSED: invalid source root", file=sys.stderr)
        return 2
    try:
        with (root / "uv.lock").open("rb") as handle:
            lock = tomllib.load(handle)
        with (root / "pyproject.toml").open("rb") as handle:
            manifest = tomllib.load(handle)
        violations = verify_lock(lock, manifest)
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError):
        print("PYTHON_LOCK_SECURITY_FLOOR_REFUSED: lock or manifest unavailable", file=sys.stderr)
        return 2
    if violations:
        for violation in sorted(violations):
            print(f"PYTHON_LOCK_SECURITY_FLOOR_REFUSED: {violation}", file=sys.stderr)
        return 1
    print("PYTHON_LOCK_KNOWN_FIXED_ADVISORY_FLOORS_PASS_NONRELEASE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
