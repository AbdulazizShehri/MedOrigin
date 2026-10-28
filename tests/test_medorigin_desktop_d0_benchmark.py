"""Offline, synthetic-only reference SHA-256 latency contract tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "benchmark_desktop_d0_sha256.py"


@pytest.fixture
def benchmark() -> ModuleType:
    spec = importlib.util.spec_from_file_location("medorigin_d0_benchmark", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_python_baseline_is_explicitly_not_rust_or_release(benchmark: ModuleType) -> None:
    result = benchmark.measure_reference(iterations=3)
    assert result["schema"] == "medorigin-desktop-d0-python-sha256-benchmark-v1"
    assert result["qualification"] == "PYTHON_REFERENCE_ONLY"
    assert result["source_commit"] == "dd84bb7b4177fbc169a04370772610ec66fa41df"
    manifest_sha256 = result["source_manifest_sha256"]
    assert isinstance(manifest_sha256, str) and len(manifest_sha256) == 64
    assert result["rust_parity_qualified"] is False
    assert result["publication_authorized"] is False
    assert result["memory_measure"] == "tracemalloc_peak_bytes_not_RSS"
    cases = result["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 4
    assert {case["id"] for case in cases} == {
        "patient-minimal",
        "patient-invalid-utf8",
        "patient-over-limit",
        "patient-exact-limit",
    }
    for case in cases:
        assert case["iterations"] == 3
        assert case["median_latency_ns"] >= 0
        assert case["p95_latency_ns"] >= case["median_latency_ns"]
        assert case["tracemalloc_peak_bytes"] >= 0
        assert len(case["sha256"]) == 64


@pytest.mark.parametrize("iterations", [-1, 0, 10_001])
def test_bounded_iterations_fail_closed(benchmark: ModuleType, iterations: int) -> None:
    with pytest.raises(ValueError, match="iterations"):
        benchmark.measure_reference(iterations=iterations)


def test_cli_never_writes_a_measurement_file(tmp_path: Path) -> None:
    output = subprocess.run(
        [sys.executable, str(_SCRIPT), "--iterations", "3"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert output.returncode == 0, output.stderr
    payload = json.loads(output.stdout)
    assert payload["qualification"] == "PYTHON_REFERENCE_ONLY"
    assert payload["rust_parity_qualified"] is False
    assert list(tmp_path.iterdir()) == []


def test_cli_rejects_invalid_benchmark_size(benchmark: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    assert benchmark.main(["--iterations", "0"]) == 2
    assert "DESKTOP_D0_BASELINE_BLOCKED" in capsys.readouterr().err
