"""Reproducible, synthetic-only Python SHA-256 reference measurement for Desktop D0.

This is a local microbenchmark, NOT a Rust parity result, peak-RSS measure,
full FHIR benchmark, medical-device evaluation, or release permission.
It reads only the checked-in D0 vector manifest and source-bound fixture code.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from types import ModuleType
from typing import cast

_ROOT = Path(__file__).resolve().parents[1]
_REFERENCE = _ROOT / "scripts" / "check_desktop_d0_vectors.py"
_SCHEMA = "medorigin-desktop-d0-python-sha256-benchmark-v1"


def _load_reference() -> ModuleType:
    spec = importlib.util.spec_from_file_location("medorigin_d0_reference", _REFERENCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("synthetic reference source is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _measure(raw: bytes, expected_sha256: str, iterations: int) -> dict[str, int | str]:
    """Measure full SHA-256 digest latency and Python heap allocation separately."""
    for _ in range(16):
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("raw SHA-256 reference mismatch")
    duration_ns: list[int] = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        digest = hashlib.sha256(raw).hexdigest()
        duration_ns.append(time.perf_counter_ns() - start)
        if digest != expected_sha256:
            raise ValueError("raw SHA-256 reference mismatch")
    ordered = sorted(duration_ns)
    p95 = ordered[max(0, math.ceil(iterations * 0.95) - 1)]
    tracemalloc.start()
    try:
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("raw SHA-256 reference mismatch")
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {
        "bytes": len(raw),
        "sha256": expected_sha256,
        "iterations": iterations,
        "median_latency_ns": int(statistics.median(ordered)),
        "p95_latency_ns": p95,
        "tracemalloc_peak_bytes": peak,
    }


def measure_reference(iterations: int = 256) -> dict[str, object]:
    """Verify the source-bound fixture manifest before measuring raw hashes."""
    if not 1 <= iterations <= 10_000:
        raise ValueError("iterations must be between 1 and 10000")
    source = _load_reference()
    manifest = cast(dict[str, object], source.verify_manifest())
    cases = cast(dict[str, bytes], source.case_bytes())
    vectors = manifest.get("vectors")
    if not isinstance(vectors, list):
        raise ValueError("source-bound manifest vectors missing")
    measured: list[dict[str, int | str]] = []
    for entry in vectors:
        if not isinstance(entry, dict):
            raise ValueError("invalid source-bound vector")
        fixture_id, digest = entry.get("id"), entry.get("sha256")
        if not isinstance(fixture_id, str) or not isinstance(digest, str):
            raise ValueError("invalid fixture identity")
        if fixture_id not in cases:
            raise ValueError("fixture not allowlisted")
        result = _measure(cases[fixture_id], digest, iterations)
        result["id"] = fixture_id
        measured.append(result)
    return {
        "schema": _SCHEMA,
        "qualification": "PYTHON_REFERENCE_ONLY",
        "rust_parity_qualified": False,
        "publication_authorized": False,
        "version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "platform": platform.system().lower(),
        "latency_clock": "perf_counter_ns",
        "memory_measure": "tracemalloc_peak_bytes_not_RSS",
        "cases": measured,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=256)
    args = parser.parse_args(argv)
    try:
        result = measure_reference(iterations=args.iterations)
    except (OSError, UnicodeError, ValueError, RuntimeError) as error:
        print(f"DESKTOP_D0_BASELINE_BLOCKED: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
