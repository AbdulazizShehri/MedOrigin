"""Adversarial source-to-package projection checks (no publishing)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage_medorigin_core_projection.py"
EXPECTED_SOURCE_HASH = "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
EXPECTED_LOCK_HASH = "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"


def _run(dest: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(dest)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_exact_committed_source_projection_is_read_only(tmp_path: Path) -> None:
    before = (ROOT / "pyproject.toml").read_bytes()
    assert hashlib.sha256(before).hexdigest() == EXPECTED_SOURCE_HASH
    package = tmp_path / "package"
    cp = _run(package)
    assert cp.returncode == 0, cp.stderr
    result = cast(dict[str, Any], json.loads(cp.stdout))
    assert result["publication_authorized"] is False
    record = json.loads((package / "MEDORIGIN_SOURCE_PROVENANCE.json").read_text())
    assert record["schema"] == "MEDORIGIN-CORE-PROJECTION-1"
    assert record["publication_authorized"] is False
    assert record["source_git_commit"] == result["source_commit"]
    assert record["frozen_pyproject_sha256"] == EXPECTED_SOURCE_HASH
    assert record["frozen_lock_sha256"] == EXPECTED_LOCK_HASH
    root_metadata = tomllib.loads(before.decode("utf-8"))
    package_metadata = tomllib.loads((package / "pyproject.toml").read_text())
    assert root_metadata["project"]["urls"]["Repository"].endswith("/TheHalfMoon/MESC")
    assert package_metadata["project"]["urls"] == {
        "Homepage": "https://github.com/AbdulazizShehri/MedOrigin",
        "Repository": "https://github.com/AbdulazizShehri/MedOrigin",
        "Documentation": "https://github.com/AbdulazizShehri/MedOrigin/tree/main/docs",
        "Issues": "https://github.com/AbdulazizShehri/MedOrigin/issues",
    }
    assert set(package_metadata["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]) == {
        "src/medscale",
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "apps/workspace/LICENSE",
        "MEDORIGIN_SOURCE_PROVENANCE.json",
    }
    assert (ROOT / "pyproject.toml").read_bytes() == before
    assert (package / "LICENSE").read_bytes() == (package / "apps/workspace/LICENSE").read_bytes()
    source_map = record["source_files"]
    assert record["source_file_count"] == len(source_map)
    assert len(source_map) > 100
    for source_path, digest in source_map.items():
        expected = subprocess.run(
            ["git", "show", f"{result['source_commit']}:{source_path}"],
            check=True,
            cwd=ROOT,
            capture_output=True,
        ).stdout
        assert (package / source_path).read_bytes() == expected
        assert hashlib.sha256(expected).hexdigest() == digest


def test_existing_output_is_never_overwritten(tmp_path: Path) -> None:
    dest = tmp_path / "protected"
    dest.mkdir()
    marker = dest / "do-not-change.txt"
    marker.write_text("preserved", encoding="utf-8")
    cp = _run(dest)
    assert cp.returncode == 2
    assert marker.read_text(encoding="utf-8") == "preserved"
    assert not (dest / "pyproject.toml").exists()
