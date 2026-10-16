"""Fail-closed synthetic Review nested validator return contracts."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))
review = importlib.import_module("medscale_workspace.review")
errors = importlib.import_module("medscale_workspace.errors")


@pytest.mark.parametrize("invalid_result", [object()], ids=["wrong-type"])
def test_review_rejects_invalid_span_validator_result(
    monkeypatch: pytest.MonkeyPatch, invalid_result: object
) -> None:
    span = object.__new__(review.SpanReview)
    monkeypatch.setattr(review.SpanReview, "validated", lambda _self: invalid_result)
    with pytest.raises(errors.ReviewSupportError, match="SpanReview instances"):
        review._admit_span_set((span,))


@pytest.mark.parametrize("invalid_result", [object()], ids=["wrong-type"])
def test_review_rejects_invalid_suggestion_validator_result(
    monkeypatch: pytest.MonkeyPatch, invalid_result: object
) -> None:
    suggestion = object.__new__(review.SuggestionRecord)
    monkeypatch.setattr(review.SuggestionRecord, "validated", lambda _self: invalid_result)
    with pytest.raises(errors.ReviewSuggestionError, match="SuggestionRecord instances"):
        review._admit_suggestion_set((suggestion,))
