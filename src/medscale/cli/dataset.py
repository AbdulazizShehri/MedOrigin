"""Dataset CLI: `medscale dataset {init|validate|manifest|freeze}`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import medscale._layout as _layout
from medscale.__about__ import __version__ as _software_version
from medscale.cli import _common
from medscale.dataset.manifest import (
    compute_dataset_checksums,
    compute_dataset_fingerprint,
    compute_dataset_manifest,
    write_checksums,
    write_manifest,
)
from medscale.dataset.validate import validate_dataset

_DEFAULT_ROOT: Path = _layout.DEFAULT_ROOT.parent / "datasets"


def _load_records(records_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with records_path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{records_path} line {line_number} is not valid JSON: {exc}"
                ) from exc
    return records


def _build_license_summary(records: list[dict[str, Any]]) -> list[dict[str, object]]:
    counts: dict[str | None, int] = {}
    for record in records:
        spdx = record.get("license_spdx")
        counts[spdx] = counts.get(spdx, 0) + 1
    return [{"spdx": key, "count": value} for key, value in sorted(counts.items())]


def _preview_manifest(dataset_dir: Path) -> dict[str, object]:
    dataset_id = dataset_dir.name
    records_path = _layout.corpus_path(dataset_dir.parent).resolve()
    records = _load_records(records_path)
    manifest = compute_dataset_manifest(
        dataset_id=dataset_id,
        version="1.0",
        created_at="2026-07-13T00:00:00+00:00",
        git_sha="abc123",
        records=records,
        license_summary=_build_license_summary(records),
        software_version=_software_version,
    )
    return manifest.to_dict()


def _write_manifests(dataset_dir: Path) -> Path:
    dataset_id = dataset_dir.name
    records_path = _layout.corpus_path(dataset_dir.parent).resolve()
    records = _load_records(records_path)
    manifest = compute_dataset_manifest(
        dataset_id=dataset_id,
        version="1.0",
        created_at="2026-07-13T00:00:00+00:00",
        git_sha="abc123",
        records=records,
        license_summary=_build_license_summary(records),
        software_version=_software_version,
    )
    write_manifest(manifest, dataset_dir / "manifest.json")
    return dataset_dir / "manifest.json"


def _frozen_receipt_guard(dataset_dir: Path) -> int | None:
    """Refuse overwriting frozen dataset evidence via *any* CLI writer.

    This must apply equally to init --write, manifest --write and freeze:
    the old freeze-only guard left an alternate path to erase manifest bytes.
    Preserve historical v0.2.0 evidence even if its checksum is invalid.
    """
    checksum_dir = dataset_dir / "checksums"
    if checksum_dir.exists() and any(checksum_dir.glob("*.sha256")):
        return _common.fail(
            f"refusing to overwrite existing dataset checksums: {checksum_dir}",
            hint="preserve frozen evidence; create a new dataset identity for migration",
        )
    manifest_path = dataset_dir / "manifest.json"
    if manifest_path.exists():
        try:
            existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return _common.fail(
                f"refusing to overwrite unreadable existing manifest: {manifest_path}",
                hint="preserve existing evidence; use a fresh dataset identity",
            )
        if not isinstance(existing_manifest, dict) or existing_manifest.get(
            "dataset_fingerprint"
        ) not in (None, ""):
            return _common.fail(
                f"refusing to overwrite a frozen dataset manifest: {manifest_path}",
                hint="preserve existing evidence; use a fresh dataset identity",
            )
    return None


def _freeze_command(dataset_dir: Path, created_at: str) -> int:
    dataset_dir = dataset_dir.resolve()
    if not dataset_dir.exists():
        return _common.fail(f"dataset directory not found: {dataset_dir}")
    guard = _frozen_receipt_guard(dataset_dir)
    if guard is not None:
        return guard

    records_path = _layout.corpus_path(dataset_dir.parent).resolve()
    records = _load_records(records_path)
    dataset_id = dataset_dir.name
    manifest = compute_dataset_manifest(
        dataset_id=dataset_id,
        version="1.0",
        created_at=created_at,
        git_sha="abc123",
        records=records,
        license_summary=_build_license_summary(records),
        software_version=_software_version,
    )
    dataset_dir_resolved = dataset_dir.resolve()
    # Order matters: the fingerprint is computed over the base manifest (it
    # cannot include itself), the final manifest is written, and only THEN are
    # checksums taken — checksums must hash the exact bytes that ship.
    # Computing checksums before the fingerprint rewrite left
    # checksums/manifest.json.sha256 stale, so freeze invalidated itself.
    write_manifest(manifest, dataset_dir / "manifest.json")
    fingerprint = compute_dataset_fingerprint(dataset_dir_resolved)
    payload = manifest.to_dict()
    payload["dataset_fingerprint"] = fingerprint
    dataset_dir.joinpath("manifest.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    write_checksums(compute_dataset_checksums(dataset_dir), dataset_dir / "checksums")
    report = validate_dataset(dataset_dir_resolved)
    print(report.to_summary())
    return 0 if report.passed else 1


def _init_command(dataset_id: str, root: Path, write: bool) -> int:
    dataset_dir = root / dataset_id
    if dataset_dir.exists() and not write:
        return _common.fail(f"{dataset_dir} already exists; use --write to mutate explicitly")
    if write and dataset_dir.exists():
        guard = _frozen_receipt_guard(dataset_dir.resolve())
        if guard is not None:
            return guard
    if write:
        dataset_dir.mkdir(parents=True, exist_ok=True)
        (dataset_dir / "schema.json").write_text("{}", encoding="utf-8", newline="\n")
        (dataset_dir / "splits").mkdir(exist_ok=True)
        (dataset_dir / "metadata").mkdir(exist_ok=True)
        (dataset_dir / "checksums").mkdir(exist_ok=True)
        print(f"initialized dataset at {dataset_dir}")
        return 0
    print(f"would initialize dataset at {dataset_dir}")
    return 0


def _validate_command(dataset_dir: Path) -> int:
    if not dataset_dir.exists():
        return _common.fail(f"dataset directory not found: {dataset_dir}")
    report = validate_dataset(dataset_dir)
    print(report.to_summary())
    return 0 if report.passed else 1


def _manifest_command(dataset_dir: Path, write: bool) -> int:
    if not dataset_dir.exists():
        return _common.fail(f"dataset directory not found: {dataset_dir}")
    if write:
        guard = _frozen_receipt_guard(dataset_dir.resolve())
        if guard is not None:
            return guard
    preview = _preview_manifest(dataset_dir)
    if write:
        path = _write_manifests(dataset_dir)
        print(f"wrote manifest: {path}")
    else:
        print(json.dumps(preview, indent=2, sort_keys=True))
        print("\nPreview only. Re-run with --write to persist.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="medscale dataset",
        description="Dataset operations: init, preview, validation, freeze.",
    )
    parser.add_argument("command", choices=["init", "manifest", "validate", "freeze"])
    parser.add_argument("dataset_id", nargs="?", default=None)
    parser.add_argument("path", nargs="?", default=None)
    parser.add_argument(
        "--root",
        type=Path,
        default=_DEFAULT_ROOT,
        help="dataset root (default: data/datasets)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="persist mutations instead of previewing",
    )
    parser.add_argument(
        "--created-at",
        default=None,
        help="explicit UTC ISO-8601 timestamp for freeze/manifest",
    )
    args = parser.parse_args(argv)

    if args.command == "init":
        guard = _common.require_root(args.root)
        if guard is not None:
            return guard
        if args.dataset_id is None:
            return _common.fail(
                "dataset_id required",
                hint="use `medscale dataset init <dataset_id>`",
            )
        return _init_command(args.dataset_id, args.root, args.write)

    dataset_dir = Path(args.path) if args.path is not None else args.root / (args.dataset_id or "")

    if args.command == "manifest":
        guard = _common.require_root(args.root)
        if guard is not None:
            return guard
        return _manifest_command(dataset_dir, args.write)

    if args.command == "validate":
        return _validate_command(dataset_dir)

    created_at = args.created_at or "2026-07-13T00:00:00+00:00"
    return _freeze_command(dataset_dir, created_at)


if __name__ == "__main__":
    raise SystemExit(main())
