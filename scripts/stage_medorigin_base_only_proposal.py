"""Prepare an unpublished, UNAPPROVED base-only packaging *proposal*.

Derives from the accepted read-only ADR-0044 Core projection and removes
the exact immutable optional dependency section in a separate scratch tree.
This extends the founder-accepted four-URL transformation and MUST NOT be
mistaken for a qualified publisher or an already-accepted ADR amendment.

Nothing changes the canonical scientific root, dependency lock or receipts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
import tomllib
from pathlib import Path

from stage_medorigin_core_projection import ROOT, ProjectionError, stage

_OPTIONAL_HEADER = "[project.optional-dependencies]\n"
_NEXT_HEADER = "[dependency-groups]"
_OPTIONAL_BLOCK_SHA256 = "8c0db866843e15ec75b764dfff4b4d983856d1e2c6f95f4427f576427e54378a"


class BaseOnlyProposalError(ValueError):
    """Fail closed when the source-projected metadata is unexpected."""


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def strip_exact_optional_section(content: bytes) -> tuple[bytes, str]:
    try:
        source = content.decode("utf-8")
        if source.count(_OPTIONAL_HEADER) != 1:
            raise BaseOnlyProposalError("expected exactly one optional extras section")
        begin = source.index(_OPTIONAL_HEADER)
        end = source.index(_NEXT_HEADER, begin)
        if source.count(_NEXT_HEADER) != 1:
            raise BaseOnlyProposalError("unexpected dependency group layout")
        removed = source[begin:end]
        if sha(removed.encode("utf-8")) != _OPTIONAL_BLOCK_SHA256:
            raise BaseOnlyProposalError("optional research-extras metadata drift")
        successor = (source[:begin] + source[end:]).encode("utf-8")
        before = tomllib.loads(source)
        after = tomllib.loads(successor.decode("utf-8"))
        if not isinstance(before.get("project", {}).get("optional-dependencies"), dict):
            raise BaseOnlyProposalError("missing expected optional dependency map")
        expected = copy.deepcopy(before)
        expected["project"].pop("optional-dependencies")
        if expected != after or after["project"].get("dependencies", []):
            raise BaseOnlyProposalError("unexpected metadata transformation")
        if "optional-dependencies" in after["project"]:
            raise BaseOnlyProposalError("optional dependencies not fully removed")
        return successor, sha(removed.encode("utf-8"))
    except (UnicodeError, KeyError, ValueError, TypeError) as exc:
        if isinstance(exc, BaseOnlyProposalError):
            raise
        raise BaseOnlyProposalError("unsafe or malformed source metadata") from exc


def propose(target: Path) -> dict[str, object]:
    target = target.resolve()
    if target.exists() or target == ROOT or ROOT in target.parents:
        raise BaseOnlyProposalError("refuse existing or in-repository proposal output")
    with tempfile.TemporaryDirectory(prefix="medorigin-base-only-proposal-") as scratch:
        temp = Path(scratch) / "source"
        upstream = stage(temp)
        original = (temp / "pyproject.toml").read_bytes()
        modified, removed_sha = strip_exact_optional_section(original)
        receipt_file = temp / "MEDORIGIN_SOURCE_PROVENANCE.json"
        record = json.loads(receipt_file.read_text(encoding="utf-8"))
        if (
            record.get("schema") != "MEDORIGIN-CORE-PROJECTION-1"
            or record.get("source_git_commit") != upstream["source_commit"]
            or record.get("projected_pyproject_sha256") != sha(original)
            or record.get("publication_authorized") is not False
        ):
            raise BaseOnlyProposalError("upstream qualified provenance mismatch")
        record.update(
            {
                "schema": "MEDORIGIN-CORE-BASE-ONLY-PROPOSAL-1",
                "parent_projected_pyproject_sha256": sha(original),
                "projected_pyproject_sha256": sha(modified),
                "removed_optional_section_sha256": removed_sha,
                "scope": "synthetic_only_base_core",
                "adr_0044_amendment_accepted": False,
                "independent_security_review_completed": False,
                "publication_authorized": False,
                "status": "UNPUBLISHED_PROPOSAL_NOT_ACCEPTED",
            }
        )
        (temp / "pyproject.toml").write_bytes(modified)
        # Windows text mode translates LF to CRLF; byte-oriented encoding
        # makes independently rebuilt proposal sdist receipts platform-stable.
        receipt_file.write_bytes(
            (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise BaseOnlyProposalError("destination appeared during staging")
        temp.rename(target)
        return {
            "status": "BASE_ONLY_PROPOSAL_NOT_QUALIFIED",
            "source_git_commit": upstream["source_commit"],
            "projection_variant": record["schema"],
            "projected_pyproject_sha256": sha(modified),
            "removed_optional_section_sha256": removed_sha,
            "publication_authorized": False,
            "adr_amendment_accepted": False,
            "staged_path": str(target),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = propose(args.out)
    except (OSError, ProjectionError, BaseOnlyProposalError, json.JSONDecodeError) as exc:
        print(f"BASE_ONLY_PROPOSAL_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
