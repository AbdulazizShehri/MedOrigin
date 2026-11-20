"""Deterministic, nonpublishing MedOrigin QA assembly contract."""

from __future__ import annotations

import hashlib
import importlib
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def builder(monkeypatch: pytest.MonkeyPatch) -> Any:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    return importlib.import_module("assemble_medorigin_unpublished_qa")


@pytest.fixture
def synthetic_inputs(
    builder: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, Path, Path, Path]:
    """Use synthetic bytes only; no real qualified Wheel changes."""
    qa = builder.qa
    wheel = tmp_path / "fake-core.whl"
    sdist = tmp_path / "fake-core.tar.gz"
    provenance = tmp_path / "provenance.json"
    wheel.write_bytes(b"fake-wheel-no-patient-data")
    sdist.write_bytes(b"fake-sdist-no-patient-data")
    manifest = {
        "source_git_commit": qa.CORE_SHA,
        "publication_authorized": False,
        "frozen_pyproject_sha256": (
            "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
        ),
        "frozen_lock_sha256": "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4",
    }
    provenance.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(
        qa,
        "TRUSTED_ARTIFACTS",
        {
            qa.WHEEL: hashlib.sha256(wheel.read_bytes()).hexdigest(),
            qa.SDIST: hashlib.sha256(sdist.read_bytes()).hexdigest(),
        },
    )

    def fixture_git(repo: Path, *args: str) -> bytes:
        assert repo == tmp_path
        if args == ("status", "--porcelain"):
            return b""
        assert len(args) == 2 and args[0] == "show"
        assert args[1].startswith(qa.DEMO_SHA + ":")
        return ("synthetic tracked fixture: " + args[1]).encode()

    monkeypatch.setattr(builder, "git", fixture_git)
    return tmp_path, wheel, sdist, provenance


def test_nonpublishing_assembler_is_deterministic_and_verifiable(
    builder: Any, synthetic_inputs: tuple[Path, Path, Path, Path], tmp_path: Path
) -> None:
    repo, wheel, sdist, provenance = synthetic_inputs
    left = builder.build_members(repo, wheel, sdist, provenance)
    right = builder.build_members(repo, wheel, sdist, provenance)
    assert left == right
    assert left["BUNDLE_MANIFEST.json"] == right["BUNDLE_MANIFEST.json"]
    assert set(left) == builder.qa.EXPECTED_PATHS
    first = builder.deterministic_zip(left)
    second = builder.deterministic_zip(right)
    assert first == second
    zip_file = tmp_path / "reproducible.zip"
    zip_file.write_bytes(first)
    checked = builder.qa.inspect(zip_file, expected_zip_sha256=hashlib.sha256(first).hexdigest())
    assert checked["status"] == "MEDORIGIN_UNPUBLISHED_QA_INTEGRITY_PASS"
    assert checked["publication_authorized"] is False
    with zipfile.ZipFile(zip_file) as z:
        assert all(item.date_time[:3] == (2020, 1, 1) for item in z.infolist())


def test_assembly_creates_new_zip_but_never_overwrites(
    builder: Any, synthetic_inputs: tuple[Path, Path, Path, Path], tmp_path: Path
) -> None:
    repo, wheel, sdist, provenance = synthetic_inputs
    output = tmp_path / builder.ARCHIVE_NAME
    receipt = builder.assemble(repo, wheel, sdist, provenance, output)
    assert receipt["status"] == "MEDORIGIN_UNPUBLISHED_QA_REPRODUCED"
    assert receipt["publication_authorized"] is False
    before = output.read_bytes()
    with pytest.raises(builder.AssemblyError, match="already exists"):
        builder.assemble(repo, wheel, sdist, provenance, output)
    assert output.read_bytes() == before


@pytest.mark.parametrize("which", ["wheel", "sdist"])
def test_assembly_refuses_changed_core_with_no_output(
    builder: Any,
    synthetic_inputs: tuple[Path, Path, Path, Path],
    tmp_path: Path,
    which: str,
) -> None:
    repo, wheel, sdist, provenance = synthetic_inputs
    (wheel if which == "wheel" else sdist).write_bytes(b"altered")
    output = tmp_path / builder.ARCHIVE_NAME
    with pytest.raises(builder.AssemblyError, match="qualified SHA-256"):
        builder.assemble(repo, wheel, sdist, provenance, output)
    assert not output.exists()


def test_assembly_refuses_source_worktree_changes(
    builder: Any,
    synthetic_inputs: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, wheel, sdist, provenance = synthetic_inputs
    monkeypatch.setattr(builder, "git", lambda *_args: b"?? unsafe-file\n")
    with pytest.raises(builder.AssemblyError, match="clean"):
        builder.build_members(repo, wheel, sdist, provenance)


def test_assembly_refuses_provenance_false_to_int_alias(
    builder: Any, synthetic_inputs: tuple[Path, Path, Path, Path]
) -> None:
    repo, wheel, sdist, provenance = synthetic_inputs
    record = json.loads(provenance.read_text(encoding="utf-8"))
    record["publication_authorized"] = 0
    provenance.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(builder.AssemblyError, match="source receipt"):
        builder.build_members(repo, wheel, sdist, provenance)


def test_assembly_invalid_zip_name_rejected(
    builder: Any, synthetic_inputs: tuple[Path, Path, Path, Path], tmp_path: Path
) -> None:
    repo, wheel, sdist, provenance = synthetic_inputs
    with pytest.raises(builder.AssemblyError, match="explicitly unpublished"):
        builder.assemble(repo, wheel, sdist, provenance, tmp_path / "MedOrigin-RELEASE.zip")


def test_assembler_contains_no_publishing_calls(builder: Any) -> None:
    source = (
        Path(__file__).resolve().parents[1] / "scripts" / "assemble_medorigin_unpublished_qa.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "twine upload",
        "gh release create",
        "git push",
        "git tag",
        "hf upload",
        "pip install",
        "requests.post",
    ):
        assert forbidden not in source
    assert builder.ARCHIVE_NAME.endswith("-UNPUBLISHED.zip")
