"""Reject malformed validation results without leaking raw implementation errors.

These synthetic-only tests protect the Draft admission contract when a provided
SourceReference or DraftSpan instance violates its claimed return contract.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from uuid import UUID

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))

draft_mod = importlib.import_module("medscale_workspace.draft")
errors_mod = importlib.import_module("medscale_workspace.errors")

WORKSPACE = UUID("af295d45-8d6e-4281-a48b-7838439e839b")
SESSION = UUID("2af64fba-ea6b-4e18-8475-28d6c373718e")
TRANSCRIPT = UUID("28413491-b095-4421-bd32-926697ef6bb0")
DRAFT_ID = UUID("8cf0701c-5b3b-42df-83b8-f30bea43fbdb")


def test_span_rejects_unexpected_validation_result(monkeypatch: pytest.MonkeyPatch) -> None:
    source = draft_mod.SourceReference(
        transcript_id=TRANSCRIPT,
        transcript_revision=draft_mod.TRANSCRIPT_REVISION,
        source_range=draft_mod.SourceRange(
            segment_index=0, char_start=0, char_end=1, source_digest="sha256:" + "a" * 64
        ),
        relation=draft_mod.SupportRelation.EXACT_QUOTE,
    )
    span = draft_mod.DraftSpan(
        span_id="span-1",
        text="synthetic",
        status=draft_mod.SupportStatus.SUPPORTED,
        sources=(source,),
        relation_note="",
        failure_reason="",
        abstention_reason="",
    )
    monkeypatch.setattr(draft_mod.SourceReference, "validated", lambda _self: None)
    with pytest.raises(errors_mod.DraftInputError, match="SourceReference"):
        span.validated()


def test_draft_rejects_unexpected_span_validation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    span = draft_mod.DraftSpan(
        span_id="span-1",
        text="synthetic",
        status=draft_mod.SupportStatus.UNSUPPORTED,
        sources=(),
        relation_note="",
        failure_reason="",
        abstention_reason="",
    )
    draft = draft_mod.Draft(
        workspace_id=WORKSPACE,
        session_id=SESSION,
        draft_id=DRAFT_ID,
        draft_revision=draft_mod.DRAFT_REVISION,
        transcript=draft_mod.TranscriptReference(TRANSCRIPT, draft_mod.TRANSCRIPT_REVISION),
        template=draft_mod.expected_template(),
        input_bundle_digest="sha256:" + "b" * 64,
        model=draft_mod.ModelIdentity(draft_mod.MODEL_ID, draft_mod.MODEL_REVISION),
        runtime=draft_mod.RuntimeIdentity(draft_mod.RUNTIME_NAME, draft_mod.RUNTIME_VERSION),
        status=draft_mod.DraftStatus.DRAFT,
        spans=(span,),
    )
    monkeypatch.setattr(draft_mod.DraftSpan, "validated", lambda _self: None)
    with pytest.raises(errors_mod.DraftInputError, match="DraftSpan"):
        draft.validated()


def test_backend_rejects_unexpected_span_plan_validation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    span = draft_mod.DraftSpan(
        span_id="span-1",
        text="synthetic",
        status=draft_mod.SupportStatus.UNSUPPORTED,
        sources=(),
        relation_note="",
        failure_reason="",
        abstention_reason="",
    )
    monkeypatch.setattr(draft_mod.DraftSpan, "validated", lambda _self: None)
    with pytest.raises(draft_mod.DraftBackendError, match="span plan"):
        draft_mod.synthesize_with_backend(
            WORKSPACE,
            SESSION,
            TRANSCRIPT,
            draft_mod.TRANSCRIPT_REVISION,
            "synthetic input",
            (),
            draft_mod.expected_template(),
            "sha256:" + "b" * 64,
            draft_mod.ModelIdentity(draft_mod.MODEL_ID, draft_mod.MODEL_REVISION),
            draft_mod.RuntimeIdentity(draft_mod.RUNTIME_NAME, draft_mod.RUNTIME_VERSION),
            (span,),
            draft_mod.mock_draft_backend,
        )
