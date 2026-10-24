"""Safety and lifecycle tests for the optional synthetic desktop example."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "synthetic_fhir_developer_beta"
GOOD_HEX = "a" * 64
OTHER_HEX = "b" * 64


@pytest.fixture
def desktop(monkeypatch: pytest.MonkeyPatch) -> Any:
    pytest.importorskip("tkinter")
    monkeypatch.syspath_prepend(str(EXAMPLE_DIR))
    sys.modules.pop("desktop", None)
    return importlib.import_module("desktop")


def test_public_projection_whitelists_fields(desktop: Any) -> None:
    payload = {
        "structural_status": "valid",
        "malformed_exit": 1,
        "report_sha256": GOOD_HEX,
        "fixture_sha256": OTHER_HEX,
        "patient_name": "DO-NOT-DISPLAY-THIS-FIELD",
    }
    admitted = desktop.public_result(payload)
    assert admitted == {
        "status": "VALID",
        "report_sha256": GOOD_HEX,
        "fixture_sha256": OTHER_HEX,
    }
    assert "DO-NOT-DISPLAY" not in str(admitted)


@pytest.mark.parametrize(
    "broken",
    [
        {"structural_status": "invalid"},
        {"structural_status": "valid", "malformed_exit": 0},
        {"structural_status": "valid", "malformed_exit": 1, "report_sha256": "xyz"},
        {"structural_status": "valid", "malformed_exit": 1, "report_sha256": "A" * 64},
    ],
)
def test_public_projection_rejects_invalid_evidence(desktop: Any, broken: Any) -> None:
    with pytest.raises(ValueError):
        desktop.public_result(broken)


def test_validation_always_uses_temporary_local_synthetic_data(
    desktop: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[Path] = []

    def fake_run(_cli: Path, directory: Path, label: str) -> dict[str, object]:
        assert label == "desktop"
        assert directory.is_dir()
        assert directory.name.startswith("medorigin-synthetic-ui-")
        observed.append(directory)
        return {
            "structural_status": "valid",
            "malformed_exit": 1,
            "report_sha256": GOOD_HEX,
            "fixture_sha256": OTHER_HEX,
        }

    monkeypatch.setattr(desktop, "run_one", fake_run)
    result = desktop.validate_installed(Path(sys.executable))
    assert result == {
        "fhir": {
            "status": "VALID",
            "report_sha256": GOOD_HEX,
            "fixture_sha256": OTHER_HEX,
        },
        "workspace": None,
    }
    assert len(observed) == 1
    assert not observed[0].exists(), "temporary fixture reports must be cleaned up"


def test_workspace_status_rejects_extra_patient_like_fields(
    desktop: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        desktop,
        "run_one",
        lambda _cli, _dir, _label: {
            "structural_status": "valid",
            "malformed_exit": 1,
            "report_sha256": GOOD_HEX,
            "fixture_sha256": OTHER_HEX,
        },
    )
    monkeypatch.setattr(
        desktop,
        "verify_workspace_shell",
        lambda _python, _dir: {
            "application": "medscale-workspace",
            "version": "0.1.0.dev1",
            "data_class": "SYNTHETIC",
            "mode": "offline-shell",
            "ready": True,
            "patient_name": "PRIVATE-SENTINEL",
        },
    )
    with pytest.raises(ValueError) as error:
        desktop.validate_installed(Path(sys.executable), Path(sys.executable))
    assert "PRIVATE-SENTINEL" not in str(error.value)


def test_native_window_initializes_and_pages_navigate(desktop: Any) -> None:
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        pytest.skip("no graphical display in hosted CI")
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        app = desktop.Desktop(root, Path(sys.executable))
        root.update()
        assert app.active == "Overview"
        app._switch("Synthetic validation")
        assert app.active == "Synthetic validation"
        app._switch("Safety & scope")
        assert app.active == "Safety & scope"
    finally:
        root.destroy()
