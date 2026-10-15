"""Fail-closed synthetic nested validation contracts for linked workspace objects."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from uuid import uuid4

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))
linked = importlib.import_module("medscale_workspace.linked_workspace")
errors = importlib.import_module("medscale_workspace.errors")


def _source_and_members() -> tuple[object, object, object]:
    source = linked.LinkSource(uuid4(), "synthetic-v1", "sha256:" + "a" * 64)
    first = linked.MemberRef(linked.LinkedMemberType.LINKED_DOCUMENT, uuid4())
    second = linked.MemberRef(linked.LinkedMemberType.LINKED_TABLE, uuid4())
    return source, first, second


def test_workspace_link_rejects_invalid_nested_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, first, second = _source_and_members()
    link = linked.WorkspaceLink(
        workspace_id=uuid4(),
        link_id=uuid4(),
        source_member=first,
        target_member=second,
        link_kind=linked.LinkKind.REFERENCES,
        sources=(source,),
        derivation_method=linked.DERIVATION_METHOD,
        derivation_version=linked.DERIVATION_METHOD_VERSION,
        link_schema_version=linked.LINK_SCHEMA_VERSION,
    )
    monkeypatch.setattr(linked.LinkSource, "validated", lambda _self: None)
    with pytest.raises(errors.LinkedInputError, match="LinkSource"):
        link.validated()


def test_link_identity_rejects_invalid_nested_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, first, second = _source_and_members()
    monkeypatch.setattr(linked.LinkSource, "validated", lambda _self: None)
    with pytest.raises(errors.LinkedInputError, match="LinkSource"):
        linked.link_id_for(
            uuid4(),
            first,
            second,
            linked.LinkKind.REFERENCES,
            (source,),
            linked.DERIVATION_METHOD,
            linked.DERIVATION_METHOD_VERSION,
        )


def test_research_references_reject_invalid_nested_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = linked.ResearchRef("synthetic-artifact", "synthetic-v1")
    monkeypatch.setattr(linked.ResearchRef, "validated", lambda _self: None)
    with pytest.raises(errors.LinkedInputError, match="ResearchRef"):
        linked._validated_research_refs((reference,))
