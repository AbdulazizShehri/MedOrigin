"""Deterministic, offline assembly of an UNPUBLISHED MedOrigin Developer Beta QA ZIP.

Never merges, tags, uploads, publishes, builds packages, installs dependencies,
reads patient data, or modifies canonical research evidence. Each Core artifact
must already have its independently known SHA-256. Example source and legal
notices are read from an immutable pinned local Git commit, not the worktree.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import verify_medorigin_qa_handoff as qa

ARCHIVE_NAME = "MedOrigin-v0.3.0-Developer-Beta-UNPUBLISHED.zip"
MAX_INPUT_SIZE = 3_000_000
FIXED_ZIP_DATE = (2020, 1, 1, 0, 0, 0)


class AssemblyError(ValueError):
    """A local file or revision failed the nonpublishing bundle contract."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bounded(path: Path, *, limit: int = MAX_INPUT_SIZE) -> bytes:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
        raise AssemblyError("missing, linked, or oversized local input")
    data = path.read_bytes()
    if len(data) > limit:
        raise AssemblyError("local input exceeded size budget")
    return data


def git(repo: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AssemblyError("local Git source unavailable") from exc
    if completed.returncode != 0 or len(completed.stdout) > MAX_INPUT_SIZE:
        # stdout/stderr could contain private checkout paths; do not echo.
        raise AssemblyError("pinned Git source could not be read")
    return completed.stdout


def build_members(repo: Path, wheel: Path, sdist: Path, provenance: Path) -> dict[str, bytes]:
    """Read only trusted artifacts and explicitly pinned tracked source bytes."""
    if git(repo, "status", "--porcelain").strip():
        raise AssemblyError("repository checkout must be clean")
    actual_wheel = read_bounded(wheel)
    actual_sdist = read_bounded(sdist)
    if digest(actual_wheel) != qa.TRUSTED_ARTIFACTS[qa.WHEEL]:
        raise AssemblyError("candidate wheel differs from qualified SHA-256")
    if digest(actual_sdist) != qa.TRUSTED_ARTIFACTS[qa.SDIST]:
        raise AssemblyError("candidate sdist differs from qualified SHA-256")
    receipt = read_bounded(provenance)
    provenance_info = qa.json_object(receipt)
    if (
        provenance_info.get("source_git_commit") != qa.CORE_SHA
        or provenance_info.get("publication_authorized") is not False
    ):
        raise AssemblyError("Core source receipt does not match immutable candidate")

    files: dict[str, bytes] = {
        f"artifacts/{qa.WHEEL}": actual_wheel,
        f"artifacts/{qa.SDIST}": actual_sdist,
        qa.PROVENANCE: receipt,
    }
    for name in qa.EXAMPLES:
        files[qa.ROOT + name] = git(repo, "show", f"{qa.DEMO_SHA}:{qa.ROOT}{name}")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        files[name] = git(repo, "show", f"{qa.DEMO_SHA}:{name}")
    files["README_UNPUBLISHED_QA.md"] = (
        "# MedOrigin v0.3.0 — UNPUBLISHED local Developer Beta QA handoff\n\n"
        "This is an **unsigned local testing bundle**, NOT a public release.\n"
        "It contains separately sourced, SHA-pinned Core wheel/sdist (Draft #598)\n"
        "and fictional-only developer examples (Draft #617). The Python\n"
        "distribution, import and CLI retain the disclosed `medscale` name.\n"
        "The Tkinter example is a separate source sample, NOT installed by\n"
        "the wheel; it is NOT a signed desktop app or clinician product.\n\n"
        "Check the external SHA-256 of this ZIP and run the read-only\n"
        "`scripts/verify_medorigin_qa_handoff.py` from the source repository\n"
        "before any offline developer test. Python 3.11 or 3.12 and a local\n"
        "Tkinter runtime are needed to explore the fictional desktop example.\n\n"
        "No real patient data, EHR writes, clinical use, automatic migration,\n"
        "release/tag, online publication or protected-main merge is approved.\n"
        "Independent review #603 and software-release decision #574 stay open.\n"
    ).encode()
    manifest: dict[str, object] = {
        "schema": "MEDORIGIN_UNPUBLISHED_QA_HANDOFF_V1",
        "project": "MedOrigin",
        "target_version": "0.3.0",
        "python_distribution": "medscale",
        "core_source_git_commit": qa.CORE_SHA,
        "example_source_git_commit": qa.DEMO_SHA,
        "publication_authorized": False,
        "release_reviewer_approved": False,
        "adr_0044_accepted": False,
        "protected_main_merged": False,
        "developer_examples_in_core_wheel": False,
        "hosted_two_os_rehearsal_run": 40119019407,
        "artifacts_sha256": qa.TRUSTED_ARTIFACTS,
    }
    files[qa.MANIFEST] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    files[qa.SUMS] = (
        "\n".join(f"{digest(files[name])}  {name}" for name in sorted(files)) + "\n"
    ).encode("ascii")

    # Reuse the actual consumer verifier, not an independent weaker check.
    try:
        qa.inspect(repo, collector=lambda _root: files)
    except (qa.HandoffIntegrityError, KeyError, OSError) as exc:
        raise AssemblyError("assembled QA inventory failed integrity admission") from exc
    return files


def deterministic_zip(files: dict[str, bytes]) -> bytes:
    if set(files) != qa.EXPECTED_PATHS:
        raise AssemblyError("unexpected QA archive member inventory")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, FIXED_ZIP_DATE)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_STORED  # same bytes on every OS
            archive.writestr(info, files[name])
    return buffer.getvalue()


def assemble(
    repository: Path,
    wheel: Path,
    sdist: Path,
    provenance: Path,
    output: Path,
) -> dict[str, object]:
    """Write only a new QA ZIP via exclusive creation; no original is changed."""
    if output.name != ARCHIVE_NAME:
        raise AssemblyError("required explicitly unpublished ZIP filename")
    if not output.parent.is_dir() or output.exists():
        raise AssemblyError("output directory missing or QA handoff already exists")
    members = build_members(repository, wheel, sdist, provenance)
    contents = deterministic_zip(members)
    # Guaranteed no-overwrite: the ZIP bytes are complete before write starts.
    with output.open("xb") as handle:
        handle.write(contents)
    try:
        receipt = qa.inspect(output, expected_zip_sha256=digest(contents))
    except (qa.HandoffIntegrityError, OSError) as exc:
        # Refuse a bogus status. Retain bytes for forensic examination.
        raise AssemblyError("new output failed post-write verification") from exc
    return {
        **receipt,
        "status": "MEDORIGIN_UNPUBLISHED_QA_REPRODUCED",
        "zip_sha256": digest(contents),
        "output_path": str(output),
        "publication_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--sdist", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args(argv)
    try:
        result = assemble(
            arguments.repository.absolute(),
            arguments.wheel.absolute(),
            arguments.sdist.absolute(),
            arguments.provenance.absolute(),
            arguments.output.absolute(),
        )
    except (AssemblyError, OSError, ValueError, zipfile.BadZipFile):
        print("MEDORIGIN_UNPUBLISHED_QA_ASSEMBLY_BLOCKED", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
