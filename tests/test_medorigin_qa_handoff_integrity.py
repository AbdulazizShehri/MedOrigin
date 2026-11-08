"""Adversarial, standard-library-only QA handoff integrity contract tests."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import stat
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "verify_medorigin_qa_handoff.py"


@pytest.fixture
def verifier() -> Any:
    spec = importlib.util.spec_from_file_location("medorigin_qa_handoff_checker", SOURCE)
    assert spec is not None and spec.loader is not None
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


@pytest.fixture
def fake_bundle(verifier: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    files = {name: (f"synthetic test: {name}\n").encode() for name in verifier.EXPECTED_PATHS}
    files[verifier.WHEEL if verifier.WHEEL in files else f"artifacts/{verifier.WHEEL}"] = (
        b"fake-wheel-test"
    )
    files[f"artifacts/{verifier.SDIST}"] = b"fake-sdist-test"
    sha = {
        verifier.WHEEL: hashlib.sha256(files[f"artifacts/{verifier.WHEEL}"]).hexdigest(),
        verifier.SDIST: hashlib.sha256(files[f"artifacts/{verifier.SDIST}"]).hexdigest(),
    }
    monkeypatch.setattr(verifier, "TRUSTED_ARTIFACTS", sha)
    manifest = {
        "schema": "MEDORIGIN_UNPUBLISHED_QA_HANDOFF_V1",
        "project": "MedOrigin",
        "target_version": "0.3.0",
        "python_distribution": "medscale",
        "core_source_git_commit": verifier.CORE_SHA,
        "example_source_git_commit": verifier.DEMO_SHA,
        "publication_authorized": False,
        "release_reviewer_approved": False,
        "adr_0044_accepted": False,
        "protected_main_merged": False,
        "developer_examples_in_core_wheel": False,
        "hosted_two_os_rehearsal_run": 40119019407,
        "artifacts_sha256": sha,
    }
    files[verifier.MANIFEST] = json.dumps(manifest).encode()
    files[verifier.PROVENANCE] = json.dumps(
        {
            "source_git_commit": verifier.CORE_SHA,
            "publication_authorized": False,
            "frozen_pyproject_sha256": (
                "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
            ),
            "frozen_lock_sha256": (
                "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"
            ),
        }
    ).encode()
    refresh_sums(verifier, files)
    return files


def refresh_sums(verifier: Any, files: dict[str, bytes]) -> None:
    files[verifier.SUMS] = (
        "\n".join(
            f"{hashlib.sha256(files[name]).hexdigest()}  {name}"
            for name in sorted(files)
            if name != verifier.SUMS
        )
        + "\n"
    ).encode()


def check(verifier: Any, fake_bundle: dict[str, bytes], tmp_path: Path) -> dict[str, object]:
    return cast(dict[str, object], verifier.inspect(tmp_path, collector=lambda _path: fake_bundle))


def test_complete_synthetic_inventory_passes(
    verifier: Any, fake_bundle: dict[str, bytes], tmp_path: Path
) -> None:
    receipt = check(verifier, fake_bundle, tmp_path)
    assert receipt["status"] == "MEDORIGIN_UNPUBLISHED_QA_INTEGRITY_PASS"
    assert receipt["checked_files"] == 16
    assert receipt["publication_authorized"] is False
    assert receipt["cryptographically_signed"] is False


@pytest.mark.parametrize("problem", ["missing", "extra", "tampered"])
def test_incomplete_or_mutated_content_rejected(
    verifier: Any, fake_bundle: dict[str, bytes], tmp_path: Path, problem: str
) -> None:
    changed = copy.copy(fake_bundle)
    name = f"artifacts/{verifier.WHEEL}"
    if problem == "missing":
        del changed[name]
    elif problem == "extra":
        changed["secret.env"] = b"unexpected"
    else:
        changed[name] += b"poison"
    with pytest.raises(verifier.HandoffIntegrityError):
        check(verifier, changed, tmp_path)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("publication_authorized", 0),
        ("release_reviewer_approved", 0),
        ("adr_0044_accepted", True),
        ("developer_examples_in_core_wheel", "false"),
        ("hosted_two_os_rehearsal_run", 40119019408),
        ("core_source_git_commit", "f" * 40),
    ],
)
def test_manifest_fails_closed_even_with_rehashed_checksums(
    verifier: Any,
    fake_bundle: dict[str, bytes],
    tmp_path: Path,
    field: str,
    bad: object,
) -> None:
    altered = copy.copy(fake_bundle)
    manifest = json.loads(altered[verifier.MANIFEST])
    manifest[field] = bad
    altered[verifier.MANIFEST] = json.dumps(manifest).encode()
    refresh_sums(verifier, altered)
    with pytest.raises(verifier.HandoffIntegrityError):
        check(verifier, altered, tmp_path)


def test_duplicate_json_fields_rejected(
    verifier: Any, fake_bundle: dict[str, bytes], tmp_path: Path
) -> None:
    altered = copy.copy(fake_bundle)
    altered[verifier.PROVENANCE] = (
        b'{"source_git_commit":"fake","source_git_commit":"fake","publication_authorized":false}'
    )
    refresh_sums(verifier, altered)
    with pytest.raises(verifier.HandoffIntegrityError):
        check(verifier, altered, tmp_path)


def test_rehashed_fake_artifact_still_refused(
    verifier: Any, fake_bundle: dict[str, bytes], tmp_path: Path
) -> None:
    altered = copy.copy(fake_bundle)
    altered[f"artifacts/{verifier.WHEEL}"] = b"substituted wheel"
    refresh_sums(verifier, altered)
    with pytest.raises(verifier.HandoffIntegrityError, match="Core artifact digest"):
        check(verifier, altered, tmp_path)


def test_checksum_duplicate_rows_rejected(
    verifier: Any, fake_bundle: dict[str, bytes], tmp_path: Path
) -> None:
    altered = copy.copy(fake_bundle)
    rows = altered[verifier.SUMS].splitlines()
    altered[verifier.SUMS] = b"\n".join([*rows[:-1], rows[0]]) + b"\n"
    with pytest.raises(verifier.HandoffIntegrityError):
        check(verifier, altered, tmp_path)


@pytest.mark.parametrize(
    "bad", ["../patient.txt", "/absolute.json", "c:/something", "a\\b", "a//b"]
)
def test_unsafe_zip_paths_rejected(verifier: Any, tmp_path: Path, bad: str) -> None:
    bundle = tmp_path / "bad.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr(bad, "data")
    with pytest.raises(verifier.HandoffIntegrityError):
        verifier._collect_zip(bundle)


def test_duplicate_zip_entry_rejected(verifier: Any, tmp_path: Path) -> None:
    bundle = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr(verifier.MANIFEST, b"a")
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr(verifier.MANIFEST, b"b")
    with pytest.raises(verifier.HandoffIntegrityError):
        verifier._collect_zip(bundle)


def test_zip_symlink_rejected(verifier: Any, tmp_path: Path) -> None:
    bundle = tmp_path / "link.zip"
    info = zipfile.ZipInfo(verifier.MANIFEST)
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr(info, "../../arbitrary")
    with pytest.raises(verifier.HandoffIntegrityError):
        verifier._collect_zip(bundle)


def test_zip_wrong_external_sha_blocked(verifier: Any, tmp_path: Path) -> None:
    path = tmp_path / "archive.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(verifier.MANIFEST, "fake manifest")
    assert verifier.main([str(path), "--expected-zip-sha256", "0" * 64]) == 2


def test_directory_symlink_rejected(verifier: Any, tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("synthetic", encoding="utf-8")
    folder = tmp_path / "bundle"
    folder.mkdir()
    try:
        (folder / "link").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks require elevated privileges on this host")
    with pytest.raises(verifier.HandoffIntegrityError):
        verifier._collect_directory(folder)
