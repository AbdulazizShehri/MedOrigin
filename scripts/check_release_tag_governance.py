"""Read-only prepublication check for enforced GitHub release-tag protection.

Default mode checks active tag protection only using GitHub's read-only
GITHUB_TOKEN; it NEVER claims bypass actor verification or publication
authorization when bypass metadata is masked. Explicit --verify-bypass-actors
requires a repository administrator's read-only ruleset inspection and fails
closed on unverified or non-admin bypass roles. Never put administrator
credentials into workflows triggered by untrusted PRs. No GitHub writes.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Callable
from typing import Any

REQUIRED_RULES = frozenset({"creation", "update", "deletion"})
CONSERVATIVE_V_TAG_TARGETS = frozenset({"~ALL", "refs/tags/v*", "refs/tags/*"})
# GitHub repository role ID 5 is Administrator. Broader or unknown bypasses
# must not satisfy a release-tag governance check.
ALLOWED_BYPASS = {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}


def _bypass_is_narrow(ruleset: dict[str, Any]) -> bool:
    actors = ruleset.get("bypass_actors")
    return isinstance(actors, list) and all(
        isinstance(actor, dict) and actor == ALLOWED_BYPASS for actor in actors
    )


def qualifies_ruleset(ruleset: dict[str, Any], *, require_bypass_actors: bool = False) -> bool:
    """Check active v-tag protection; optionally enforce admin-only bypass."""
    if ruleset.get("target") != "tag" or ruleset.get("enforcement") != "active":
        return False
    conditions = ruleset.get("conditions")
    if not isinstance(conditions, dict):
        return False
    names = conditions.get("ref_name")
    if not isinstance(names, dict):
        return False
    include, exclude = names.get("include"), names.get("exclude")
    if not isinstance(include, list) or not isinstance(exclude, list):
        return False
    if exclude or not any(v in CONSERVATIVE_V_TAG_TARGETS for v in include):
        return False
    if require_bypass_actors and not _bypass_is_narrow(ruleset):
        return False
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        return False
    types = {v.get("type") for v in rules if isinstance(v, dict)}
    return REQUIRED_RULES.issubset(types)


def inspect(
    repository: str,
    tag_ref: str,
    fetch_json: Callable[[str], Any],
    *,
    require_bypass_actors: bool = False,
) -> dict[str, Any]:
    problems: list[str] = []
    qualifying: list[int] = []
    bypass_verified: list[int] = []
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) is None:
        problems.append("invalid GitHub owner/repository")
    if re.fullmatch(r"refs/tags/v[0-9][A-Za-z0-9.+_-]*", tag_ref) is None:
        problems.append("explicit release v-tag required")
    if not problems:
        try:
            # GH REST supports pagination; includes_parents includes org rules.
            for page in range(1, 6):
                summaries = fetch_json(
                    f"repos/{repository}/rulesets?includes_parents=true&per_page=100&page={page}"
                )
                if not isinstance(summaries, list):
                    raise ValueError("unexpected GitHub rulesets list")
                for summary in summaries:
                    if not isinstance(summary, dict):
                        raise ValueError("invalid ruleset summary")
                    if summary.get("enforcement") != "active":
                        continue
                    identifier = summary.get("id")
                    if not isinstance(identifier, int) or identifier <= 0:
                        raise ValueError("invalid ruleset id")
                    details = fetch_json(
                        f"repos/{repository}/rulesets/{identifier}?includes_parents=true"
                    )
                    if not isinstance(details, dict):
                        raise ValueError("unexpected GitHub ruleset details")
                    if qualifies_ruleset(details, require_bypass_actors=require_bypass_actors):
                        qualifying.append(identifier)
                        if _bypass_is_narrow(details):
                            bypass_verified.append(identifier)
                if len(summaries) < 100:
                    break
            else:
                raise ValueError("ruleset pagination budget exceeded")
        except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError):
            problems.append("could not verify repository and inherited tag rulesets")
    if not qualifying:
        problems.append("active v-tag creation/update/deletion ruleset absent or unverifiable")
        if require_bypass_actors:
            problems.append("admin-only bypass actor verification failed or unavailable")
    return {
        "status": "RELEASE_TAG_RULESET_PRESENT_ONLY" if not problems else "BLOCKED",
        "repository": repository,
        "tag_ref": tag_ref,
        "matching_ruleset_ids": sorted(set(qualifying)),
        "bypass_actors_verified": bool(bypass_verified),
        "publication_authorized": False,
        "issues": problems,
    }


def _gh_get(path: str) -> Any:
    response = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return json.loads(response.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag-ref", required=True)
    parser.add_argument(
        "--verify-bypass-actors",
        action="store_true",
        help="Require admin-visible, admin-only bypass roles (manual prepublication gate)",
    )
    options = parser.parse_args()
    result = inspect(
        options.repository,
        options.tag_ref,
        _gh_get,
        require_bypass_actors=options.verify_bypass_actors,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "RELEASE_TAG_RULESET_PRESENT_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
