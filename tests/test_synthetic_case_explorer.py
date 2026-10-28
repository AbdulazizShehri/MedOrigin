"""Strict synthetic-only case explorer contract and native navigation tests."""

from __future__ import annotations

import copy
import importlib
import json
import os
import sys
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_fhir_developer_beta"


@pytest.fixture
def explorer(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(EXAMPLE))
    sys.modules.pop("synthetic_cases", None)
    return importlib.import_module("synthetic_cases")


def test_pinned_fixture_projects_only_safe_demo_labels(explorer: Any) -> None:
    admitted = explorer.admit_snapshot(copy.deepcopy(explorer.EXPECTED_SNAPSHOT))
    assert admitted == {
        "workspace": "Synthetic workspace",
        "patient": "Synthetic Patient Alpha",
        "encounter": "Synthetic Encounter 001",
        "data_class": "SYNTHETIC",
        "origin": "Installed Workspace 0.1.0.dev1",
    }
    assert len(admitted) == 5
    assert "object_id" not in admitted


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["patient"].update({"phone": "PRIVATE-SENTINEL"}),
        lambda d: d["patient"].update({"display_name": "Real Patient"}),
        lambda d: d["encounter"].update({"patient_id": "malformed"}),
        lambda d: d["capabilities"].update({"network": True}),
        lambda d: d["storage"].update({"platform_key_provider": "unknown"}),
        lambda d: d.update({"clinical_record": "PRIVATE-SENTINEL"}),
    ],
)
def test_case_explorer_rejects_drift_and_patient_like_fields(explorer: Any, change: Any) -> None:
    candidate = copy.deepcopy(explorer.EXPECTED_SNAPSHOT)
    change(candidate)
    with pytest.raises(ValueError) as err:
        explorer.admit_snapshot(candidate)
    assert "PRIVATE-SENTINEL" not in str(err.value)


@pytest.mark.parametrize(
    "path,replacement",
    [
        (("capabilities", "network"), 0),
        (("capabilities", "ehr"), 0.0),
        (("capabilities", "persistent_write"), 1),
        (("storage", "plaintext_fallback"), 0),
        (("capabilities", "external_model"), 0.0),
    ],
)
def test_case_explorer_refuses_numeric_boolean_aliases(
    explorer: Any, path: Any, replacement: Any
) -> None:
    candidate = copy.deepcopy(explorer.EXPECTED_SNAPSHOT)
    candidate[path[0]][path[1]] = replacement
    # Ordinary Python dict equality would accept these altered values.
    assert candidate == explorer.EXPECTED_SNAPSHOT
    with pytest.raises(ValueError):
        explorer.admit_snapshot(candidate)


@pytest.mark.parametrize("duplicate_at", ["root", "patient", "capabilities"])
def test_case_loader_rejects_duplicate_json_fields(
    explorer: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, duplicate_at: str
) -> None:
    monkeypatch.setattr(explorer, "verify_workspace_shell", lambda _python, _cwd: None)
    payload = json.dumps(explorer.EXPECTED_SNAPSHOT)
    if duplicate_at == "root":
        payload = payload.replace(
            '{"workspace_id":', '{"workspace_id": "PRIVATE-SENTINEL", "workspace_id":', 1
        )
    elif duplicate_at == "patient":
        payload = payload.replace(
            '"display_name":', '"display_name": "PRIVATE-SENTINEL", "display_name":', 1
        )
    else:
        payload = payload.replace('"network":', '"network": true, "network":', 1)
    monkeypatch.setattr(
        explorer, "call", lambda _python, args, _cwd: CompletedProcess(args, 0, payload, "")
    )
    with pytest.raises(ValueError) as err:
        explorer.load_synthetic_case(Path(sys.executable), tmp_path)
    assert "PRIVATE-SENTINEL" not in str(err.value)


def test_case_loader_requests_only_installed_fixed_fixture(
    explorer: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observed: list[list[str]] = []

    monkeypatch.setattr(explorer, "verify_workspace_shell", lambda _python, _cwd: None)

    def fake_call(_python: Path, args: list[str], _cwd: Path) -> CompletedProcess[str]:
        observed.append(args)
        return CompletedProcess(args, 0, json.dumps(explorer.EXPECTED_SNAPSHOT), "")

    monkeypatch.setattr(explorer, "call", fake_call)
    result = explorer.load_synthetic_case(Path(sys.executable), tmp_path)
    assert result["patient"] == "Synthetic Patient Alpha"
    assert len(observed) == 1
    assert observed[0][:2] == ["-I", "-c"]
    assert observed[0][-1] == explorer._SNAPSHOT_COMMAND


def test_case_loader_suppresses_malformed_shell_payload(
    explorer: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(explorer, "verify_workspace_shell", lambda _python, _cwd: None)
    monkeypatch.setattr(
        explorer,
        "call",
        lambda _python, args, _cwd: CompletedProcess(args, 0, '{"patient":"PRIVATE-SENTINEL"}', ""),
    )
    with pytest.raises(ValueError) as err:
        explorer.load_synthetic_case(Path(sys.executable), tmp_path)
    assert "PRIVATE-SENTINEL" not in str(err.value)


def test_case_loader_rejects_oversized_output(
    explorer: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(explorer, "verify_workspace_shell", lambda _python, _cwd: None)
    monkeypatch.setattr(
        explorer,
        "call",
        lambda _python, args, _cwd: CompletedProcess(args, 0, "x" * 4097, ""),
    )
    with pytest.raises(ValueError):
        explorer.load_synthetic_case(Path(sys.executable), tmp_path)


def test_native_case_page_respects_missing_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        pytest.skip("no graphical Tk display")
    pytest.importorskip("tkinter")
    import tkinter as tk

    monkeypatch.syspath_prepend(str(EXAMPLE))
    sys.modules.pop("desktop", None)
    desktop = importlib.import_module("desktop")
    root = tk.Tk()
    root.withdraw()
    try:
        app = desktop.Desktop(root, Path(sys.executable))
        root.update()
        app._switch("Synthetic cases")
        assert app.active == "Synthetic cases"
        assert app.case_button["state"] == "disabled"
        assert app.case_patient.get() == "Not loaded"
        app._switch("Synthetic validation")
        assert app.active == "Synthetic validation"
    finally:
        root.destroy()
