"""Read-only main-branch independent-review preflight for MedOrigin.

This diagnostic does not modify GitHub controls and never approves publication.
It requires a non-author human APPROVED review at the exact current PR head,
an active protected-main ruleset, one mandatory review, last-push approval,
and the existing mandatory security/quality checks. This is necessary but NOT
sufficient for the independent security judgment in issue #603.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from typing import Any

EXPECTED_CHECKS = frozenset({"quality (py3.11)", "quality (py3.12)", "analyze (python)"})
DEFAULT_RULESET_ID = 20172239


def assess(
    ruleset: dict[str, Any], pull: dict[str, Any], reviews: Sequence[object]
) -> dict[str, Any]:
    issues: list[str] = []
    conditions = ruleset.get("conditions")
    refs = conditions.get("ref_name") if isinstance(conditions, dict) else None
    if (
        ruleset.get("target") != "branch"
        or ruleset.get("enforcement") != "active"
        or not isinstance(refs, dict)
        or "refs/heads/main" not in refs.get("include", [])
        or refs.get("exclude") != []
    ):
        issues.append("active exact-main branch ruleset absent or incomplete")
    rules = ruleset.get("rules")
    mapped = (
        {rule.get("type"): rule.get("parameters", {}) for rule in rules if isinstance(rule, dict)}
        if isinstance(rules, list)
        else {}
    )
    if not {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}.issubset(
        mapped
    ):
        issues.append("required main-branch mutation protections missing")
    pr_rule = mapped.get("pull_request")
    if not isinstance(pr_rule, dict):
        pr_rule = {}
    approvals = pr_rule.get("required_approving_review_count")
    if type(approvals) is not int or approvals < 1:
        issues.append("main requires fewer than one approving review")
    if pr_rule.get("require_last_push_approval") is not True:
        issues.append("last-push approval not required on main")
    if pr_rule.get("dismiss_stale_reviews_on_push") is not True:
        issues.append("stale PR approvals not dismissed after push")
    if pr_rule.get("required_review_thread_resolution") is not True:
        issues.append("review-thread resolution not required")
    checks = mapped.get("required_status_checks")
    if not isinstance(checks, dict):
        checks = {}
    required = checks.get("required_status_checks")
    contexts = (
        {
            entry.get("context")
            for entry in required
            if isinstance(entry, dict) and isinstance(entry.get("context"), str)
        }
        if isinstance(required, list)
        else set()
    )
    if checks.get(
        "strict_required_status_checks_policy"
    ) is not True or not EXPECTED_CHECKS.issubset(contexts):
        issues.append("strict required quality and CodeQL checks not enforced")
    # Non-admin tokens may receive null for bypass_actors. Do not assert
    # release authorization from this result even if other checks pass.
    if ruleset.get("bypass_actors") is None:
        issues.append("ruleset bypass actors unavailable to read-only token")
    elif ruleset.get("bypass_actors") != []:
        issues.append("main ruleset contains unreviewed bypass actors")
    head = pull.get("head")
    sha = head.get("sha") if isinstance(head, dict) else None
    author = pull.get("user")
    author_login = author.get("login") if isinstance(author, dict) else None
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        issues.append("pull request head SHA invalid")
    if not isinstance(author_login, str) or not author_login:
        issues.append("pull request author cannot be verified")
    if pull.get("state") != "open" or pull.get("draft") is not False:
        issues.append("pull request is not open and review-ready")
    # GitHub reviews are ordered by submission. Ignore COMMENTED and PENDING:
    # they are not approval decisions and do not revoke earlier approval.
    # CHANGES_REQUESTED and DISMISSED revoke a prior approval by that user.
    reviewers: dict[str, bool] = {}
    for review in reviews:
        if not isinstance(review, dict):
            issues.append("malformed PR review entry")
            continue
        user = review.get("user")
        if not isinstance(user, dict):
            continue
        login = user.get("login")
        if (
            not isinstance(login, str)
            or not login
            or login.casefold() == str(author_login).casefold()
            or login.endswith("[bot]")
            or user.get("type") != "User"
        ):
            continue
        state = review.get("state")
        if state == "APPROVED":
            # An approval on a prior commit is NOT admission for new code.
            reviewers[login.casefold()] = review.get("commit_id") == sha
        elif state in {"CHANGES_REQUESTED", "DISMISSED"}:
            reviewers[login.casefold()] = False
    qualified = sorted(name for name, approved in reviewers.items() if approved)
    if not qualified:
        issues.append("no independent human APPROVED review at exact PR head")
    return {
        "status": "REVIEW_GOVERNANCE_PREFLIGHT_PRESENT_ONLY" if not issues else "BLOCKED",
        "candidate_head_sha": sha,
        "ruleset_id": ruleset.get("id"),
        "human_current_head_approvers": qualified,
        "issues": sorted(set(issues)),
        "independent_security_review_603_completed": False,
        "adr_0045_accepted": False,
        "publication_authorized": False,
    }


def _gh(path: str, *, paginate: bool = False) -> Any:
    args = ["gh", "api"]
    if paginate:
        args.extend(["--paginate", "--slurp"])
    args.append(path)
    result = subprocess.run(args, capture_output=True, text=True, check=True, timeout=45)
    return json.loads(result.stdout)


def check(repository: str, pr_number: int, ruleset_id: int = DEFAULT_RULESET_ID) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or pr_number < 1:
        raise ValueError("invalid exact repository or PR number")
    ruleset = _gh(f"repos/{repository}/rulesets/{ruleset_id}?includes_parents=true")
    pull = _gh(f"repos/{repository}/pulls/{pr_number}")
    pages = _gh(f"repos/{repository}/pulls/{pr_number}/reviews?per_page=100", paginate=True)
    if not isinstance(ruleset, dict) or not isinstance(pull, dict):
        raise ValueError("unexpected GitHub API ruleset or pull request")
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise ValueError("incomplete review pagination")
    reviews = [entry for page in pages for entry in page]
    if len(reviews) > 5000:
        raise ValueError("review history exceeds bounded admission budget")
    return assess(ruleset, pull, reviews)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="AbdulazizShehri/MedOrigin")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--ruleset-id", type=int, default=DEFAULT_RULESET_ID)
    args = parser.parse_args(argv)
    try:
        result = check(args.repository, args.pr, args.ruleset_id)
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        result = {
            "status": "BLOCKED",
            "issues": [f"unverifiable read-only GitHub governance: {exc.__class__.__name__}"],
            "independent_security_review_603_completed": False,
            "adr_0045_accepted": False,
            "publication_authorized": False,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "REVIEW_GOVERNANCE_PREFLIGHT_PRESENT_ONLY" else 2


if __name__ == "__main__":
    sys.exit(main())
