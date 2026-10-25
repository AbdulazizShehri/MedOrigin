"""Adversarial, synthetic-only tests for fail-closed publisher artifact admission."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_base_core_publication_scope.py"


@pytest.fixture
def checker() -> Any:
    spec = importlib.util.spec_from_file_location("medorigin_publish_scope", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def metadata(
    *,
    name: str = "medscale",
    version: str = "0.3.0",
    extra: str | None = None,
    dependency: str | None = None,
    dynamic: str | None = None,
    duplicate_name: bool = False,
) -> bytes:
    doc = EmailMessage()
    doc["Metadata-Version"] = "2.3"
    doc["Name"] = name
    doc["Version"] = version
    if extra is not None:
        doc["Provides-Extra"] = extra
    if dependency is not None:
        doc["Requires-Dist"] = dependency
    if dynamic is not None:
        doc["Dynamic"] = dynamic
    if duplicate_name:
        doc["Name"] = name
    return doc.as_bytes()


def make_dist(
    folder: Path,
    *,
    wheel: bytes | None = None,
    sdist: bytes | None = None,
    duplicate_wheel: bool = False,
    symlink_sdist: bool = False,
) -> Path:
    folder.mkdir(exist_ok=True)
    if wheel is None:
        wheel = metadata()
    if sdist is None:
        sdist = metadata()
    with zipfile.ZipFile(folder / "medscale-0.3.0-py3-none-any.whl", "w") as z:
        z.writestr("medscale-0.3.0.dist-info/METADATA", wheel)
        if duplicate_wheel:
            z.writestr("medscale-9.9.dist-info/METADATA", wheel)
    with tarfile.open(folder / "medscale-0.3.0.tar.gz", "w:gz") as z:
        info = tarfile.TarInfo("medscale-0.3.0/PKG-INFO")
        if symlink_sdist:
            info.type = tarfile.SYMTYPE
            info.linkname = "../../other"
            z.addfile(info)
        else:
            info.size = len(sdist)
            z.addfile(info, io.BytesIO(sdist))
    return folder


def test_base_only_realistic_pair_is_eligible_but_not_authorized(
    checker: Any, tmp_path: Path
) -> None:
    result = checker.inspect(make_dist(tmp_path / "candidate"))
    assert result["status"] == "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
    assert result["versions"] == {"wheel": "0.3.0", "sdist": "0.3.0"}
    assert result["publication_authorized"] is False
    assert result["independent_security_review_complete"] is False


@pytest.mark.parametrize(
    ("wheel", "sdist", "match"),
    [
        (metadata(extra="rq1-runtime-feasibility"), metadata(), "wheel: optional extras"),
        (metadata(), metadata(extra="training-hf-sft"), "sdist: optional extras"),
        (metadata(dependency="pillow==12.3.0"), metadata(), "wheel: runtime dependencies"),
        (metadata(), metadata(dependency="accelerate==1.14.0"), "sdist: runtime dependencies"),
        (metadata(dynamic="Provides-Extra"), metadata(), "dynamic dependency"),
        (metadata(), metadata(dynamic="Requires-Dist"), "dynamic dependency"),
        (metadata(version="0.3.0"), metadata(version="0.4.0"), "versions disagree"),
        (metadata(name="other-project"), metadata(), "unexpected distribution"),
        (metadata(duplicate_name=True), metadata(), "ambiguous Name"),
    ],
)
def test_unqualified_metadata_blocked(
    checker: Any,
    tmp_path: Path,
    wheel: bytes,
    sdist: bytes,
    match: str,
) -> None:
    result = checker.inspect(make_dist(tmp_path / "candidate", wheel=wheel, sdist=sdist))
    assert result["status"] == "BLOCKED"
    assert any(match in str(issue) for issue in result["issues"])
    assert result["publication_authorized"] is False


@pytest.mark.parametrize(
    ("duplicate_wheel", "symlink_sdist", "match"),
    [
        (True, False, "exactly one METADATA"),
        (False, True, "exactly one regular PKG-INFO"),
    ],
)
def test_malicious_archive_metadata_blocked(
    checker: Any,
    tmp_path: Path,
    duplicate_wheel: bool,
    symlink_sdist: bool,
    match: str,
) -> None:
    result = checker.inspect(
        make_dist(
            tmp_path / "candidate", duplicate_wheel=duplicate_wheel, symlink_sdist=symlink_sdist
        )
    )
    assert result["status"] == "BLOCKED"
    assert any(match in str(issue) for issue in result["issues"])


def test_missing_archive_fails_closed(checker: Any, tmp_path: Path) -> None:
    result = checker.inspect(tmp_path)
    assert result["status"] == "BLOCKED"
    assert len(result["issues"]) == 2


def test_malformed_duplicate_wheel_metadata_blocked(checker: Any, tmp_path: Path) -> None:
    result = checker.inspect(
        make_dist(tmp_path / "candidate", wheel=b"Metadata-Version: 2.3\nName: medscale\n")
    )
    assert result["status"] == "BLOCKED"
    assert any("ambiguous Version" in str(x) for x in result["issues"])


@pytest.mark.parametrize("safe", [True, False])
def test_cli_actual_exit_and_no_release_side_effects(
    tmp_path: Path,
    safe: bool,
) -> None:
    folder = make_dist(
        tmp_path / "candidate",
        wheel=metadata() if safe else metadata(extra="rq1-runtime-feasibility"),
    )
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--dist", str(folder)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == (0 if safe else 2)
    receipt = json.loads(completed.stdout)
    assert receipt["publication_authorized"] is False
    assert receipt["independent_security_review_complete"] is False


def test_gate_wired_before_both_publishers() -> None:
    source = (SCRIPT.parents[1] / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert source.count("python scripts/check_base_core_publication_scope.py --dist dist") == 1
    assert source.index("Block release when optional") < source.index("name: Create Release")
    github_job = source.split("  github-release:", 1)[1].split("  testpypi-publish:", 1)[0]
    pypi_job = source.split("  testpypi-publish:", 1)[1].split("  pr-artifact-build:", 1)[0]
    assert "actions/checkout@" in github_job
    assert "persist-credentials: false" in github_job
    assert "needs: github-release" in pypi_job
    assert "Block TestPyPI" not in pypi_job
    assert "actions/checkout@" not in pypi_job
    assert "permissions:\n      id-token: write" in pypi_job
    assert "contents: write" not in pypi_job


def test_no_independent_approval_or_publisher_code_in_gate() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "github.event_name" not in source
    assert "gh release create" not in source
    assert "twine upload" not in source
