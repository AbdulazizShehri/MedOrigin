"""Regression guard for fail-closed synthetic ClaimSet admission."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from uuid import uuid4

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))

evidence_strength = importlib.import_module("medscale_workspace.evidence_strength")
errors_mod = importlib.import_module("medscale_workspace.errors")


def test_claim_set_rejects_invalid_claim_validation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed typed Claim validators must not leak an AttributeError."""

    malicious_claim = object.__new__(evidence_strength.Claim)
    claim_set = evidence_strength.ClaimSet(
        workspace_id=uuid4(),
        set_id=uuid4(),
        answer_text="synthetic answer",
        claims=(malicious_claim,),
    )
    monkeypatch.setattr(evidence_strength.Claim, "validated", lambda _self: None)
    with pytest.raises(errors_mod.ClaimInputError, match="Claim instances"):
        claim_set.validated()
