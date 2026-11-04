"""Portable installed-Core CLI proof using only embedded synthetic resources."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "workspace" / "src"))

from medscale.cli import main as core_main  # noqa: E402
from medscale.fhirkit import workspace_demo  # noqa: E402

PRIVATE_SENTINEL = "CLIENT_PRIVATE_PATH_SHOULD_NEVER_PRINT"


def test_real_public_cli_runs_fictional_encrypted_ephemeral_workspace(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert core_main(["fhir", "workspace-demo", "--synthetic-only", "--ephemeral-demo"]) == 0
    result = capsys.readouterr()
    assert result.err == ""
    receipt = json.loads(result.out)
    assert receipt["schema"] == "medorigin-installed-ephemeral-fhir-workspace/v1"
    assert receipt["status"] == "SYNTHETIC_ENCRYPTED_ATOMIC_DEMO_PASS"
    assert receipt["resource_count"] == 3
    assert receipt["provenance_records"] == 3
    assert receipt["audit_events"] == 1
    assert receipt["verified_reopen"] is True
    assert receipt["ephemeral_store_removed"] is True
    assert receipt["clinical_use_authorized"] is False
    assert receipt["full_fhir_r4_conformance_established"] is False
    assert receipt["publication_authorized"] is False
    assert receipt["production_key_provider_used"] is False
    assert receipt["payload_included"] is False
    assert "fictional-patient-001" not in result.out
    assert "Fictional Example Only" not in result.out
    assert "fictional value" not in result.out


@pytest.mark.parametrize(
    "tokens",
    [
        ["fhir", "workspace-demo"],
        ["fhir", "workspace-demo", "--synthetic-only"],
        ["fhir", "workspace-demo", "--ephemeral-demo"],
        ["fhir", "workspace-demo", "--synthetic-only", "--synthetic-only"],
        ["fhir", "workspace-demo", "--ephemeral-demo", "--ephemeral-demo"],
        ["fhir", "workspace-demo", "--synthetic-only", PRIVATE_SENTINEL],
        ["fhir", "workspace-demo", "--ephemeral-demo", "--source", PRIVATE_SENTINEL],
        ["fhir", "workspace-demo", "--synthetic-only", "--ephemeral-demo", PRIVATE_SENTINEL],
    ],
)
def test_all_non_exact_flag_sequences_refuse_without_disclosing_tokens(
    tokens: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert core_main(tokens) == 2
    out = capsys.readouterr()
    assert out.out == ""
    assert "explicit_synthetic_demo_flags_required" in out.err
    assert PRIVATE_SENTINEL not in out.err


def test_help_does_not_open_store(capsys: pytest.CaptureFixture[str]) -> None:
    assert core_main(["fhir", "workspace-demo", "--help"]) == 0
    out = capsys.readouterr()
    assert "synthetic-only" in out.out
    assert "ephemeral-demo" in out.out
    assert out.err == ""


def test_demo_handles_internal_failure_with_fixed_redacted_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def error() -> str:
        raise RuntimeError(PRIVATE_SENTINEL)

    monkeypatch.setattr(workspace_demo, "receipt_json", error)
    assert core_main(["fhir", "workspace-demo", "--ephemeral-demo", "--synthetic-only"]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "encrypted_synthetic_demo_blocked" in result.err
    assert PRIVATE_SENTINEL not in result.err


def test_fictional_fixture_is_fresh_per_invocation() -> None:
    one = workspace_demo._fictional_bundle()
    two = workspace_demo._fictional_bundle()
    one["entry"][1]["resource"]["name"][0]["text"] = "changed"
    assert two["entry"][1]["resource"]["name"][0]["text"] == "Fictional Example Only"
