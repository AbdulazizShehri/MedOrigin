"""Reject release tags that do not select the exact protected main HEAD.

This is a read-only, fail-closed prepublication admission gate. It never
creates tags, fetches from the network, enables publishers or signs releases.
The invoking GitHub checkout MUST include all branch refs (fetch-depth: 0).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

MAIN_REF = "refs/remotes/origin/main"
TAG_PATTERN = re.compile(r"refs/tags/v[0-9][A-Za-z0-9.+_-]*")


def _rev_parse(repository: Path, ref: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", ref],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def inspect(repository: Path, *, tag_ref: str, event_sha: str) -> dict[str, object]:
    issues: list[str] = []
    checkout = ""
    protected_main = ""
    if TAG_PATTERN.fullmatch(tag_ref) is None:
        issues.append("release admission requires an explicit v-prefixed tag ref")
    if re.fullmatch(r"[0-9a-f]{40}", event_sha) is None:
        issues.append("release event commit SHA is not canonical")
    try:
        checkout = _rev_parse(repository, "HEAD")
        # The workflow must fetch the complete origin/main ref from GitHub;
        # a missing or inaccessible ref blocks instead of guessing.
        protected_main = _rev_parse(repository, MAIN_REF)
        if checkout != protected_main:
            issues.append("tagged commit is not current protected origin/main HEAD")
        if checkout != event_sha:
            issues.append("GitHub event SHA does not match the checked-out commit")
        if TAG_PATTERN.fullmatch(tag_ref) is not None:
            tag_commit = _rev_parse(repository, tag_ref + "^{commit}")
            if checkout != tag_commit:
                issues.append("tag ref does not point to the checked-out commit")
    except (OSError, subprocess.CalledProcessError, ValueError):
        issues.append("cannot independently resolve tag, checkout or protected main")
    return {
        "status": "TAG_ON_PROTECTED_MAIN_ONLY" if not issues else "BLOCKED",
        "tag_ref": tag_ref,
        "checkout_sha": checkout,
        "protected_main_sha": protected_main,
        "publication_authorized": False,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--tag-ref", required=True)
    parser.add_argument("--event-sha", required=True)
    args = parser.parse_args(argv)
    result = inspect(args.repo, tag_ref=args.tag_ref, event_sha=args.event_sha)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "TAG_ON_PROTECTED_MAIN_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
