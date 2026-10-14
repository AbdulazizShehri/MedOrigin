"""Workspace packaging version authority and legacy API compatibility.

The standalone Workspace distribution has its own build configuration. Its
version must come from the package's existing public __version__ and never
be independently repeated in packaging metadata.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_WORKSPACE = _ROOT / "apps" / "workspace"
_VERSION_FILE = Path("src/medscale_workspace/__init__.py")


def _version_from_source() -> str:
    source = (_WORKSPACE / _VERSION_FILE).read_text(encoding="utf-8")
    module = ast.parse(source)
    versions = [
        value
        for node in module.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id == "__version__"
        for value in [ast.literal_eval(node.value)]
    ]
    assert len(versions) == 1, "exactly one authoritative runtime version is required"
    version = versions[0]
    assert isinstance(version, str)
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:\.dev\d+)?", version)
    return version


def test_workspace_version_is_single_sourced_from_public_runtime_version() -> None:
    configuration = tomllib.loads((_WORKSPACE / "pyproject.toml").read_text(encoding="utf-8"))
    project = configuration["project"]
    hatch_version = configuration["tool"]["hatch"]["version"]

    assert project["dynamic"] == ["version"]
    assert "version" not in project
    assert hatch_version == {"path": _VERSION_FILE.as_posix()}
    assert _version_from_source() == "0.1.0.dev1"


def test_workspace_legacy_package_identity_and_dependency_stay_unchanged() -> None:
    configuration = tomllib.loads((_WORKSPACE / "pyproject.toml").read_text(encoding="utf-8"))
    project = configuration["project"]

    assert project["name"] == "medscale-workspace"
    assert project["dependencies"] == ["cryptography==50.0.1"]
    assert configuration["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/medscale_workspace"
    ]
    assert "MedOrigin" in project["description"]
    assert "synthetic-only" in project["description"].lower()
