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
        "provenance_status": "not_validated",
        "validation_exit": 2,
        "malformed_exit": 1,
        "report_sha256": GOOD_HEX,
        "fixture_sha256": OTHER_HEX,
        "patient_name": "DO-NOT-DISPLAY-THIS-FIELD",
    }
    admitted = desktop.public_result(payload)
    assert admitted == {
        "status": "NOT_VALIDATED",
        "report_sha256": GOOD_HEX,
        "fixture_sha256": OTHER_HEX,
    }
    assert "DO-NOT-DISPLAY" not in str(admitted)


@pytest.mark.parametrize(
    "broken",
    [
        {"provenance_status": "valid"},
        {"provenance_status": "not_validated", "validation_exit": 2, "malformed_exit": 0},
        {
            "provenance_status": "not_validated",
            "validation_exit": 2,
            "malformed_exit": 1,
            "report_sha256": "xyz",
        },
        {
            "provenance_status": "not_validated",
            "validation_exit": 2,
            "malformed_exit": 1,
            "report_sha256": "A" * 64,
        },
        {
            "provenance_status": "not_validated",
            "validation_exit": 2,
            "malformed_exit": True,
            "report_sha256": GOOD_HEX,
            "fixture_sha256": OTHER_HEX,
        },
        {
            "provenance_status": "not_validated",
            "validation_exit": 2,
            "malformed_exit": 1.0,
            "report_sha256": GOOD_HEX,
            "fixture_sha256": OTHER_HEX,
        },
        {
            "provenance_status": "not_validated",
            "malformed_exit": 1,
            "validation_exit": True,
            "report_sha256": GOOD_HEX,
            "fixture_sha256": OTHER_HEX,
        },
        {
            "provenance_status": "not_validated",
            "malformed_exit": 1,
            "validation_exit": 0,
            "report_sha256": GOOD_HEX,
            "fixture_sha256": OTHER_HEX,
        },
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
            "provenance_status": "not_validated",
            "validation_exit": 2,
            "malformed_exit": 1,
            "report_sha256": GOOD_HEX,
            "fixture_sha256": OTHER_HEX,
        }

    monkeypatch.setattr(desktop, "run_one", fake_run)
    result = desktop.validate_installed(Path(sys.executable))
    assert result == {
        "fhir": {
            "status": "NOT_VALIDATED",
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
            "provenance_status": "not_validated",
            "validation_exit": 2,
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


def _hosted_windows_tcl_bootstrap_failure(error: Exception) -> bool:
    """Recognize ONLY a broken hosted Windows Tcl installation, never app errors."""
    return (
        os.name == "nt"
        and os.environ.get("GITHUB_ACTIONS") == "true"
        and any(
            marker in str(error)
            for marker in ("Can't find a usable init.tcl", "Can't find a usable tk.tcl")
        )
    )


def test_hosted_tcl_deferral_is_exact_and_never_hides_other_gui_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tkinter as tk

    known_init = tk.TclError("Can't find a usable init.tcl in the following directories")
    known_tk = tk.TclError(
        "Can't find a usable tk.tcl in the following directories: "
        "tk8.6/ttk/sizegrip.tcl: no such file or directory"
    )
    other = tk.TclError("unexpected native GUI render failure")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert _hosted_windows_tcl_bootstrap_failure(known_init) is (os.name == "nt")
    assert _hosted_windows_tcl_bootstrap_failure(known_tk) is (os.name == "nt")
    assert _hosted_windows_tcl_bootstrap_failure(other) is False
    monkeypatch.delenv("GITHUB_ACTIONS")
    assert _hosted_windows_tcl_bootstrap_failure(known_init) is False
    assert _hosted_windows_tcl_bootstrap_failure(known_tk) is False


def test_all_native_pages_can_scroll_to_their_end_at_minimum_window_size(
    desktop: Any,
) -> None:
    """The last synthetic safety instruction must be accessible on a small screen."""
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        pytest.skip("no graphical display in hosted CI")
    import tkinter as tk
    from types import SimpleNamespace

    try:
        root = tk.Tk()
    except tk.TclError as error:
        if _hosted_windows_tcl_bootstrap_failure(error):
            pytest.skip(
                "Hosted Windows Tcl/Tk init scripts unavailable; "
                "independent real-owner Windows GUI acceptance required"
            )
        raise
    try:
        app = desktop.Desktop(root, Path(sys.executable))
        root.geometry("850x610-2000-2000")
        for name in ("Overview", "Synthetic cases", "Synthetic validation", "Safety & scope"):
            app._switch(name)
            root.update()
            assert app.canvas.winfo_height() > 0
            assert app.pages[name].winfo_reqheight() > app.canvas.winfo_height()
            assert app.canvas.yview()[0] == 0
            app._scroll_page(SimpleNamespace(delta=-120))
            root.update()
            assert app.canvas.yview()[0] > 0, name
            app.canvas.yview_moveto(1)
            root.update()
            assert app.canvas.yview()[1] == 1, name
        # Switching pages resets the view without losing the other widgets.
        app._switch("Synthetic validation")
        root.update()
        assert app.canvas.yview()[0] == 0
        assert app.run_button.winfo_exists()
    finally:
        root.destroy()
