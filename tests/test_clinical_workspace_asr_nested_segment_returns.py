"""Synthetic-only nested ASR segment return-contract regression guards."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from uuid import uuid4

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))
asr = importlib.import_module("medscale_workspace.asr")
errors = importlib.import_module("medscale_workspace.errors")


@pytest.mark.parametrize("invalid_result", [None, object()], ids=["none", "wrong-type"])
def test_asr_result_rejects_invalid_segment_validation_return(
    monkeypatch: pytest.MonkeyPatch, invalid_result: object
) -> None:
    segment = asr.AsrSegment(index=0, start_s=0.0, end_s=1.0, text="synthetic")
    result = asr.AsrResult(
        workspace_id=uuid4(),
        session_id=uuid4(),
        input_id=uuid4(),
        input_revision="chunk-00000001",
        status=asr.AsrStatus.SUCCESS,
        transcript="synthetic",
        segments=(segment,),
        requested_language="en",
        detected_language="en",
        model_id=asr.MODEL_ID,
        model_revision=asr.MODEL_REVISION,
        runtime_name=asr.RUNTIME_NAME,
        runtime_version=asr.RUNTIME_VERSION,
        input_occurred_at="2026-10-15T00:00:00Z",
        result_occurred_at="2026-10-15T00:00:01Z",
        reason="",
    )
    monkeypatch.setattr(asr.AsrSegment, "validated", lambda _self: invalid_result)
    with pytest.raises(errors.AsrInputError, match="AsrSegment"):
        result.validated()
