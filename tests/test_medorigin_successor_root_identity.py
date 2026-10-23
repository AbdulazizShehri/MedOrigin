"""Independent, append-only predecessor/successor package identity contract."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs" / "releases" / "successor_root_identity_candidate_20261023.json"
FROZEN = ROOT / "specs" / "mesc-experiment-0" / "mrl-0809-static-prerequisites-v1.json"
OLD_ROOT_HASH = "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
LOCK_HASH = "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _record() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(RECORD.read_text(encoding="utf-8")))


def test_successor_does_not_rewrite_frozen_evidence() -> None:
    record = _record()
    assert record["schema"] == "MEDORIGIN-RELEASE-ROOT-SUCCESSOR-CANDIDATE-V1"
    assert record["status"] == "PROPOSED_UNPUBLISHED"
    predecessor = record["predecessor"]
    assert predecessor["pyproject_sha256"] == OLD_ROOT_HASH
    assert predecessor["uv_lock_sha256"] == LOCK_HASH
    assert _hash(FROZEN) == predecessor["static_manifest_sha256"]
    historical = json.loads(FROZEN.read_text(encoding="utf-8"))
    old_root = [x for x in historical["sources"] if x["path"] == "pyproject.toml"]
    assert len(old_root) == 1 and old_root[0]["sha256"] == OLD_ROOT_HASH
    assert historical["dependency_lock_sha256"] == LOCK_HASH
    assert _hash(ROOT / "uv.lock") == LOCK_HASH


def test_new_distribution_identity_is_truthful_and_stable() -> None:
    record = _record()
    successor = record["successor"]
    assert _hash(ROOT / "pyproject.toml") == successor["pyproject_sha256"]
    assert successor["uv_lock_sha256"] == LOCK_HASH
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == successor["distribution"] == "medscale"
    assert data["project"]["dynamic"] == ["version"]
    base = "https://github.com/AbdulazizShehri/MedOrigin"
    assert successor["canonical_repository"] == base
    assert data["project"]["urls"] == {
        "Homepage": base,
        "Repository": base,
        "Documentation": base + "/tree/main/docs",
        "Issues": base + "/issues",
    }
    expected = ["src/medscale", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"]
    assert successor["sdist_explicit_only_include"] == expected
    assert data["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"] == expected
    assert (ROOT / "src" / "medscale" / "__about__.py").read_text(
        encoding="utf-8"
    ).strip() == '__version__ = "0.3.0"'


def test_publication_stays_off_and_release_archive_is_qualified() -> None:
    record = _record()
    assert "NO_AUTO_PUBLICATION" in record["prohibitions"]
    assert "NO_TAG" in record["prohibitions"]
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert workflow.count("scripts/inspect_release_wheel_metadata.py --wheel") == 2
    assert workflow.count("scripts/check_sdist_publication_scope.py --sdist") == 2
    assert "vars.GITHUB_RELEASE_PUBLISH_ENABLED == 'true'" in workflow
    assert "vars.TESTPYPI_PUBLISH_ENABLED == 'true'" in workflow
    assert (ROOT / "docs" / "adr" / "0043-release-root-successor-identity.md").is_file()
