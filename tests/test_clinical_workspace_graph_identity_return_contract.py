"""Synthetic fail-closed guard for derived patient graph edge identity."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from uuid import uuid4

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))
graph = importlib.import_module("medscale_workspace.patient_graph")
errors = importlib.import_module("medscale_workspace.errors")


@pytest.mark.parametrize("invalid_result", [None, object()], ids=["none", "wrong-type"])
def test_edge_identity_rejects_invalid_source_validation_return(
    monkeypatch: pytest.MonkeyPatch,
    invalid_result: object,
) -> None:
    source = graph.GraphEdgeSource(uuid4(), "synthetic-v1", "sha256:" + "a" * 64)
    monkeypatch.setattr(graph.GraphEdgeSource, "validated", lambda _self: invalid_result)
    with pytest.raises(errors.GraphInputError, match="GraphEdgeSource"):
        graph.edge_id_for(
            uuid4(),
            uuid4(),
            uuid4(),
            graph.RelationshipType.RELATED_TO,
            graph.EpistemicState.ASSERTED,
            (source,),
            graph.DERIVATION_METHOD,
            graph.DERIVATION_METHOD_VERSION,
            None,
            None,
        )
