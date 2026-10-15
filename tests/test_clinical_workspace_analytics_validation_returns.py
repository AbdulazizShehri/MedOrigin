"""Synthetic-only guard for AnalyticsRecord nested validator return contracts."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from uuid import uuid4

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))
analytics = importlib.import_module("medscale_workspace.analytics")
errors = importlib.import_module("medscale_workspace.errors")


@pytest.mark.parametrize("invalid_result", [None, object()], ids=["none", "wrong-type"])
def test_analytics_rejects_invalid_metric_validation_return(
    monkeypatch: pytest.MonkeyPatch, invalid_result: object
) -> None:
    counts = (
        analytics.MetricCount("draft", 1),
        analytics.MetricCount("reviewed", 0),
        analytics.MetricCount("finalized", 0),
    )
    record = analytics.AnalyticsRecord(
        workspace_id=uuid4(),
        analytics_id=uuid4(),
        metric_name=analytics.MetricName.REVIEW_STATUS_COUNTS,
        metric_version=analytics.ADMITTED_METRIC_VERSION,
        input_count=1,
        input_digest="sha256:" + "a" * 64,
        counts=counts,
    )
    monkeypatch.setattr(analytics.MetricCount, "validated", lambda _self: invalid_result)
    with pytest.raises(errors.AnalyticsInputError, match="MetricCount instances"):
        record.validated()
