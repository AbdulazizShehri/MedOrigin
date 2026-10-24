"""Read-only prepublication check for enforced GitHub release-tag protection.

Requires a GitHub CLI identity authorized to read complete ruleset details,
including bypass_actors. GitHub can mask this field to non-admin callers,
including the default Actions GITHUB_TOKEN. Unverifiable bypass metadata
must block tag admission until a separately governed privileged read-only
verification path is available. No rule creation, release or tag writes.
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


def qualifies_ruleset(ruleset: dict[str, Any]) -> bool:
    """Admit only an active tag ruleset that clearly covers *all* v-tags."""
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
    bypass_actors = ruleset.get("bypass_actors")
    if not isinstance(bypass_actors, list) or any(
        not isinstance(actor, dict) or actor != ALLOWED_BYPASS for actor in bypass_actors
    ):
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
) -> dict[str, Any]:
    problems: list[str] = []
    qualifying: list[int] = []
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
                    if qualifies_ruleset(details):
                        qualifying.append(identifier)
                if len(summaries) < 100:
                    break
            else:
                raise ValueError("ruleset pagination budget exceeded")
        except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError):
            problems.append("could not verify repository and inherited tag rulesets")
    if not qualifying:
        problems.append("active v-tag creation/update/deletion ruleset absent or unverifiable")
    return {
        "status": "RELEASE_TAG_RULESET_PRESENT_ONLY" if not problems else "BLOCKED",
        "repository": repository,
        "tag_ref": tag_ref,
        "matching_ruleset_ids": sorted(set(qualifying)),
        "bypass_actors_verified": bool(qualifying),
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
    options = parser.parse_args()
    result = inspect(options.repository, options.tag_ref, _gh_get)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "RELEASE_TAG_RULESET_PRESENT_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
