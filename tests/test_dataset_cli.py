"""Dataset CLI coverage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from medscale.cli.dataset import main


def test_dataset_init_preview_does_not_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data" / "datasets"
    root.mkdir(parents=True)
    target = root / "medscale-dataset-v1"
    assert main(["init", "medscale-dataset-v1", "--root", str(root)]) == 0
    assert not target.exists(), "init without --write must not create a dataset directory"


def test_dataset_init_writes_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data" / "datasets"
    root.mkdir(parents=True)
    target = root / "medscale-dataset-v1"
    assert main(["init", "medscale-dataset-v1", "--root", str(root), "--write"]) == 0
    assert target.exists()
    assert (target / "schema.json").exists()
    assert (target / "splits").exists()


def test_dataset_manifest_exits_nonzero_for_missing_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data" / "datasets"
    root.mkdir(parents=True)
    assert main(["manifest", "missing", "--root", str(root)]) == 2


def test_dataset_validate_exits_nonzero_for_invalid_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_dir = tmp_path / "medscale-dataset-v1"
    dataset_dir.mkdir(parents=True)
    (dataset_dir / "manifest.json").write_text("{}", encoding="utf-8")
    exit_code = main(["validate", str(dataset_dir)])
    assert exit_code in {1, 2}


def test_dataset_validate_exits_zero_for_valid_dataset(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "medscale-dataset-v1"
    dataset_dir.mkdir(parents=True)
    (dataset_dir / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_id": "medscale-dataset-v1",
                "created_at": "2026-07-13T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    (dataset_dir / "schema.json").write_text("{}", encoding="utf-8")
    (dataset_dir / "splits").mkdir()
    for name in ["train", "validation", "test"]:
        (dataset_dir / "splits" / f"{name}.json").write_text("[]", encoding="utf-8")
    metadata = dataset_dir / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "license.json").write_text(
        json.dumps(
            {
                "spdx_id": "MIT",
                "source_scope": ["synthetic"],
                "redistribution_allowed": True,
                "attribution_required": False,
                "commercial_allowed": True,
            }
        ),
        encoding="utf-8",
    )
    checksums = dataset_dir / "checksums"
    checksums.mkdir()
    for path in [
        dataset_dir / "manifest.json",
        dataset_dir / "schema.json",
        dataset_dir / "splits" / "train.json",
        dataset_dir / "splits" / "validation.json",
        dataset_dir / "splits" / "test.json",
    ]:
        checksums.joinpath(path.name + ".sha256").write_text(
            hashlib.sha256(path.read_bytes()).hexdigest() + "\n", encoding="utf-8"
        )
    assert main(["validate", str(dataset_dir)]) == 0


def test_dataset_freeze_produces_self_consistent_checksums(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression (audit F-6): freeze used to checksum the manifest BEFORE
    rewriting it with the fingerprint, so checksums/manifest.json.sha256 never
    matched the shipped manifest and freeze failed its own validation."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "data" / "datasets"
    dataset_dir = root / "medscale-dataset-v1"
    corpus = root / "corpus" / "records.jsonl"
    corpus.parent.mkdir(parents=True)
    corpus.write_text(
        json.dumps({"record_id": "r-1", "license_spdx": "MIT"}) + "\n", encoding="utf-8"
    )
    dataset_dir.mkdir(parents=True)
    (dataset_dir / "schema.json").write_text("{}", encoding="utf-8")
    splits = dataset_dir / "splits"
    splits.mkdir()
    for name in ("train", "validation", "test"):
        (splits / f"{name}.json").write_text("[]", encoding="utf-8")
    metadata = dataset_dir / "metadata"
    metadata.mkdir()
    (metadata / "license.json").write_text(
        json.dumps(
            {
                "spdx_id": "MIT",
                "source_scope": ["synthetic"],
                "redistribution_allowed": True,
                "attribution_required": False,
                "commercial_allowed": True,
            }
        ),
        encoding="utf-8",
    )

    # An unsigned manifest --write draft remains eligible for its first
    # freeze; the safeguard only protects immutable receipts.
    assert main(["manifest", "medscale-dataset-v1", "--root", str(root), "--write"]) == 0
    assert (
        json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))[
            "dataset_fingerprint"
        ]
        == ""
    )

    exit_code = main(
        [
            "freeze",
            "medscale-dataset-v1",
            "--root",
            str(root),
            "--created-at",
            "2026-07-13T00:00:00+00:00",
        ]
    )

    manifest_bytes = (dataset_dir / "manifest.json").read_bytes()
    recorded = (
        (dataset_dir / "checksums" / "manifest.json.sha256").read_text(encoding="utf-8").strip()
    )
    assert recorded == hashlib.sha256(manifest_bytes).hexdigest(), (
        "checksums must hash the exact manifest bytes that ship"
    )
    assert json.loads(manifest_bytes)["dataset_fingerprint"]
    assert b"\r" not in manifest_bytes
    assert exit_code == 0

    # Once checksum receipts exist, refreezing must not rewrite a historical
    # or current artifact, even when the original receipt is now invalid.
    original_checksum = (dataset_dir / "checksums" / "manifest.json.sha256").read_bytes()
    original_manifest = manifest_bytes
    freeze_args = [
        "freeze",
        "medscale-dataset-v1",
        "--root",
        str(root),
        "--created-at",
        "2026-07-13T00:00:00+00:00",
    ]
    assert main(freeze_args) == 2
    assert (dataset_dir / "manifest.json").read_bytes() == original_manifest
    assert (dataset_dir / "checksums" / "manifest.json.sha256").read_bytes() == original_checksum

    # A corrupt historical receipt is not eligible for in-place "repair."
    bad_checksum = b"0" * 64 + b"\n"
    (dataset_dir / "checksums" / "manifest.json.sha256").write_bytes(bad_checksum)
    assert main(freeze_args) == 2
    assert (dataset_dir / "manifest.json").read_bytes() == original_manifest
    assert (dataset_dir / "checksums" / "manifest.json.sha256").read_bytes() == bad_checksum


def test_dataset_freeze_refuses_existing_protected_manifest_without_checksums(
    tmp_path: Path,
) -> None:
    """Damaged or fingerprinted manifests must never be silently repaired."""
    for name, raw in (
        ("malformed", b"{truncated historical bytes"),
        ("fingerprinted", b'{"dataset_fingerprint": "historical-immutable"}'),
    ):
        dataset_dir = tmp_path / name
        dataset_dir.mkdir()
        path = dataset_dir / "manifest.json"
        path.write_bytes(raw)
        assert main(["freeze", name, "--root", str(tmp_path)]) == 2
        assert path.read_bytes() == raw
        assert not (dataset_dir / "checksums").exists()
