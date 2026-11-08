"""Synthetic-only desktop export: no PHI, no overwrite, no public release."""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

DIR = Path(__file__).resolve().parents[1] / "examples" / "synthetic_fhir_developer_beta"
GOOD_SHA = "a" * 64
OTHER_SHA = "b" * 64
# The only Core provenance status the export admits: truthful negative truth.
ADMITTED_STATUS = "NOT_VALIDATED"
# The historical false-positive status that earlier exports wrongly accepted.
HISTORICAL_VALID_STATUS = "VALID"
RECEIPT_KEYS = {
    "schema",
    "project",
    "distribution",
    "data_class",
    "validation_kind",
    "fhir_conformance_validated",
    "full_beta_preview_qualified",
    "fhir",
    "workspace",
    "clinical_use_authorized",
    "publication_authorized",
    "independent_review_completed",
}


@pytest.fixture
def exported(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(DIR))
    sys.modules.pop("evidence_export", None)
    return importlib.import_module("evidence_export")


def admitted(*, workspace: bool = False, status: str = ADMITTED_STATUS) -> dict[str, object]:
    """Build the desktop worker's admitted negative-truth result shape."""
    return {
        "fhir": {
            "status": status,
            "report_sha256": GOOD_SHA,
            "fixture_sha256": OTHER_SHA,
        },
        "workspace": (
            {"version": "0.1.0.dev1", "mode": "SYNTHETIC / offline-shell"} if workspace else None
        ),
    }


def test_receipt_contains_only_safe_evidence(exported: Any) -> None:
    receipt = exported.build_receipt(admitted())
    assert set(receipt) == RECEIPT_KEYS
    assert receipt["schema"] == "medorigin-synthetic-desktop-evidence/v2"
    assert receipt["data_class"] == "SYNTHETIC"
    assert receipt["fhir"] == {
        "status": "NOT_VALIDATED",
        "report_sha256": GOOD_SHA,
        "synthetic_fixture_sha256": OTHER_SHA,
    }
    assert receipt["fhir_conformance_validated"] is False
    assert receipt["full_beta_preview_qualified"] is False
    assert receipt["clinical_use_authorized"] is False
    assert receipt["publication_authorized"] is False
    assert receipt["independent_review_completed"] is False
    assert receipt["workspace"] == {
        "installed_synthetic_shell": False,
        "synthetic_case_preview_verified": False,
    }
    rendered = json.dumps(receipt)
    assert "patient" not in rendered.lower()
    assert '"VALID"' not in rendered
    assert str(DIR) not in rendered
    assert "\\\\" not in rendered and "/home/" not in rendered and ":/" not in rendered


@pytest.mark.parametrize("workspace", [False, True])
def test_historical_valid_provenance_is_refused(
    exported: Any, tmp_path: Path, workspace: bool
) -> None:
    historical = admitted(workspace=workspace, status=HISTORICAL_VALID_STATUS)
    with pytest.raises(
        ValueError, match="synthetic Core provenance is not an admitted negative-truth result"
    ):
        exported.build_receipt(historical)
    dest = tmp_path / "historical.json"
    with pytest.raises(ValueError):
        exported.save_receipt_new(dest, historical)
    assert not dest.exists()
    assert not list(tmp_path.iterdir())


def test_workspace_case_attestation_is_boolean_not_identity(exported: Any) -> None:
    receipt = exported.build_receipt(admitted(workspace=True), case_verified=True)
    assert receipt["fhir"]["status"] == "NOT_VALIDATED"
    assert type(receipt["workspace"]["synthetic_case_preview_verified"]) is bool
    assert receipt["workspace"] == {
        "installed_synthetic_shell": True,
        "synthetic_case_preview_verified": True,
    }
    assert "Synthetic Patient Alpha" not in json.dumps(receipt)
    assert "Synthetic Encounter 001" not in json.dumps(receipt)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update({"patient_name": "SECRET-CANARY"}),
        lambda r: r["fhir"].update({"patient_name": "SECRET-CANARY"}),
        lambda r: r["fhir"].update({"status": "INVALID"}),
        lambda r: r["fhir"].update({"report_sha256": "xyz"}),
        lambda r: r["fhir"].update({"fixture_sha256": "A" * 64}),
        lambda r: r.update({"workspace": {"patient_name": "SECRET-CANARY"}}),
    ],
)
def test_export_refuses_unknown_clinical_fields_and_invalid_status(
    exported: Any, mutate: Any
) -> None:
    data = admitted()
    mutate(data)
    with pytest.raises(ValueError) as err:
        exported.build_receipt(data)
    assert "SECRET-CANARY" not in str(err.value)


def test_fails_if_case_status_lacks_verified_workspace(exported: Any) -> None:
    with pytest.raises(ValueError):
        exported.build_receipt(admitted(), case_verified=True)
    with pytest.raises(ValueError):
        exported.build_receipt(admitted(workspace=True), case_verified="true")


def test_exclusive_save_is_reproducible_and_does_not_overwrite(
    exported: Any, tmp_path: Path
) -> None:
    dest = tmp_path / "synthetic-evidence.json"
    result = admitted(workspace=True)
    assert exported.save_receipt_new(dest, result) == "SYNTHETIC_EVIDENCE_EXPORTED"
    original = dest.read_bytes()
    saved = json.loads(original)
    assert saved["schema"] == "medorigin-synthetic-desktop-evidence/v2"
    assert saved["fhir"]["status"] == "NOT_VALIDATED"
    assert saved == exported.build_receipt(result)
    assert b"SECRET" not in original
    with pytest.raises(FileExistsError):
        exported.save_receipt_new(dest, result)
    assert dest.read_bytes() == original
    another = tmp_path / "again.json"
    exported.save_receipt_new(another, result)
    assert another.read_bytes() == original


def test_invalid_output_path_rejected_before_any_creation(exported: Any, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        exported.save_receipt_new(tmp_path / "not-json.txt", admitted())
    with pytest.raises(ValueError):
        exported.save_receipt_new(tmp_path / "absent" / "receipt.json", admitted())
    assert not list(tmp_path.iterdir())


def test_existing_symlink_destination_not_modified(exported: Any, tmp_path: Path) -> None:
    victim = tmp_path / "victim.txt"
    victim.write_text("DO-NOT-TOUCH", encoding="utf-8")
    link = tmp_path / "receipt.json"
    try:
        link.symlink_to(victim)
    except OSError:
        pytest.skip("symlinks require elevated privileges on this Windows host")
    with pytest.raises(FileExistsError):
        exported.save_receipt_new(link, admitted())
    assert victim.read_text(encoding="utf-8") == "DO-NOT-TOUCH"


def test_gui_export_button_requires_completed_validation(
    exported: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        pytest.skip("no graphical display in CI")
    pytest.importorskip("tkinter")
    import tkinter as tk

    monkeypatch.syspath_prepend(str(DIR))
    sys.modules.pop("desktop", None)
    desktop = importlib.import_module("desktop")
    root = tk.Tk()
    root.withdraw()
    try:
        app = desktop.Desktop(root, Path(sys.executable))
        root.update()
        assert app.export_button["state"] == "disabled"

        # Simulate the already-qualified worker result; live installed-Wheel
        # E2E is executed separately, with no fake data in real receipts.
        app.events.put(("success", admitted(workspace=True)))
        app._drain()
        assert app.export_button["state"] == "normal"
        output = tmp_path / "from-desktop.json"
        monkeypatch.setattr(desktop.filedialog, "asksaveasfilename", lambda **_kw: str(output))
        app._save_receipt()
        assert app.status.get() == "SYNTHETIC EVIDENCE SAVED"
        assert json.loads(output.read_text(encoding="utf-8"))["data_class"] == "SYNTHETIC"
        app._save_receipt()
        assert app.status.get() == "EXPORT NOT SAVED - EXISTING FILE PRESERVED"
        app.events.put(("error", "bad result"))
        app._drain()
        assert app.export_button["state"] == "disabled"
    finally:
        root.destroy()
