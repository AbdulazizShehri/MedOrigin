"""The proposed base-only metadata projection never changes frozen research."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/stage_medorigin_base_only_proposal.py"
FROZEN_PROJECT_SHA = "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
FROZEN_LOCK_SHA = "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


@pytest.fixture
def proposal() -> Any:
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location("medorigin_base_only_proposal", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT.parent))


def test_proposal_removes_exact_extras_only(proposal: Any) -> None:
    original = (ROOT / "pyproject.toml").read_bytes()
    assert sha(original) == FROZEN_PROJECT_SHA
    successor, removed_sha = proposal.strip_exact_optional_section(original)
    old = tomllib.loads(original.decode())
    new = tomllib.loads(successor.decode())
    assert old["project"]["optional-dependencies"]
    assert "optional-dependencies" not in new["project"]
    old["project"].pop("optional-dependencies")
    assert old == new
    assert removed_sha == proposal._OPTIONAL_BLOCK_SHA256
    assert sha((ROOT / "pyproject.toml").read_bytes()) == FROZEN_PROJECT_SHA


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "dependency rewrite",
        "malicious metadata injection",
    ],
)
def test_mutation_attempts_fail_closed(proposal: Any, mutation: str) -> None:
    original = (ROOT / "pyproject.toml").read_bytes().decode()
    header = "[project.optional-dependencies]\n"
    if mutation == "missing":
        changed = original.replace(header, "[project.optional-UNKNOWN]\n")
    elif mutation == "duplicate":
        changed = original.replace(header, header + header)
    elif mutation == "dependency rewrite":
        changed = original.replace("pillow==12.3.0", "pillow==13.0.0")
    else:
        changed = original.replace(header, header + 'malicious = ["extra>=1"]\n')
    with pytest.raises(proposal.BaseOnlyProposalError):
        proposal.strip_exact_optional_section(changed.encode())


def test_no_in_place_source_target(proposal: Any) -> None:
    with pytest.raises(proposal.BaseOnlyProposalError):
        proposal.propose(ROOT / "stage-inside-repo-refused")
    with pytest.raises(proposal.BaseOnlyProposalError):
        proposal.propose(ROOT)


def test_source_bound_proposal_receipt_and_no_overwrite(
    proposal: Any,
    tmp_path: Path,
) -> None:
    target = tmp_path / "proposed"
    result = proposal.propose(target)
    assert result["status"] == "BASE_ONLY_PROPOSAL_NOT_QUALIFIED"
    assert result["publication_authorized"] is False
    assert result["adr_amendment_accepted"] is False
    root = (ROOT / "pyproject.toml").read_bytes()
    lock = (ROOT / "uv.lock").read_bytes()
    assert sha(root) == FROZEN_PROJECT_SHA
    assert sha(lock) == FROZEN_LOCK_SHA
    staged = tomllib.loads((target / "pyproject.toml").read_text(encoding="utf-8"))
    assert not staged["project"].get("optional-dependencies")
    receipt_bytes = (target / "MEDORIGIN_SOURCE_PROVENANCE.json").read_bytes()
    receipt = json.loads(receipt_bytes)
    assert receipt_bytes == (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    assert b"\r" not in receipt_bytes
    assert (target / ".gitignore").read_bytes() == b""
    assert receipt["staged_vcs_ignore_sha256"] == sha(b"")
    assert receipt["schema"] == "MEDORIGIN-CORE-BASE-ONLY-PROPOSAL-1"
    assert receipt["publication_authorized"] is False
    assert receipt["adr_0044_amendment_accepted"] is False
    assert receipt["independent_security_review_completed"] is False
    assert receipt["projected_pyproject_sha256"] == sha((target / "pyproject.toml").read_bytes())
    assert (
        receipt["source_git_commit"]
        == subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    with pytest.raises(proposal.BaseOnlyProposalError):
        proposal.propose(target)
    assert sha(root) == FROZEN_PROJECT_SHA


def test_no_release_capabilities_in_proposal() -> None:
    contents = SCRIPT.read_text(encoding="utf-8")
    for operation in ("git push", "gh release create", "twine upload", "hf upload"):
        assert operation not in contents
