"""Offline regression tests for known patched Python lock advisory floors."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts/verify_python_lock_security_floor.py"
spec = importlib.util.spec_from_file_location("verify_python_lock_security_floor", MODULE)
assert spec is not None and spec.loader is not None
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def manifest(version: str = "13.0.0") -> dict:
    return {
        "project": {
            "optional-dependencies": {
                "rq1-runtime-feasibility": [f"pillow=={version}", "torch==2.13.0"]
            }
        }
    }


def valid_lock() -> dict:
    return {
        "package": [
            {"name": name, "version": minimum} for name, minimum in checker.PATCH_FLOORS.items()
        ]
    }


def test_every_reviewed_fixed_advisory_floor_passes_offline() -> None:
    assert checker.verify_lock(valid_lock(), manifest()) == []


@pytest.mark.parametrize("package", sorted(checker.PATCH_FLOORS))
def test_lower_version_of_each_package_is_refused(package: str) -> None:
    lock = valid_lock()
    target = next(row for row in lock["package"] if row["name"] == package)
    target["version"] = "0.0.1"
    assert any(package in item for item in checker.verify_lock(lock, manifest()))


def test_all_platform_markers_must_use_patched_versions() -> None:
    lock = valid_lock()
    lock["package"].append(
        {"name": "pillow", "version": "12.3.0", "resolution-markers": ["sys_platform == 'win32'"]}
    )
    assert any("pillow 12.3.0" in item for item in checker.verify_lock(lock, manifest()))


def test_runtime_manifest_pin_cannot_reintroduce_old_pillow() -> None:
    assert any(
        "Pillow runtime manifest" in item
        for item in checker.verify_lock(valid_lock(), manifest("12.3.0"))
    )


@pytest.mark.parametrize("broken", ["13.0.0rc1", "13.0.0+local", "not-a-version", ""])
def test_unreviewed_versions_fail_closed(broken: str) -> None:
    lock = valid_lock()
    lock["package"][0]["version"] = broken
    assert checker.verify_lock(lock, manifest())


def test_missing_or_malformed_reviewed_dependency_fails_closed() -> None:
    rows = valid_lock()
    rows["package"].pop()
    assert checker.verify_lock(rows, manifest())
    assert checker.verify_lock({"package": {}}, manifest())


def test_patched_numeric_version_has_unambiguous_comparison() -> None:
    assert checker.patched_at_least("13.0", "13.0.0")
    assert checker.patched_at_least("13.0.1", "13.0.0")
    assert not checker.patched_at_least("12.99.999", "13.0.0")
