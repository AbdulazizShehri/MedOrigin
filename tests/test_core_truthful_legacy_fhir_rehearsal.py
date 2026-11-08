"""Truthful, explicit Core-only route through the historical developer demo.

The legacy native/static-preview track must remain NO-GO until independently
reconciled. These tests never use clinical data or assert schema conformance.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "synthetic_fhir_developer_beta"
HIDDEN = "CLIENT_NAME_MUST_NOT_LEAK"


def _load(file: str) -> Any:
    spec = importlib.util.spec_from_file_location(
        "legacy_core_truth_" + file.replace(".", "_"), EXAMPLE / file
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _proof() -> dict[str, object]:
    return {
        "status": "LOCAL_FHIR_PROVENANCE_ONLY",
        "installed_cli_count": 1,
        "execution_mode": "unattested_installed_console_shim",
        "known_report_sha256": "a" * 64,
        "unknown_report_sha256": "b" * 64,
        "fhir_conformance_validated": False,
        "publication_authorized": False,
        "clinical_use_authorized": False,
        "independent_security_review_complete": False,
        "prepublication_rehearsal_qualified": False,
    }


def test_safe_core_only_receipt_does_not_certify_fhir_or_release() -> None:
    helper = _load("core_only.py")
    receipt = helper.qualified_receipt([Path("fake-installed-cli")], checker=lambda _: _proof())
    assert receipt == {
        "schema": "medorigin-core-fhir-provenance-only/v1",
        "status": "CORE_FHIR_PROVENANCE_ONLY",
        "scope": "deterministic local FHIR provenance ONLY; not FHIR validation",
        "installed_cli_count": 1,
        "launcher_identity_attested": False,
        "known_report_sha256": "a" * 64,
        "unknown_report_sha256": "b" * 64,
        "fhir_conformance_validated": False,
        "clinical_use_authorized": False,
        "independent_security_review_complete": False,
        "prepublication_rehearsal_qualified": False,
        "publication_authorized": False,
        "preview_generated": False,
    }
    assert HIDDEN not in json.dumps(receipt)
    assert "valid" not in receipt["status"].casefold()


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "FHIR_VALID"),
        ("installed_cli_count", True),
        ("installed_cli_count", 2),
        ("execution_mode", "source_verified_python_module"),
        ("fhir_conformance_validated", True),
        ("clinical_use_authorized", True),
        ("publication_authorized", True),
        ("independent_security_review_complete", True),
        ("prepublication_rehearsal_qualified", True),
        ("known_report_sha256", "not-a-hash"),
        ("unknown_report_sha256", "a" * 64),
    ],
)
def test_core_only_gate_rejects_forged_success(field: str, value: object) -> None:
    helper = _load("core_only.py")
    fake = _proof()
    fake[field] = value
    with pytest.raises(helper.CoreOnlyError):
        helper.qualified_receipt([Path("test")], checker=lambda _: fake)


def test_core_only_gate_rejects_extra_sensitive_member_without_echo() -> None:
    helper = _load("core_only.py")
    fake = _proof()
    fake["patient_name"] = HIDDEN
    with pytest.raises(helper.CoreOnlyError) as error:
        helper.qualified_receipt([Path("test")], checker=lambda _: fake)
    assert HIDDEN not in str(error.value)


def test_core_only_runner_creates_only_nonclinical_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = _load("reproduce.py")
    helper = _load("core_only.py")
    shim = tmp_path / "synthetic-pretend-installed.exe"
    shim.write_bytes(b"synthetic fixture only")
    out = tmp_path / "core-evidence"
    safe_receipt = helper.qualified_receipt([shim], checker=lambda _: _proof())

    def fake_run(path: str) -> dict[str, object]:
        assert str(path).endswith("core_only.py")
        return {
            "qualified_receipt": lambda clis: safe_receipt,
            "commit_new_receipt": helper.commit_new_receipt,
        }

    monkeypatch.setattr(runner.runpy, "run_path", fake_run)
    assert runner.main(["--cli", str(shim), "--out", str(out), "--core-provenance-only"]) == 0
    printed = capsys.readouterr()
    assert "MEDORIGIN_CORE_FHIR_PROVENANCE_ONLY_PASS" in printed.out
    assert "fhir_conformance_validated=false" in printed.out
    assert printed.err == ""
    assert sorted(x.name for x in out.iterdir()) == ["core-provenance-only.json"]
    assert json.loads((out / "core-provenance-only.json").read_text()) == safe_receipt
    assert not (out / "preview.html").exists()
    assert HIDDEN not in printed.out


def test_core_only_does_not_overwrite_existing_evidence(tmp_path: Path) -> None:
    helper = _load("core_only.py")
    out = tmp_path / "evidence"
    out.mkdir()
    original = out / "core-provenance-only.json"
    original.write_text(HIDDEN, encoding="utf-8")
    with pytest.raises(helper.CoreOnlyError):
        helper.commit_new_receipt(
            out, helper.qualified_receipt([Path("test")], checker=lambda _: _proof())
        )
    assert original.read_text(encoding="utf-8") == HIDDEN


def test_missing_or_failed_checker_does_not_create_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = _load("reproduce.py")
    shim = tmp_path / "pretend.exe"
    shim.write_bytes(b"synthetic only")
    out = tmp_path / "no-evidence"

    def fail(_paths: list[Path]) -> dict[str, object]:
        raise ValueError(HIDDEN)

    monkeypatch.setattr(
        runner.runpy,
        "run_path",
        lambda _: {"qualified_receipt": fail, "commit_new_receipt": lambda *a: None},
    )
    assert runner.main(["--cli", str(shim), "--out", str(out), "--core-provenance-only"]) == 2
    result = capsys.readouterr()
    assert "MEDORIGIN_CORE_FHIR_PROVENANCE_ONLY_BLOCKED" in result.err
    assert HIDDEN not in result.err
    assert not out.exists()


def test_core_only_refuses_workspace_preview_combination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = _load("reproduce.py")
    shim = tmp_path / "fake-cli"
    shim.write_bytes(b"synthetic fake")
    result = runner.main(
        [
            "--cli",
            str(shim),
            "--out",
            str(tmp_path / "not-created"),
            "--core-provenance-only",
            "--workspace-python",
            str(Path(sys.executable)),
        ]
    )
    assert result == 2
    assert "MEDORIGIN_CORE_FHIR_PROVENANCE_ONLY_BLOCKED" in capsys.readouterr().err
    assert not (tmp_path / "not-created").exists()


def test_legacy_full_beta_failure_redacts_installed_cli_stderr_and_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import subprocess

    runner = _load("reproduce.py")
    cli = tmp_path / "fictional-installed.exe"
    cli.write_bytes(b"offline-fictional-stub")
    out = tmp_path / "old-beta-evidence"

    def fake_cli(_cli: Path, args: list[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
        if args == ["--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="medscale 0.3.0\\n", stderr="")
        return subprocess.CompletedProcess(
            args, 2, stdout="", stderr=f"unable to validate {HIDDEN} C:\\\\private\\\\record.json"
        )

    monkeypatch.setattr(runner, "call", fake_cli)
    assert runner.main(["--cli", str(cli), "--out", str(out)]) == 1
    captured = capsys.readouterr()
    assert "MEDORIGIN_SYNTHETIC_FHIR_DEMO_FAIL" in captured.err
    assert "legacy_preview_contract_unqualified" in captured.err
    assert HIDDEN not in captured.err
    assert "record.json" not in captured.err
    assert not (out / "evidence.json").exists()
    assert not (out / "preview.html").exists()
