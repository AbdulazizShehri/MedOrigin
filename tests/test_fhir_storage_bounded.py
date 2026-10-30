"""Fail-closed synthetic report-artifact admission and storage regression tests.

The limit is a reversible developer-Beta proposal, not release approval.
No real patient data, external network, or package publication is involved.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from medscale.fhirkit import FhirStorageError, ValidationReport, report_hash, store_report
from medscale.fhirkit.storage import fhirkit_reports_dir, load_report

_REPORT_LIMIT = 8 * 1024 * 1024


def _existing_path(root: Path, report: ValidationReport) -> Path:
    target = fhirkit_reports_dir(root) / report_hash(report) / "report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


@pytest.mark.parametrize("operation", ["load", "store"])
def test_existing_oversized_report_is_rejected_before_full_read(
    tmp_path: Path, operation: str
) -> None:
    report = ValidationReport(status="valid")
    target = _existing_path(tmp_path, report)
    with target.open("wb") as stream:
        stream.truncate(_REPORT_LIMIT + 1)

    with pytest.raises(FhirStorageError, match="size limit"):
        if operation == "load":
            load_report(report_hash(report), root=tmp_path)
        else:
            store_report(report, root=tmp_path)
    assert target.stat().st_size == _REPORT_LIMIT + 1


def test_new_oversized_report_is_rejected_before_creating_artifact(tmp_path: Path) -> None:
    report = ValidationReport(status="invalid", errors=("X" * _REPORT_LIMIT,))
    target = fhirkit_reports_dir(tmp_path) / report_hash(report) / "report.json"

    with pytest.raises(FhirStorageError, match="size limit"):
        store_report(report, root=tmp_path)
    assert not target.exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO unavailable")
@pytest.mark.parametrize("operation", ["load", "store"])
def test_existing_fifo_is_rejected_without_blocking(
    tmp_path: Path, operation: str
) -> None:
    """A user-controlled FIFO must never stall report load or idempotent store."""
    report = ValidationReport(status="valid")
    target = _existing_path(tmp_path, report)
    os.mkfifo(target)
    code = (
        "import sys; "
        "from pathlib import Path; "
        "from medscale.fhirkit import ValidationReport, report_hash, store_report, FhirStorageError; "
        "from medscale.fhirkit.storage import load_report; "
        "root=Path(sys.argv[1]); op=sys.argv[2]; "
        "report=ValidationReport(status='valid'); "
        "exec('try:\\n"
        "    load_report(report_hash(report), root=root) if op == \\"load\\" "
        "else store_report(report, root=root)\\n"
        "except FhirStorageError:\\n    print(\\"REJECTED\\")\\n"
        "else:\\n    raise SystemExit(2)')"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), operation],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "REJECTED"
    assert target.is_fifo()


def test_small_canonical_report_remains_idempotent(tmp_path: Path) -> None:
    report = ValidationReport(status="valid")
    path = store_report(report, root=tmp_path)
    assert store_report(report, root=tmp_path) == path
    assert load_report(report_hash(report), root=tmp_path) == path.read_text(
        encoding="utf-8"
    )
