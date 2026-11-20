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


def _has_expected_validation_diagnostic(
    result: object, *, passed: bool, markers: tuple[str, ...]
) -> bool:
    """An expected exit code alone is not evidence of the expected reason."""
    if not isinstance(result, dict):
        return False
    stdout, stderr = result.get("stdout"), result.get("stderr")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        return False
    if "Traceback" in stdout or "Traceback" in stderr:
        return False
    state = "Passed: True" if passed else "Passed: False"
    return (
        "Dataset: synthetic-public-fixture" in stdout
        and state in stdout
        and all(marker in stdout for marker in markers)
    )


def evaluate_replay(report: dict[str, Any]) -> list[str]:
    """Fail closed if the pinned synthetic historical-compatibility matrix drifts.

    A passing result means only that the known INCOMPATIBILITY and safeguards
    were reproduced. It never establishes cross-version compatibility.
    """
    issues: list[str] = []
    if report.get("baseline") != HISTORICAL:
        issues.append("historical source commit differs from pinned v0.2.0")
    candidate = report.get("candidate")
    if (
        not isinstance(candidate, str)
        or len(candidate) != 40
        or any(char not in "0123456789abcdef" for char in candidate)
        or candidate == HISTORICAL
    ):
        issues.append("candidate source commit is not a distinct canonical SHA")
    if report.get("synthetic_only") is not True:
        issues.append("audit evidence must use synthetic datasets only")
    if report.get("publication_authorized") is not False:
        issues.append("audit evidence cannot authorize publication")
    cases = report.get("cases")
    if not isinstance(cases, dict) or set(cases) != {"v0.2.0", "candidate"}:
        issues.append("historical and candidate result cases missing")
        return issues
    expected = {
        "v0.2.0": {"freeze": 1, "v0.2.0": 1, "candidate": 1, "checksum": False},
        "candidate": {"freeze": 0, "v0.2.0": 1, "candidate": 0, "checksum": True},
    }
    for name, contract in expected.items():
        entry = cases[name]
        if not isinstance(entry, dict):
            issues.append(f"{name}: invalid result type")
            continue
        if entry.get("manifest_exit") != 0:
            issues.append(f"{name}: initial manifest creation did not succeed")
        freeze = entry.get("freeze")
        if not isinstance(freeze, dict) or freeze.get("exit") != contract["freeze"]:
            issues.append(f"{name}: freeze exit differs from audited baseline")
        freeze_reasons = (
            ("license.json: missing artifact for checksum", "manifest.json: sha256 mismatch")
            if name == "v0.2.0"
            else ()
        )
        if not _has_expected_validation_diagnostic(
            freeze, passed=name == "candidate", markers=freeze_reasons
        ):
            issues.append(f"{name}: freeze diagnostic differs from audited baseline")
        validations = entry.get("validations")
        for validator in ("v0.2.0", "candidate"):
            observed = validations.get(validator) if isinstance(validations, dict) else None
            if not isinstance(observed, dict) or observed.get("exit") != contract[validator]:
                issues.append(f"{name}: {validator} validator differs from audited baseline")
            required_reasons = (
                ("license.json: missing artifact for checksum",) if validator == "v0.2.0" else ()
            ) + (("manifest.json: sha256 mismatch",) if name == "v0.2.0" else ())
            if not _has_expected_validation_diagnostic(
                observed,
                passed=name == "candidate" and validator == "candidate",
                markers=required_reasons,
            ):
                issues.append(
                    f"{name}: {validator} validator diagnostic differs from audited baseline"
                )
        if entry.get("manifest_checksum_matches") is not contract["checksum"]:
            issues.append(f"{name}: manifest checksum relation changed")
        digests = (entry.get("manifest_sha256"), entry.get("recorded_manifest_sha256"))
        if not all(
            isinstance(value, str)
            and len(value) == 64
            and all(char in "0123456789abcdef" for char in value)
            for value in digests
        ):
            issues.append(f"{name}: missing or invalid manifest checksums")
        elif (digests[0] == digests[1]) is not contract["checksum"]:
            issues.append(f"{name}: recorded checksum contradicts computed relation")
        # The recorded checksum relation alone is not evidence of file bytes:
        # a matching forged pair can preserve the expected TRUE/FALSE result.
        # Tie both declared hashes to the snapshots taken from real files.
        snapshot = entry.get("artifact_hashes_by_relative_path")
        if not isinstance(snapshot, dict):
            issues.append(f"{name}: missing artifact snapshot")
        else:
            if snapshot.get("manifest.json") != entry.get("manifest_sha256"):
                issues.append(f"{name}: manifest hash differs from artifact snapshot")
            recorded = entry.get("recorded_manifest_sha256")
            possible_checksum_files = (
                {
                    hashlib.sha256((recorded + newline).encode("ascii")).hexdigest()
                    for newline in ("\n", "\r\n")
                }
                if isinstance(recorded, str) and recorded.isascii()
                else set()
            )
            if snapshot.get("checksums/manifest.json.sha256") not in possible_checksum_files:
                issues.append(f"{name}: checksum file differs from artifact snapshot")
        guards = entry.get("writer_guards")
        if not isinstance(guards, dict) or set(guards) != {
            "freeze",
            "manifest-write",
            "init-write",
        }:
            issues.append(f"{name}: immutable-writer coverage incomplete")
        else:
            for operation, result in guards.items():
                if (
                    not isinstance(result, dict)
                    or result.get("exit") != 2
                    or result.get("all_artifact_bytes_preserved") is not True
                ):
                    issues.append(f"{name}: {operation} did not refuse without mutation")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="medorigin-history-replay-") as directory:
        report = inspect(args.repo.resolve(), Path(directory))
    issues = evaluate_replay(report)
    report["status"] = "KNOWN_INCOMPATIBILITY_REPRODUCED_ONLY" if not issues else "BLOCKED"
    report["issues"] = issues
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
    if issues:
        print("audit baseline drift: " + "; ".join(issues), file=sys.stderr)
    return 2 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
