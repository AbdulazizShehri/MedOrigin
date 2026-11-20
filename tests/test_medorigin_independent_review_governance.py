"""Strict read-only independent review and main-ruleset admission tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_medorigin_independent_review_governance.py"
SHA = "a" * 40
OLD = "b" * 40


@pytest.fixture
def gate() -> Any:
    spec = importlib.util.spec_from_file_location("medorigin_review_preflight", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def good_rule() -> dict[str, Any]:
    return {
        "id": 20172239,
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "bypass_actors": [],
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "require_last_push_approval": True,
                    "dismiss_stale_reviews_on_push": True,
                    "required_review_thread_resolution": True,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "required_status_checks": [
                        {"context": "quality (py3.11)"},
                        {"context": "quality (py3.12)"},
                        {"context": "analyze (python)"},
                    ],
                },
            },
        ],
    }


@pytest.fixture
def good_pr() -> dict[str, Any]:
    return {
        "head": {"sha": SHA},
        "user": {"login": "Author"},
        "state": "open",
        "draft": False,
    }


@pytest.fixture
def good_reviews() -> list[dict[str, Any]]:
    return [
        {
            "user": {"login": "independent-reviewer", "type": "User"},
            "state": "APPROVED",
            "commit_id": SHA,
        }
    ]


def test_minimal_positive_never_authorizes_publication(
    gate: Any, good_rule: Any, good_pr: Any, good_reviews: Any
) -> None:
    result = gate.assess(good_rule, good_pr, good_reviews)
    assert result["status"] == "REVIEW_GOVERNANCE_PREFLIGHT_PRESENT_ONLY"
    assert result["human_current_head_approvers"] == ["independent-reviewer"]
    assert result["publication_authorized"] is False
    assert result["adr_0045_accepted"] is False
    assert result["independent_security_review_603_completed"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("required_approving_review_count", 0),
        ("require_last_push_approval", False),
        ("dismiss_stale_reviews_on_push", False),
        ("required_review_thread_resolution", False),
    ],
)
def test_refuses_main_review_policy_gaps(
    gate: Any,
    good_rule: Any,
    good_pr: Any,
    good_reviews: Any,
    field: str,
    value: Any,
) -> None:
    good_rule["rules"][2]["parameters"][field] = value
    assert gate.assess(good_rule, good_pr, good_reviews)["status"] == "BLOCKED"


def test_refuses_missing_required_codeql(
    gate: Any, good_rule: Any, good_pr: Any, good_reviews: Any
) -> None:
    good_rule["rules"][3]["parameters"]["required_status_checks"].pop()
    result = gate.assess(good_rule, good_pr, good_reviews)
    assert result["status"] == "BLOCKED"
    assert any("CodeQL" in issue for issue in result["issues"])


def test_refuses_hidden_admin_bypass(
    gate: Any, good_rule: Any, good_pr: Any, good_reviews: Any
) -> None:
    good_rule["bypass_actors"] = None
    assert gate.assess(good_rule, good_pr, good_reviews)["status"] == "BLOCKED"


@pytest.mark.parametrize(
    "reviews",
    [
        [],
        [{"user": {"login": "Author", "type": "User"}, "state": "APPROVED", "commit_id": SHA}],
        [
            {
                "user": {"login": "github-advanced-security[bot]", "type": "Bot"},
                "state": "APPROVED",
                "commit_id": SHA,
            }
        ],
        [
            {
                "user": {"login": "independent-reviewer", "type": "User"},
                "state": "APPROVED",
                "commit_id": OLD,
            }
        ],
        [
            {
                "user": {"login": "independent-reviewer", "type": "User"},
                "state": "COMMENTED",
                "commit_id": SHA,
            }
        ],
        [
            {
                "user": {"login": "independent-reviewer", "type": "User"},
                "state": "APPROVED",
                "commit_id": SHA,
            },
            {
                "user": {"login": "independent-reviewer", "type": "User"},
                "state": "DISMISSED",
                "commit_id": SHA,
            },
        ],
    ],
)
def test_no_fake_independent_approval(
    gate: Any, good_rule: Any, good_pr: Any, reviews: list[dict[str, Any]]
) -> None:
    result = gate.assess(good_rule, good_pr, reviews)
    assert result["status"] == "BLOCKED"
    assert result["human_current_head_approvers"] == []


def test_draft_is_not_release_review_ready(
    gate: Any, good_rule: Any, good_pr: Any, good_reviews: Any
) -> None:
    good_pr["draft"] = True
    assert gate.assess(good_rule, good_pr, good_reviews)["status"] == "BLOCKED"


def test_live_payload_malformed_fail_closed(
    gate: Any, monkeypatch: Any, good_rule: Any, good_pr: Any
) -> None:
    replies = [good_rule, good_pr, {"bad": "pagination"}]
    monkeypatch.setattr(gate, "_gh", lambda *_args, **_kw: replies.pop(0))
    with pytest.raises(ValueError, match="pagination"):
        gate.check("AbdulazizShehri/MedOrigin", 630)


def test_paginated_approvals_are_evaluated(
    gate: Any, monkeypatch: Any, good_rule: Any, good_pr: Any, good_reviews: Any
) -> None:
    replies = [
        good_rule,
        good_pr,
        [[{"user": {"login": "bot[bot]", "type": "Bot"}, "state": "COMMENTED"}], good_reviews],
    ]
    monkeypatch.setattr(gate, "_gh", lambda *_args, **_kw: replies.pop(0))
    result = gate.check("AbdulazizShehri/MedOrigin", 630)
    assert result["status"] == "REVIEW_GOVERNANCE_PREFLIGHT_PRESENT_ONLY"


def test_real_governance_never_assumed_authorized_without_admin(
    gate: Any, good_rule: Any, good_pr: Any, good_reviews: Any
) -> None:
    good_rule["rules"][2]["parameters"]["required_approving_review_count"] = 0
    good_rule["bypass_actors"] = None
    good_pr["draft"] = True
    result = gate.assess(good_rule, good_pr, good_reviews)
    assert result["status"] == "BLOCKED"
    assert result["publication_authorized"] is False
    assert len(result["issues"]) >= 3


@pytest.mark.parametrize(
    ("rule_index", "broken_parameters"),
    [(2, None), (2, {"required_approving_review_count": "1"}), (3, None)],
)
def test_malformed_ruleset_params_fail_closed(
    gate: Any,
    good_rule: Any,
    good_pr: Any,
    good_reviews: Any,
    rule_index: int,
    broken_parameters: Any,
) -> None:
    good_rule["rules"][rule_index]["parameters"] = broken_parameters
    result = gate.assess(good_rule, good_pr, good_reviews)
    assert result["status"] == "BLOCKED"
    assert result["publication_authorized"] is False


def test_malformed_review_entries_fail_closed(
    gate: Any, good_rule: Any, good_pr: Any, good_reviews: Any
) -> None:
    # Mixed server responses must not be accepted merely because another
    # review object happens to contain an apparently eligible approval.
    result = gate.assess(good_rule, good_pr, [good_reviews[0], "malformed"])
    assert result["status"] == "BLOCKED"
    assert "malformed PR review entry" in result["issues"]
    assert result["publication_authorized"] is False
