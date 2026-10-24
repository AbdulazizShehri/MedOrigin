"""Negative and positive checks for read-only GitHub tag ruleset admission."""

from __future__ import annotations

import runpy
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

REPOSITORY = "AbdulazizShehri/MedOrigin"
TAG = "refs/tags/v0.3.0"
# Load the CLI script by path: mypy also checks scripts/ as standalone files,
# so importing it under a second dotted module name would duplicate sources.
_inspect = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "check_release_tag_governance.py")
)["inspect"]
inspect = cast(Callable[[str, str, Callable[[str], Any]], dict[str, Any]], _inspect)


def _details(
    *,
    target: str = "tag",
    enforcement: str = "active",
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    types: tuple[str, ...] = ("creation", "update", "deletion"),
    bypass: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "target": target,
        "enforcement": enforcement,
        "conditions": {
            "ref_name": {
                "include": ["refs/tags/v*"] if include is None else include,
                "exclude": [] if exclude is None else exclude,
            }
        },
        "rules": [{"type": name} for name in types],
        "bypass_actors": [] if bypass is None else bypass,
    }


def _stub(details: dict[str, Any] | None) -> Callable[[str], Any]:
    def fetch(path: str) -> Any:
        if "/rulesets?" in path:
            return [{"id": 42, "enforcement": "active"}] if details is not None else []
        assert "/rulesets/42?" in path, path
        return details

    return fetch


def test_complete_active_tag_ruleset_is_prepublication_only() -> None:
    result = inspect(REPOSITORY, TAG, _stub(_details()))
    assert result["status"] == "RELEASE_TAG_RULESET_PRESENT_ONLY", result
    assert result["issues"] == []
    assert result["matching_ruleset_ids"] == [42]
    assert result["publication_authorized"] is False
    assert result["bypass_actors_verified"] is True


@pytest.mark.parametrize(
    "bad",
    [
        _details(target="branch"),
        _details(enforcement="disabled"),
        _details(include=["refs/tags/v0.3.*"]),
        _details(exclude=["refs/tags/v1*"]),
        _details(types=("creation", "deletion")),
        _details(types=("creation", "update")),
        _details(types=("update", "deletion")),
    ],
)
def test_partial_or_inapplicable_protection_is_refused(bad: dict[str, Any]) -> None:
    result = inspect(REPOSITORY, TAG, _stub(bad))
    assert result["status"] == "BLOCKED"
    assert result["publication_authorized"] is False


@pytest.mark.parametrize(
    "bypass",
    [
        [{"actor_id": 4, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
        [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}],
        [{"actor_id": 5, "actor_type": "Team", "bypass_mode": "always"}],
        [
            {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"},
            {"actor_id": 4, "actor_type": "RepositoryRole", "bypass_mode": "always"},
        ],
    ],
)
def test_non_admin_bypass_never_qualifies_tag_ruleset(
    bypass: list[dict[str, Any]],
) -> None:
    result = inspect(REPOSITORY, TAG, _stub(_details(bypass=bypass)))
    assert result["status"] == "BLOCKED", result
    assert result["publication_authorized"] is False
    assert result["bypass_actors_verified"] is False


def test_ruleset_without_bypass_metadata_is_rejected() -> None:
    details = _details()
    del details["bypass_actors"]
    result = inspect(REPOSITORY, TAG, _stub(details))
    assert result["status"] == "BLOCKED", result
    assert result["bypass_actors_verified"] is False


def test_admin_only_bypass_is_verified_without_authorizing_publication() -> None:
    result = inspect(
        REPOSITORY,
        TAG,
        _stub(
            _details(
                bypass=[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]
            )
        ),
    )
    assert result["status"] == "RELEASE_TAG_RULESET_PRESENT_ONLY", result
    assert result["bypass_actors_verified"] is True
    assert result["publication_authorized"] is False


def test_only_main_branch_ruleset_is_refused() -> None:
    result = inspect(REPOSITORY, TAG, _stub(None))
    assert result["status"] == "BLOCKED"
    assert result["matching_ruleset_ids"] == []


def test_unavailable_repository_ruleset_api_fails_closed() -> None:
    def broken_fetch(_path: str) -> Any:
        raise subprocess.CalledProcessError(1, ["gh", "api"])

    result = inspect(REPOSITORY, TAG, broken_fetch)
    assert result["status"] == "BLOCKED"
    assert "could not verify" in " ".join(result["issues"])


@pytest.mark.parametrize(
    "repository,ref",
    [
        ("org/repo;malicious", TAG),
        (REPOSITORY, "refs/heads/main"),
        (REPOSITORY, "refs/tags/unknown"),
    ],
)
def test_noncanonical_input_never_calls_api(repository: str, ref: str) -> None:
    def forbidden(_path: str) -> Any:
        raise AssertionError("unsafe API call")

    result = inspect(repository, ref, forbidden)
    assert result["status"] == "BLOCKED"


def test_tag_ruleset_admission_is_before_release_quality_gate() -> None:
    from test_release_workflow_contract import _job_block, _workflow_text

    text = _workflow_text()
    block = _job_block(text, "tag-ruleset-admission")
    quality = _job_block(text, "quality")
    assert "if: github.event_name == 'push'" in block
    assert "needs: tag-main-admission" in block
    assert "persist-credentials: false" in block
    assert "GH_TOKEN: ${{ github.token }}" in block
    assert "scripts/check_release_tag_governance.py" in block
    assert "id-token: write" not in block
    assert "contents: write" not in block
    assert "needs: [tag-main-admission, tag-ruleset-admission]" in quality
