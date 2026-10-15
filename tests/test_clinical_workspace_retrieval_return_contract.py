"""Reject malformed nested retrieval validation returns using synthetic objects."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from uuid import uuid4

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))
retrieval = importlib.import_module("medscale_workspace.retrieval")
errors = importlib.import_module("medscale_workspace.errors")


def test_snapshot_rejects_invalid_entry_validation_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = retrieval.SnapshotEntry(
        source_id=uuid4(), source_revision="synthetic-v1", content_digest="sha256:" + "a" * 64
    )
    snapshot = retrieval.SnapshotManifest(
        workspace_id=uuid4(),
        corpus_id=uuid4(),
        corpus_key="test-corpus",
        snapshot_id=uuid4(),
        entries=(entry,),
        index_identity=retrieval.INDEX_IDENTITY,
        ranking_identity=retrieval.RANKING_IDENTITY,
        schema_version=retrieval.SCHEMA_VERSION,
    )
    monkeypatch.setattr(retrieval.SnapshotEntry, "validated", lambda _self: None)
    with pytest.raises(errors.SnapshotInputError, match="SnapshotEntry"):
        snapshot.validated()


def test_result_set_rejects_invalid_hit_validation_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query_id = uuid4()
    hit = retrieval.ScoredResult(
        source_id=uuid4(),
        source_revision="synthetic-v1",
        source_date="2026-10-15",
        rank=0,
        score=1,
        text="synthetic",
    )
    results = retrieval.ResultSet(
        workspace_id=uuid4(),
        query_id=query_id,
        snapshot_id=uuid4(),
        result_id=retrieval.result_id_for(query_id),
        results=(hit,),
    )
    monkeypatch.setattr(retrieval.ScoredResult, "validated", lambda _self: None)
    with pytest.raises(errors.RetrievalInputError, match="ScoredResult"):
        results.validated()
