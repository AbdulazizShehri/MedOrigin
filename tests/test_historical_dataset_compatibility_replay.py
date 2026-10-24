"""A passing replay means known incompatibility was reproduced, NOT compatibility."""

from __future__ import annotations

import copy
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
_adjudicate = runpy.run_path(str(ROOT / "scripts/audit_historical_dataset_compatibility.py"))[
    "evaluate_replay"
]
evaluate_replay = cast(Callable[[dict[str, Any]], list[str]], _adjudicate)
OLD = "d2e651a55c92f2218aca49acaa5b7bd18a75f096"
DUMMY_A = "a" * 64
DUMMY_B = "b" * 64


def _case(*, historical: bool) -> dict[str, Any]:
    return {
        "manifest_exit": 0,
        "freeze": {"exit": 1 if historical else 0},
        "validations": {
            "v0.2.0": {"exit": 1},
            "candidate": {"exit": 1 if historical else 0},
        },
        "manifest_sha256": DUMMY_A,
        "recorded_manifest_sha256": DUMMY_B if historical else DUMMY_A,
        "manifest_checksum_matches": not historical,
        "writer_guards": {
            name: {"exit": 2, "all_artifact_bytes_preserved": True}
            for name in ("freeze", "manifest-write", "init-write")
        },
    }


def _receipt() -> dict[str, Any]:
    return {
        "baseline": OLD,
        "candidate": "c" * 40,
        "synthetic_only": True,
        "publication_authorized": False,
        "cases": {"v0.2.0": _case(historical=True), "candidate": _case(historical=False)},
    }


def test_known_negative_compatibility_matrix_is_qualified_not_released() -> None:
    report = _receipt()
    assert evaluate_replay(report) == []
    assert report["publication_authorized"] is False


@pytest.mark.parametrize(
    ("case", "field", "value", "diagnostic"),
    [
        ("v0.2.0", "freeze", {"exit": 0}, "freeze exit"),
        ("candidate", "freeze", {"exit": 1}, "freeze exit"),
        ("v0.2.0", "manifest_exit", 2, "manifest creation"),
        ("v0.2.0", "manifest_checksum_matches", True, "checksum"),
        ("candidate", "manifest_checksum_matches", False, "checksum"),
        ("candidate", "recorded_manifest_sha256", DUMMY_B, "checksum"),
        ("candidate", "writer_guards", {}, "immutable-writer"),
        ("candidate", "validations", {}, "validator"),
    ],
)
def test_known_matrix_drifts_cannot_silently_pass(
    case: str, field: str, value: object, diagnostic: str
) -> None:
    report = _receipt()
    report["cases"][case][field] = value
    assert any(diagnostic in issue for issue in evaluate_replay(report))


def test_historical_validators_suddenly_accepting_other_format_is_detected() -> None:
    report = _receipt()
    report["cases"]["candidate"]["validations"]["v0.2.0"]["exit"] = 0
    assert any("validator" in issue for issue in evaluate_replay(report))
    report = _receipt()
    report["cases"]["v0.2.0"]["validations"]["candidate"]["exit"] = 0
    assert any("validator" in issue for issue in evaluate_replay(report))


@pytest.mark.parametrize("operation", ["freeze", "manifest-write", "init-write"])
def test_any_writer_mutation_is_a_hard_failure(operation: str) -> None:
    report = _receipt()
    report["cases"]["v0.2.0"]["writer_guards"][operation]["all_artifact_bytes_preserved"] = False
    assert any(operation in issue for issue in evaluate_replay(report))


def test_unexpected_writer_success_is_not_qualified() -> None:
    report = _receipt()
    report["cases"]["candidate"]["writer_guards"]["manifest-write"]["exit"] = 0
    assert any("manifest-write" in issue for issue in evaluate_replay(report))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("baseline", "f" * 40),
        ("candidate", "malformed"),
        ("synthetic_only", False),
        ("publication_authorized", True),
    ],
)
def test_bad_identity_or_evidence_scope_is_blocked(field: str, value: object) -> None:
    report = copy.deepcopy(_receipt())
    report[field] = value
    assert evaluate_replay(report)


def test_ci_replays_historical_format_on_supported_interpreters() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    static = ci.split("  static:\n", maxsplit=1)[1].split("  pytest-shard:\n", maxsplit=1)[0]
    assert 'python-version: ["3.11", "3.12"]' in static
    assert "fetch-depth: 0" in static
    assert "ref: ${{ github.event.pull_request.head.sha || github.sha }}" in static
    assert "Historical synthetic dataset format replay (read-only)" in static
    assert "scripts/audit_historical_dataset_compatibility.py" in static
    assert "--repo ." in static
    assert "${{ runner.temp }}/medorigin-history-${{ matrix.python-version }}.json" in static
    assert "uv run --no-sync python" in static


def test_missing_or_malformed_cases_cannot_count_as_a_pass() -> None:
    report = _receipt()
    report["cases"].pop("v0.2.0")
    assert evaluate_replay(report)
    report = _receipt()
    report["cases"]["candidate"] = None
    assert evaluate_replay(report)
