"""Isolated synthetic Git tests for prepublication tag admission."""

import json
import subprocess
import sys
from pathlib import Path
from typing import TypedDict, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_release_tag_main_head.py"


class AdmissionReport(TypedDict):
    status: str
    tag_ref: str
    checkout_sha: str
    protected_main_sha: str
    publication_authorized: bool
    issues: list[str]


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "scratch"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "CI Test")
    git(root, "config", "user.email", "ci@example.invalid")
    (root / "fixture.txt").write_text("one", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "synthetic baseline")
    git(root, "tag", "v0.3.0")
    git(root, "update-ref", "refs/remotes/origin/main", git(root, "rev-parse", "HEAD"))
    return root


def admission(repo: Path, ref: str, sha: str) -> tuple[int, AdmissionReport]:
    result = subprocess.run(
        [sys.executable, str(CHECK), "--repo", str(repo), "--tag-ref", ref, "--event-sha", sha],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stdout, result.stderr
    return result.returncode, cast(AdmissionReport, json.loads(result.stdout))


def test_exact_main_release_tag_is_qualified_only(repo: Path) -> None:
    code, result = admission(repo, "refs/tags/v0.3.0", git(repo, "rev-parse", "HEAD"))
    assert code == 0, result
    assert result["publication_authorized"] is False


def test_unmerged_branch_release_tag_rejected(repo: Path) -> None:
    git(repo, "checkout", "-b", "feature")
    (repo / "feature.txt").write_text("two", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "synthetic feature")
    git(repo, "tag", "v0.3.1")
    code, result = admission(repo, "refs/tags/v0.3.1", git(repo, "rev-parse", "HEAD"))
    assert code == 2, result
    assert "tagged commit is not current protected origin/main HEAD" in result["issues"]


def test_old_main_tag_rejected_after_main_moves(repo: Path) -> None:
    old = git(repo, "rev-parse", "HEAD")
    (repo / "second.txt").write_text("two", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "new main")
    git(repo, "update-ref", "refs/remotes/origin/main", git(repo, "rev-parse", "HEAD"))
    git(repo, "checkout", "--detach", "v0.3.0")
    code, result = admission(repo, "refs/tags/v0.3.0", old)
    assert code == 2, result


def test_tag_at_other_ref_is_rejected(repo: Path) -> None:
    git(repo, "tag", "v0.3.1")
    git(repo, "checkout", "-b", "different")
    (repo / "new.txt").write_text("feature", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "new checkout")
    checkout = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/main", checkout)
    code, report = admission(repo, "refs/tags/v0.3.1", checkout)
    assert code == 2, report
    assert "tag ref does not point to the checked-out commit" in report["issues"]


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/tags/0.3.0", "refs/tags/v../escape"])
def test_nonversion_or_invalid_refs_rejected(repo: Path, ref: str) -> None:
    code, report = admission(repo, ref, git(repo, "rev-parse", "HEAD"))
    assert code == 2
    assert "release admission requires an explicit v-prefixed tag ref" in report["issues"]


def test_release_workflow_gate_is_in_quality_chain() -> None:
    from test_release_workflow_contract import _job_block, _workflow_text

    workflow = _workflow_text()
    gate = _job_block(workflow, "tag-main-admission")
    quality = _job_block(workflow, "quality")
    publish = _job_block(workflow, "github-release")
    index = _job_block(workflow, "testpypi-publish")
    assert "fetch-depth: 0" in gate
    assert "persist-credentials: false" in gate
    assert "scripts/check_release_tag_main_head.py" in gate
    assert '--tag-ref "$GITHUB_REF" --event-sha "$GITHUB_SHA"' in gate
    assert "needs: tag-main-admission" in quality
    assert "needs: [quality, build, install-smoke]" in publish
    assert "needs: github-release" in index
    assert "contents: write" not in gate
    assert "id-token: write" not in gate


def test_mismatched_event_or_missing_main_blocked(repo: Path) -> None:
    code, _ = admission(repo, "refs/tags/v0.3.0", "f" * 40)
    assert code == 2
    git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    code, _ = admission(repo, "refs/tags/v0.3.0", git(repo, "rev-parse", "HEAD"))
    assert code == 2
