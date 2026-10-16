"""Synthetic fail-closed checks for fixture connector JSON admission."""

from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))
connector = importlib.import_module("medscale_workspace.connector")
errors = importlib.import_module("medscale_workspace.errors")


@pytest.mark.parametrize(
    "nonfinite", [math.nan, math.inf, -math.inf], ids=["nan", "inf", "neg-inf"]
)
def test_fixture_response_refuses_nonfinite_json_numbers(nonfinite: float) -> None:
    response = {
        "source_version": "synthetic-v1",
        "retrieved_at": "2026-10-15T00:00:00Z",
        "payload": {"synthetic": [{"measurement": nonfinite}]},
    }
    with pytest.raises(errors.ConnectorInputError, match="finite"):
        connector._admit_response(response)


def test_fixture_response_refuses_mixed_type_object_keys() -> None:
    response = {
        "source_version": "synthetic-v1",
        "retrieved_at": "2026-10-15T00:00:00Z",
        "payload": {"synthetic": {1: "synthetic", "item": "synthetic"}},
    }
    with pytest.raises(errors.ConnectorInputError, match="key"):
        connector._admit_response(response)
