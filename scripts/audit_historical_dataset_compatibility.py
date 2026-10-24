"""Reproduce v0.2.0-vs-current dataset receipts with synthetic inputs only.

Never checks out the historical tag into the working tree, mutates frozen
research files, installs packages, or accesses a publisher. All source code
is exported from pinned Git commit objects, independent of local edits.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

HISTORICAL = "d2e651a55c92f2218aca49acaa5b7bd18a75f096"
DATASET = "synthetic-public-fixture"
DATE = "2026-07-13T00:00:00+00:00"
COMMAND = "from medscale.cli.dataset import main; import sys; sys.exit(main(sys.argv[1:]))"


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    ).stdout


def _export_source(repo: Path, commit: str, destination: Path) -> Path:
    data = _git(repo, "archive", "--format=zip", commit, "--", "src/medscale")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if not names or not all(
            (name == "src/" or name.startswith("src/medscale/"))
            and ".." not in name.split("/")
            and "\\" not in name
            for name in names
        ):
            raise ValueError("invalid Git-archive source path")
        archive.extractall(destination)
    return destination / "src"


def _fixture(base: Path) -> tuple[Path, Path]:
    root = base / "data" / "datasets"
    target = root / DATASET
    target.mkdir(parents=True)
    (target / "schema.json").write_text("{}", encoding="utf-8")
    splits = target / "splits"
    splits.mkdir()
    for name in ("train", "validation", "test"):
        (splits / f"{name}.json").write_text("[]", encoding="utf-8")
    license_dir = target / "metadata"
    license_dir.mkdir()
    (license_dir / "license.json").write_text(
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
    corpus = root / "corpus"
    corpus.mkdir()
    (corpus / "records.jsonl").write_text(
        json.dumps({"record_id": "r-synthetic-1", "license_spdx": "MIT"}) + "\n",
        encoding="utf-8",
    )
    return root, target


def _digest_files(directory: Path) -> dict[str, str]:
    return {
        file.relative_to(directory).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(directory.rglob("*"))
        if file.is_file()
    }


def _run(root: Path, source: Path, tag: str, args: list[str]) -> dict[str, object]:
    environment = {
        **os.environ,
        "PYTHONPATH": str(source),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    process = subprocess.run(
        [sys.executable, "-c", COMMAND, *args],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return {
        "source": tag,
        "argv": ["<synthetic-root>" if item.startswith(str(root)) else item for item in args],
        "exit": process.returncode,
        "stdout": process.stdout[:2000],
        "stderr": process.stderr[:2000],
    }


def inspect(repo: Path, workspace: Path) -> dict[str, Any]:
    current = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    if len(current) != 40 or current == HISTORICAL:
        raise ValueError("unexpected comparison commit")
    sources = {
        "v0.2.0": _export_source(repo, HISTORICAL, workspace / "source_old"),
        "candidate": _export_source(repo, current, workspace / "source_candidate"),
    }
    cases: dict[str, Any] = {}
    for label in ("v0.2.0", "candidate"):
        root, target = _fixture(workspace / label)
        manifest = _run(
            workspace,
            sources[label],
            label,
            ["manifest", DATASET, "--root", str(root), "--write"],
        )
        freeze = _run(
            workspace,
            sources[label],
            label,
            ["freeze", DATASET, "--root", str(root), "--created-at", DATE],
        )
        original = _digest_files(target)
        validations = {
            source_name: _run(workspace, source_path, source_name, ["validate", str(target)])
            for source_name, source_path in sources.items()
        }
        guards: dict[str, Any] = {}
        for operation, args in (
            (
                "freeze",
                ["freeze", DATASET, "--root", str(root), "--created-at", DATE],
            ),
            ("manifest-write", ["manifest", DATASET, "--root", str(root), "--write"]),
            ("init-write", ["init", DATASET, "--root", str(root), "--write"]),
        ):
            outcome = _run(workspace, sources["candidate"], "candidate", args)
            guards[operation] = {
                "exit": outcome["exit"],
                "all_artifact_bytes_preserved": _digest_files(target) == original,
            }
        manifest_file = target / "manifest.json"
        checksum_file = target / "checksums" / "manifest.json.sha256"
        actual = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
        recorded = checksum_file.read_text(encoding="utf-8").strip()
        cases[label] = {
            "manifest_exit": manifest["exit"],
            "freeze": freeze,
            "validations": validations,
            "writer_guards": guards,
            "manifest_sha256": actual,
            "recorded_manifest_sha256": recorded,
            "manifest_checksum_matches": actual == recorded,
            "artifact_hashes_by_relative_path": original,
        }
    return {
        "baseline": HISTORICAL,
        "candidate": current,
        "python_version": sys.version.split()[0],
        "synthetic_only": True,
        "publication_authorized": False,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="medorigin-history-replay-") as directory:
        report = inspect(args.repo.resolve(), Path(directory))
    args.json_out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    cases = report["cases"]
    for name in ("v0.2.0", "candidate"):
        case = cases[name]
        preserved = all(
            value["all_artifact_bytes_preserved"] for value in case["writer_guards"].values()
        )
        print(
            f"{name}: freeze={case['freeze']['exit']} "
            f"checksum_match={case['manifest_checksum_matches']} "
            f"validate_old={case['validations']['v0.2.0']['exit']} "
            f"validate_candidate={case['validations']['candidate']['exit']} "
            f"preserved={preserved}"
        )
    if not all(
        operation["all_artifact_bytes_preserved"] and operation["exit"] != 0
        for case in cases.values()
        for operation in case["writer_guards"].values()
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
