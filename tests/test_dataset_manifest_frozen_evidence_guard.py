"""Guard frozen dataset evidence against all dataset CLI writers.

All payloads are synthetic. No historical research records are touched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from medscale.cli.dataset import main


def _dataset(tmp_path: Path, evidence: str) -> tuple[Path, Path, Path, bytes, bytes]:
    root = tmp_path / "synthetic-datasets"
    root.mkdir()
    dataset = root / "synthetic-only"
    dataset.mkdir()
    corpus = root / "corpus" / "records.jsonl"
    corpus.parent.mkdir()
    corpus.write_text(
        json.dumps({"record_id": "synthetic-1", "license_spdx": "MIT"}) + "\n",
        encoding="utf-8",
    )
    schema = dataset / "schema.json"
    schema.write_bytes(b'{"historic_schema": 1}\n')
    manifest = dataset / "manifest.json"
    if evidence == "fingerprinted":
        manifest.write_bytes(b'{"dataset_fingerprint": "immutable-old-identity"}\n')
    elif evidence == "unreadable":
        manifest.write_bytes(b"{ historic-invalid-byte-evidence")
    else:
        manifest.write_bytes(b'{"dataset_fingerprint": ""}\n')

    if evidence == "checksummed":
        checksum = dataset / "checksums" / "manifest.json.sha256"
        checksum.parent.mkdir()
        checksum.write_text(
            hashlib.sha256(manifest.read_bytes()).hexdigest() + "\n", encoding="utf-8"
        )
    return root, dataset, manifest, manifest.read_bytes(), schema.read_bytes()


@pytest.mark.parametrize("evidence", ["checksummed", "fingerprinted", "unreadable"])
@pytest.mark.parametrize("action", ["init", "manifest", "freeze"])
def test_all_dataset_writers_refuse_existing_evidence(
    tmp_path: Path, evidence: str, action: str
) -> None:
    root, dataset, manifest, manifest_bytes, schema_bytes = _dataset(tmp_path, evidence)
    checksum_dir = dataset / "checksums"
    original_receipts = (
        {path.name: path.read_bytes() for path in checksum_dir.glob("*.sha256")}
        if checksum_dir.exists()
        else {}
    )

    options = [action, "synthetic-only", "--root", str(root)]
    if action != "freeze":
        options.append("--write")
    assert main(options) == 2
    assert manifest.read_bytes() == manifest_bytes
    assert (dataset / "schema.json").read_bytes() == schema_bytes
    assert (
        {path.name: path.read_bytes() for path in checksum_dir.glob("*.sha256")}
        == original_receipts
        if checksum_dir.exists()
        else not original_receipts
    )


def test_unsigned_draft_manifest_remains_writable(tmp_path: Path) -> None:
    root, dataset, manifest, original, _ = _dataset(tmp_path, "draft")
    assert main(["manifest", "synthetic-only", "--root", str(root), "--write"]) == 0
    assert manifest.read_bytes() != original
    assert json.loads(manifest.read_bytes())["dataset_fingerprint"] == ""
    assert not (dataset / "checksums" / "manifest.json.sha256").exists()


def test_init_new_dataset_still_works(tmp_path: Path) -> None:
    root = tmp_path / "synthetic-new"
    root.mkdir()
    assert main(["init", "new", "--root", str(root), "--write"]) == 0
    assert (root / "new" / "schema.json").read_bytes() == b"{}"
