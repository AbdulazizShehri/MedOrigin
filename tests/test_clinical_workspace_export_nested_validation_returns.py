"""Synthetic guard for nested export descriptor validation return types."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))
dataset = importlib.import_module("medscale_workspace.dataset")
errors = importlib.import_module("medscale_workspace.errors")


@pytest.mark.parametrize("bad_value", [None, object()], ids=["null", "wrong-type"])
def test_export_item_admission_rejects_malformed_validation_result(
    monkeypatch: pytest.MonkeyPatch, bad_value: object
) -> None:
    item = object.__new__(dataset.ExportSourceDescriptor)
    monkeypatch.setattr(dataset.ExportSourceDescriptor, "validated", lambda _self: bad_value)
    with pytest.raises(errors.ExportStagingInputError, match="ExportSourceDescriptor"):
        dataset._admit_items((item,))
