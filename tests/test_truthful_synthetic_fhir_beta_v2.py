"""Real v2 contract tests for truthful synthetic FHIR Developer Beta.

All input FHIR records are fictional and bundled. The Core CLI fake used in
the narrow unit test below is intentionally NOT a Wheel/provenance test.
Installed-Wheel Python3.11/3.12 E2E must run independently in hosted CI.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "synthetic_fhir_developer_beta"


def _module(filename: str, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(EXAMPLES))
    spec = importlib.util.spec_from_file_location("truthful_beta_" + filename, EXAMPLES / filename)
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def _report(good: dict[str, object], warning: str) -> dict[str, object]:
    h = hashlib.sha256(
        json.dumps(
            good, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "created_at": "2026-10-24T00:00:00Z",
        "errors": [],
        "format_version": "fhirkit-validation-report/v1",
        "input_hash": h,
        "report_id": "",
        "status": "not_validated",
        "validator_name": "medscale-fhirkit-local",
        "validator_version": "0.1.0",
        "warnings": [warning],
    }


def _sample_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, Any, dict[str, object], dict[str, object], Path]:
    reproduce = _module("reproduce.py", monkeypatch)
    preview = _module("preview.py", monkeypatch)
    fixture = json.loads(reproduce.GOOD.read_text(encoding="utf-8"))
    report = _report(fixture, reproduce.WARNING)
    rendered = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    report_file = tmp_path / "reports_run_1" / "fixed-fictional" / "report.json"
    report_file.parent.mkdir(parents=True)
    report_file.write_text(rendered, encoding="utf-8", newline="\n")
    source = reproduce.GOOD.read_bytes()
    row: dict[str, object] = {
        "label": "run_1",
        "installed_version": "medscale 0.3.0",
        "fixture_sha256": hashlib.sha256(source).hexdigest(),
        "report_sha256": hashlib.sha256(report_file.read_bytes()).hexdigest(),
        "report_path": report_file.relative_to(tmp_path).as_posix(),
        "provenance_status": "not_validated",
        "validation_exit": 2,
        "malformed_exit": 1,
    }
    receipt: dict[str, object] = {
        "schema": "medorigin-local-synthetic-fhir-example/v2",
        "scope": "fictional Core provenance only, not FHIR validation",
        "fhir_conformance_validated": False,
        "full_beta_preview_qualified": False,
        "publication_authorized": False,
        "clinical_authorized": False,
        "independent_review_completed": False,
        "runs": [row],
    }
    return reproduce, preview, row, receipt, report_file


def test_exact_fictional_report_renders_only_negative_truth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, preview, _, receipt, _ = _sample_receipt(tmp_path, monkeypatch)
    admitted = preview.admit_receipt(receipt, directory=tmp_path)
    rendered = preview.render(admitted)
    assert "<h1>Local FHIR provenance reproduced. Not validated.</h1>" in rendered
    assert "NOT VALIDATED" in rendered
    assert "FHIR validators executed" in rendered
    assert "<code>not_validated</code>" in rendered
    assert "script-src 'none'" in rendered
    assert "connect-src 'none'" in rendered
    assert "<script" not in rendered
    assert "patient" not in rendered.lower()


@pytest.mark.parametrize(
    "change",
    ["forged_valid", "fake_validation_exit", "publish", "extra", "wrong_warning", "legacy_schema"],
)
def test_forged_or_legacy_success_never_reaches_inert_preview(
    change: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, preview, row, receipt, report_path = _sample_receipt(tmp_path, monkeypatch)
    if change == "forged_valid":
        forged = json.loads(report_path.read_text(encoding="utf-8"))
        forged["status"] = "valid"
        forged["warnings"] = []
        report_path.write_text(json.dumps(forged, sort_keys=True)+"\n", encoding="utf-8")
        row["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
        row["provenance_status"] = "valid"
        row["validation_exit"] = 0
    elif change == "fake_validation_exit":
        row["validation_exit"] = True
    elif change == "publish":
        receipt["publication_authorized"] = True
    elif change == "extra":
        receipt["patient_name"] = "PRIVATE_PERSON_DO_NOT_EMIT"
    elif change == "wrong_warning":
        forged = json.loads(report_path.read_text(encoding="utf-8"))
        forged["warnings"] = []
        report_path.write_text(json.dumps(forged, sort_keys=True)+"\n", encoding="utf-8")
        row["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    else:
        receipt["schema"] = "medorigin-local-synthetic-fhir-example/v1"
    with pytest.raises((ValueError, TypeError)):
        preview.render(preview.admit_receipt(receipt, directory=tmp_path))


def test_full_v2_file_backed_run_one_admits_only_exit2_not_exit0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reproduce = _module("reproduce.py", monkeypatch)
    fixture = json.loads(reproduce.GOOD.read_text(encoding="utf-8"))
    expected_report = _report(fixture, reproduce.WARNING)
    payload = json.dumps(expected_report, sort_keys=True, separators=(",", ":"))+"\n"
    seen: list[str] = []

    def fake_call(_cli: Path, args: list[str], cwd: Path) -> CompletedProcess[str]:
        assert cwd.is_dir()
        seen.append(" ".join(args[:2]))
        if args == ["--version"]:
            return CompletedProcess(args, 0, "medscale 0.3.0\n", "")
        if args[:2] == ["fhir", "validate"] and "--output-dir" in args:
            store = Path(args[args.index("--output-dir") + 1])
            file = store / "fixed-fictional" / "report.json"
            file.parent.mkdir(parents=True)
            file.write_text(payload, encoding="utf-8", newline="\n")
            return CompletedProcess(args, 2, payload+"\n", "")
        if "--summary-only" in args:
            if str(reproduce.BAD) in args:
                return CompletedProcess(args, 1, "", "fixed refusal")
            return CompletedProcess(args, 0, json.dumps(fixture), "")
        raise AssertionError("unexpected fake installed CLI arguments")

    monkeypatch.setattr(reproduce, "call", fake_call)
    receipt = reproduce.run_one(Path("fake-installed-cli.exe"), tmp_path, "run_1")
    assert receipt["provenance_status"] == "not_validated"
    assert receipt["validation_exit"] == 2
    assert receipt["malformed_exit"] == 1
    assert len(receipt["report_sha256"]) == 64
    assert len(seen) == 5

    def forged_cli(_cli: Path, args: list[str], cwd: Path) -> CompletedProcess[str]:
        result = fake_call(_cli, args, cwd)
        if "--output-dir" in args:
            return CompletedProcess(args, 0, result.stdout, result.stderr)
        return result

    target = tmp_path / "second"
    target.mkdir()
    monkeypatch.setattr(reproduce, "call", forged_cli)
    with pytest.raises(ValueError, match="refuse unperformed validation"):
        reproduce.run_one(Path("fake-installed-cli.exe"), target, "run_2")


def test_native_export_receipt_stays_not_validated_and_never_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exporter = _module("evidence_export.py", monkeypatch)
    value = {
        "fhir": {
            "status": "NOT_VALIDATED",
            "report_sha256": "a" * 64,
            "fixture_sha256": "b" * 64,
        },
        "workspace": None,
    }
    expected = exporter.build_receipt(value)
    assert expected["schema"] == "medorigin-synthetic-desktop-evidence/v2"
    assert expected["fhir"]["status"] == "NOT_VALIDATED"
    assert expected["fhir_conformance_validated"] is False
    assert expected["clinical_use_authorized"] is False
    assert expected["publication_authorized"] is False
    file = tmp_path / "fictional-evidence.json"
    assert exporter.save_receipt_new(file, value)
    original = file.read_bytes()
    with pytest.raises(FileExistsError):
        exporter.save_receipt_new(file, value)
    assert file.read_bytes() == original
    value["fhir"]["status"] = "VALID"
    with pytest.raises(ValueError):
        exporter.build_receipt(value)
