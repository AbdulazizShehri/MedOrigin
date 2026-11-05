"""Physical owner Windows: verify, extract and UIA-test a private D2 ZIP.

Source/reproducibility acceptance only. Never installs, signs, publishes, opens
patient files or claims clinical readiness. Extraction is restricted to the
five exact canonical members validated by verify_preview.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from verify_preview import verify_archive

ARCHIVE_ROOT = "MedOrigin-Synthetic-Preview"
EXECUTABLE = "medorigin-desktop-d2-native-egui.exe"
MAX_ARCHIVE_BYTES = 140 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}")
TESTS = (
    (
        "windows-native-fhir-uia-qualification.ps1",
        "-ExpectedSha256",
        "D2_NATIVE_FHIR_UIA_8_OF_8_PASS_NONPUBLISHING",
    ),
    (
        "windows-native-fictional-workspace-uia.ps1",
        "-ExpectedSha256",
        "D2_WINDOWS_FICTIONAL_WORKSPACE_4_CASES_FILTER_AND_CLEAR_PASS_NOT_CLINICAL",
    ),
    (
        "windows-real-core963-file-batch-receipt-uia.ps1",
        "-ExpectedExeSha256",
        "D2_CORE_BATCH_OPENED_ONLY_ACTUAL_WINDOWS_UIA_PASS_NONCLINICAL",
    ),
)
MEMBERS = (
    EXECUTABLE,
    "LICENSE",
    "MANIFEST.json",
    "README-SYNTHETIC.txt",
    "UPSTREAM-NOTICE.md",
)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _regular_exact(path: Path, *, directory: bool) -> Path:
    if path.is_symlink() or not path.exists():
        raise ValueError("portable_qa_missing_or_reparse_path")
    if directory and not path.is_dir():
        raise ValueError("portable_qa_expected_directory")
    if not directory and not path.is_file():
        raise ValueError("portable_qa_expected_regular_file")
    resolved = path.resolve(strict=True)
    if resolved != path.absolute():
        raise ValueError("portable_qa_alias_path_refused")
    return resolved


def _extract_verified_archive(archive: Path, stage: Path, expected_binary: str) -> Path:
    # Verify every member against exact source-controlled canonical bytes before
    # touching the extraction directory. Recheck archive identity after opening.
    with zipfile.ZipFile(archive, "r") as zf:
        members = zf.infolist()
        wanted = [ARCHIVE_ROOT + "/" + name for name in MEMBERS]
        if sorted(info.filename for info in members) != sorted(wanted):
            raise ValueError("portable_qa_archive_members_not_allowlisted")
        target_root = stage / ARCHIVE_ROOT
        target_root.mkdir()
        for name in MEMBERS:
            source = ARCHIVE_ROOT + "/" + name
            output = target_root / name
            with zf.open(source, "r") as stream, output.open("xb") as destination:
                while chunk := stream.read(1024 * 1024):
                    destination.write(chunk)
    binary = target_root / EXECUTABLE
    if _sha(binary) != expected_binary:
        raise ValueError("portable_qa_extracted_binary_changed")
    return binary


def _owner_windows_x64() -> bool:
    return sys.platform == "win32" and platform.machine().lower() in ("amd64", "x86_64")


def qualify(
    archive: Path,
    repo: Path,
    scratch: Path,
    expected_archive_sha: str,
    expected_native_sha: str,
    *,
    runner=subprocess.run,
) -> None:
    if not _owner_windows_x64():
        raise ValueError("portable_qa_requires_owner_windows_x64")
    if not isinstance(expected_archive_sha, str) or not SHA.fullmatch(expected_archive_sha):
        raise ValueError("portable_qa_archive_sha_malformed")
    if not isinstance(expected_native_sha, str) or not SHA.fullmatch(expected_native_sha):
        raise ValueError("portable_qa_native_sha_malformed")
    archive = _regular_exact(archive, directory=False)
    repo = _regular_exact(repo, directory=True)
    scratch = _regular_exact(scratch, directory=True)
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("portable_qa_archive_oversized")
    if _sha(archive) != expected_archive_sha:
        raise ValueError("portable_qa_archive_identity_refused")
    # verify_archive demands the exact source commit, canonical manifest,
    # executable header, resource contents, modes and no extra ZIP members.
    manifest = verify_archive(archive, repo, "windows-x86_64")
    if manifest.get("binary_sha256") != expected_native_sha:
        raise ValueError("portable_qa_binary_identity_refused")
    if _sha(archive) != expected_archive_sha:
        raise ValueError("portable_qa_archive_changed_during_verification")

    scripts_dir = repo / "experiments" / "desktop-d2-native-egui" / "tests"
    scripts = []
    for name, option, success in TESTS:
        script = _regular_exact(scripts_dir / name, directory=False)
        scripts.append((script, option, success))
    with TemporaryDirectory(prefix="medorigin-private-extracted-qa-", dir=scratch) as temp:
        native = _extract_verified_archive(archive, Path(temp), expected_native_sha)
        if _sha(archive) != expected_archive_sha:
            raise ValueError("portable_qa_archive_changed_during_extract")
        for script, option, success in scripts:
            result = runner(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                    "-ExePath",
                    str(native),
                    option,
                    expected_native_sha,
                ],
                cwd=Path(temp),
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            if result.returncode != 0 or result.stderr or success not in result.stdout.splitlines():
                raise ValueError("portable_qa_actual_windows_uia_refused:" + script.name)
            if _sha(native) != expected_native_sha:
                raise ValueError("portable_qa_native_changed_during_gui")
            print("PORTABLE_EXTRACTED_WINDOWS_GUI_PASS=" + script.name)
    print("MEDORIGIN_PRIVATE_PORTABLE_WINDOWS_EXTRACTED_THREE_GUI_SUITES_PASS_NOT_RELEASED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--native-sha256", required=True)
    try:
        args = parser.parse_args()
        qualify(
            args.archive,
            args.repo,
            args.scratch,
            args.archive_sha256,
            args.native_sha256,
        )
    except (OSError, ValueError, EOFError, zipfile.BadZipFile, subprocess.TimeoutExpired):
        print("MEDORIGIN_PRIVATE_PORTABLE_WINDOWS_EXTRACTED_GUI_NO_GO", file=sys.stderr)
        raise SystemExit(2) from None
