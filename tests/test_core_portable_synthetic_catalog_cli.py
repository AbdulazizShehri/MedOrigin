"""Portable public Core FHIR catalog demo acceptance, fictional only."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "workspace" / "src"))

from medscale.cli import main as core_main  # noqa: E402
from medscale.fhirkit import workspace_catalog_demo  # noqa: E402

PRIVATE = "NEVER_PRINT_THIS_PRIVATE_FILE_OR_PATIENT_NAME"


def test_public_installed_style_catalog_demo_really_imports_and_indexes_two_bundles(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        core_main(["fhir", "workspace-catalog-demo", "--synthetic-only", "--ephemeral-demo"]) == 0
    )
    output = capsys.readouterr()
    assert output.err == ""
    report = json.loads(output.out)
    assert report["schema"] == "medorigin-ephemeral-fhir-import-catalog-demo/v1"
    assert report["status"] == "SYNTHETIC_ENCRYPTED_CATALOG_DEMO_PASS"
    assert report["import_count"] == 2
    assert report["resource_count"] == 4
    assert report["verified_audit_events"] == 3
    assert report["ephemeral_store_removed"] is True
    assert report["payload_included"] is False
    assert report["clinical_use_authorized"] is False
    assert report["full_fhir_r4_conformance_established"] is False
    assert report["publication_authorized"] is False
    assert [entry["audit_sequence"] for entry in report["imports"]] == [1, 3]
    assert [entry["resource_count"] for entry in report["imports"]] == [3, 1]
    assert all(len(entry["source_content_sha256"]) == 64 for entry in report["imports"])
    assert "Fictional Catalog Example Only" not in output.out
    assert "Fictional Example Only" not in output.out
    assert "urn:uuid" not in output.out
    assert PRIVATE not in output.out


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--synthetic-only"],
        ["--ephemeral-demo"],
        ["--synthetic-only", "--synthetic-only"],
        ["--ephemeral-demo", "--ephemeral-demo"],
        ["--synthetic-only", PRIVATE],
        ["--synthetic-only", "--ephemeral-demo", PRIVATE],
        ["--synthetic-only", "--file", PRIVATE],
    ],
)
def test_unknown_flags_never_echo_potential_patient_data(
    args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert core_main(["fhir", "workspace-catalog-demo", *args]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "explicit_synthetic_demo_flags_required" in captured.err
    assert PRIVATE not in captured.err


def test_help_is_safe_and_does_not_run_a_workspace(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert core_main(["fhir", "workspace-catalog-demo", "--help"]) == 0
    captured = capsys.readouterr()
    assert "synthetic-only" in captured.out
    assert "ephemeral-demo" in captured.out
    assert captured.err == ""


def test_internal_failure_is_fixed_redacted_and_not_false_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def refuse() -> str:
        raise RuntimeError(PRIVATE)

    monkeypatch.setattr(workspace_catalog_demo, "receipt_json", refuse)
    assert (
        core_main(["fhir", "workspace-catalog-demo", "--synthetic-only", "--ephemeral-demo"]) == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "encrypted_synthetic_catalog_blocked" in captured.err
    assert PRIVATE not in captured.err


def test_two_fictional_bundles_are_fresh_and_no_path_is_used() -> None:
    first: dict[str, Any] = workspace_catalog_demo._other_fictional_bundle()
    second: dict[str, Any] = workspace_catalog_demo._other_fictional_bundle()
    first["entry"][0]["resource"]["name"][0]["text"] = PRIVATE
    assert second["entry"][0]["resource"]["name"][0]["text"] != PRIVATE
    assert not any(isinstance(value, Path) for value in second.values())
