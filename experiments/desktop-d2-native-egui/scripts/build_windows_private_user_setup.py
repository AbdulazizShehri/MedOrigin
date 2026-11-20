#!/usr/bin/env python3
"""Build a PRIVATE unsigned Windows x64 self-extracting fictional D2 setup.

No clinical release, patients, network downloads, third-party installer, or
publisher attestation. Uses Windows' built-in IExpress + canonical reviewed ZIP.
Never runs/installs the generated EXE; owner-local QA must test separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from package_preview import commit_of, inspect_native_header
from verify_preview import verify_archive

ARCHIVE_ROOT = "MedOrigin-Synthetic-Preview"
FILES = (
    "medorigin-desktop-d2-native-egui.exe",
    "LICENSE",
    "MANIFEST.json",
    "README-SYNTHETIC.txt",
    "UPSTREAM-NOTICE.md",
)
SHA = re.compile(r"[0-9a-f]{64}")
SAFE_DRIVE_PATH = re.compile(r"[A-Za-z]:\\[A-Za-z0-9 _.~\\-]+")
INSTALLER_SCRIPT = "Install-MedOrigin-Private.ps1"
INSTALLER_COMMAND = "Install-MedOrigin-Private.cmd"
REVIEWED_ARCHIVE = "MedOrigin-Reviewed-Archive.zip"
MAX_BINARY = 120 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _real_path(path: Path, *, directory: bool) -> Path:
    if path.is_symlink() or not path.exists():
        raise ValueError("missing_or_reparse_input_path")
    # Stop at an actual reparse ancestor, including junctions on Python 3.11.
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError("symlink_ancestor_refused")
        if sys.platform == "win32":
            attrs = getattr(ancestor.lstat(), "st_file_attributes", None)
            if attrs is None or attrs & 0x400:
                raise ValueError("windows_reparse_ancestor_refused")
    if directory and not path.is_dir():
        raise ValueError("expected_reviewed_directory")
    if not directory and not path.is_file():
        raise ValueError("expected_reviewed_file")
    return path.resolve(strict=True)


def _safe_sed_path(path: Path) -> str:
    spelling = str(path)
    if len(spelling) > 230:
        raise ValueError("unreviewed_iexpress_sed_windows_path:length_refused")
    if not SAFE_DRIVE_PATH.fullmatch(spelling):
        # Do not expose absolute CI/user paths. Only character-code diagnostics
        # distinguish benign platform path spellings from SED injection.
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 _.~\\-:")
        codes = sorted({f"U+{ord(ch):04X}" for ch in spelling if ch not in allowed})
        raise ValueError(
            "unreviewed_iexpress_sed_windows_path:characters_refused:"
            + "codes="
            + ",".join(codes[:12])
            + ";length="
            + str(len(spelling))
            + ";drive="
            + str(len(spelling) > 2 and spelling[1] == ":")
            + ";backslashes="
            + str(spelling.count("\\"))
        )
    return spelling


def _read_exact_zip_members(archive: Path) -> dict[str, bytes]:
    expected = {ARCHIVE_ROOT + "/" + name for name in FILES}
    with zipfile.ZipFile(archive, "r") as zf:
        members = zf.infolist()
        if len(members) != len(expected) or {x.filename for x in members} != expected:
            raise ValueError("setup_unexpected_duplicate_or_extra_zip_members")
        output = {}
        for member in members:
            max_size = MAX_BINARY if member.filename.endswith(".exe") else 1024 * 1024
            if member.file_size < 0 or member.file_size > max_size:
                raise ValueError("setup_zip_member_size_refused")
            with zf.open(member, "r") as source:
                payload = source.read(max_size + 1)
            if len(payload) != member.file_size:
                raise ValueError("setup_zip_member_decompressed_size_refused")
            output[member.filename.removeprefix(ARCHIVE_ROOT + "/")] = payload
    return output


def render_script(
    template: str, source_commit: str, files: dict[str, bytes], archive_sha256: str
) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit) or set(files) != set(FILES):
        raise ValueError("setup_source_or_member_set_refused")
    if not SHA.fullmatch(archive_sha256):
        raise ValueError("setup_archive_digest_refused")
    required = ("__EXPECTED_COMMIT__", "__EXPECTED_HASHES__", "__EXPECTED_ARCHIVE_SHA256__")
    if any(template.count(marker) != 1 for marker in required):
        raise ValueError("setup_template_identity_missing")
    pins = "\n".join("    '" + name + "'='" + digest(files[name]) + "'" for name in sorted(FILES))
    return (
        template.replace("__EXPECTED_COMMIT__", source_commit)
        .replace("__EXPECTED_HASHES__", pins)
        .replace("__EXPECTED_ARCHIVE_SHA256__", archive_sha256)
    )


def render_sed(stage: Path, target: Path) -> str:
    source = _safe_sed_path(stage)
    destination = _safe_sed_path(target)
    # IExpress no longer redundantly compresses a 34 MB executable. It
    # carries only the already source-verified, hash-pinned canonical ZIP.
    names = (INSTALLER_COMMAND, INSTALLER_SCRIPT, REVIEWED_ARCHIVE)
    file_literals = "\n".join(f'FILE{i}="{name}"' for i, name in enumerate(names))
    file_slots = "\n".join(f"%FILE{i}%=" for i in range(len(names)))
    return (
        "[Version]\nClass=IEXPRESS\nSEDVersion=3\n[Options]\n"
        "PackagePurpose=InstallApp\nShowInstallProgramWindow=0\n"
        "HideExtractAnimation=1\nUseLongFileName=1\nInsideCompressed=0\n"
        "CAB_FixedSize=0\nCAB_ResvCodeSigning=0\nRebootMode=N\n"
        "InstallPrompt=%InstallPrompt%\nDisplayLicense=%DisplayLicense%\n"
        "FinishMessage=%FinishMessage%\nTargetName=%TargetName%\n"
        "FriendlyName=%FriendlyName%\nAppLaunched=%AppLaunched%\n"
        "PostInstallCmd=%PostInstallCmd%\nAdminQuietInstCmd=%AdminQuietInstCmd%\n"
        "UserQuietInstCmd=%UserQuietInstCmd%\nSourceFiles=SourceFiles\n"
        "[Strings]\nInstallPrompt=\nDisplayLicense=\nFinishMessage=\n"
        f"TargetName={destination}\n"
        "FriendlyName=MedOrigin Synthetic Private Preview (NOT clinical)\n"
        f"AppLaunched=cmd.exe /d /c {INSTALLER_COMMAND}\n"
        "PostInstallCmd=<None>\nAdminQuietInstCmd=\nUserQuietInstCmd=\n"
        f"{file_literals}\n[SourceFiles]\nSourceFiles0={source}\\\n"
        f"[SourceFiles0]\n{file_slots}\n"
    )


def _run_iexpress(sed: Path, target: Path) -> None:
    """Build under a kill-on-close Windows Job; never orphan makecab.exe."""
    import ctypes
    from ctypes import wintypes

    from qualify_windows_job_subtree import (
        CREATE_NO_WINDOW,
        CREATE_SUSPENDED,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION_STRUCT,
        PROCESS_INFORMATION,
        STARTUPINFOW,
        WAIT_OBJECT_0,
        WAIT_TIMEOUT,
        _require,
        _win32,
    )

    executable = Path(os.environ.get("WINDIR", "C:\\Windows")) / "System32" / "iexpress.exe"
    _real_path(executable, directory=False)
    api = _win32()
    api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    api.GetExitCodeProcess.restype = wintypes.BOOL
    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(startup)
    parent = PROCESS_INFORMATION()
    job = None
    limit = JOBOBJECT_EXTENDED_LIMIT_INFORMATION_STRUCT()
    limit.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    try:
        job = api.CreateJobObjectW(None, None)
        _require(job, "create_private_iexpress_job")
        _require(
            api.SetInformationJobObject(
                job,
                JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(limit),
                ctypes.sizeof(limit),
            ),
            "set_iexpress_subtree_kill_on_close",
        )
        command = ctypes.create_unicode_buffer(
            subprocess.list2cmdline([str(executable), "/N", "/Q", str(sed)])
        )
        _require(
            api.CreateProcessW(
                str(executable),
                command,
                None,
                None,
                False,
                CREATE_SUSPENDED | CREATE_NO_WINDOW,
                None,
                str(sed.parent),
                ctypes.byref(startup),
                ctypes.byref(parent),
            ),
            "create_suspended_iexpress",
        )
        _require(
            api.AssignProcessToJobObject(job, parent.hProcess),
            "attach_iexpress_to_private_job",
        )
        if api.ResumeThread(parent.hThread) != 1:
            raise ValueError("iexpress_parent_resume_refused")
        result = api.WaitForSingleObject(parent.hProcess, 240_000)
        if result == WAIT_TIMEOUT:
            raise ValueError("windows_iexpress_builder_timed_out_subtree_terminated")
        if result != WAIT_OBJECT_0:
            raise ValueError("windows_iexpress_builder_wait_failed")
        exit_code = wintypes.DWORD()
        _require(
            api.GetExitCodeProcess(parent.hProcess, ctypes.byref(exit_code)),
            "read_iexpress_exit_code",
        )
        if exit_code.value != 0:
            raise ValueError("windows_iexpress_builder_failed")

        # IExpress can exit before its cabinet child finishes writing.
        # The Job stays open throughout the stability checks, so any child
        # is terminated even when an exception aborts packaging.
        stable = 0
        prior = -1
        for _ in range(150):
            size = target.stat().st_size if target.exists() else 0
            if size >= 175_000 and size == prior:
                stable += 1
            else:
                stable = 0
            if stable >= 12:
                with target.open("rb") as f:
                    header = f.read(4096)
                if inspect_native_header(header) != ("windows", "x86_64"):
                    raise ValueError("iexpress_output_not_windows_x64_executable")
                return
            prior = size
            time.sleep(0.2)
        raise ValueError("windows_iexpress_builder_output_not_stable")
    finally:
        if parent.hThread:
            api.CloseHandle(parent.hThread)
        if parent.hProcess:
            api.CloseHandle(parent.hProcess)
        if job:
            api.CloseHandle(job)  # Kill only this builder's IExpress/makecab tree.


def build(
    archive: Path, repo: Path, out: Path, expected_archive: str, expected_native: str
) -> Path:
    if sys.platform != "win32":
        raise ValueError("windows_only_private_setup")
    if not SHA.fullmatch(expected_archive) or not SHA.fullmatch(expected_native):
        raise ValueError("setup_expected_digest_refused")
    archive = _real_path(archive, directory=False)
    repo = _real_path(repo, directory=True)
    parent = _real_path(out.parent, directory=True)
    _safe_sed_path(parent)
    if out.exists() or out.is_symlink():
        raise ValueError("private_setup_output_already_exists")
    if digest(archive.read_bytes()) != expected_archive:
        raise ValueError("private_setup_archive_sha256_refused")
    manifest = verify_archive(archive, repo, "windows-x86_64")
    if manifest.get("binary_sha256") != expected_native:
        raise ValueError("private_setup_native_sha256_refused")
    files = _read_exact_zip_members(archive)
    if digest(files[FILES[0]]) != expected_native:
        raise ValueError("private_setup_extracted_sha256_refused")
    if digest(archive.read_bytes()) != expected_archive:
        raise ValueError("private_setup_archive_changed_after_verify")
    commit = commit_of(repo)
    template_path = (
        repo
        / "experiments"
        / "desktop-d2-native-egui"
        / "scripts"
        / "windows_private_user_setup.template.ps1"
    )
    template = _real_path(template_path, directory=False).read_text(encoding="utf-8")
    script = render_script(template, commit, files, expected_archive)
    # Only a task-owned local builder output directory; no system installation.
    out.mkdir(mode=0o700)
    target = out / f"MedOrigin-Synthetic-Private-Setup-{commit[:8]}.exe"
    with tempfile.TemporaryDirectory(prefix="medorigin-iexpress-", dir=parent) as name:
        stage = Path(name)
        _safe_sed_path(stage)
        # Stage the exact canonical ZIP rather than a second 34 MB
        # decompression/recompression pass over the native executable.
        # Rechecking its hash closes the verification-to-staging gap.
        if digest(archive.read_bytes()) != expected_archive:
            raise ValueError("private_setup_archive_changed_before_stage")
        (stage / REVIEWED_ARCHIVE).write_bytes(archive.read_bytes())
        if digest((stage / REVIEWED_ARCHIVE).read_bytes()) != expected_archive:
            raise ValueError("private_setup_staged_archive_sha256_refused")
        (stage / INSTALLER_SCRIPT).write_bytes(script.replace("\n", "\r\n").encode("utf-8"))
        (stage / INSTALLER_COMMAND).write_bytes(
            (
                "@echo off\r\nsetlocal DisableDelayedExpansion\r\n"
                "echo MedOrigin PRIVATE SYNTHETIC preview ONLY. NEVER patient data.\r\n"
                "%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe "
                "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass "
                f'-File "%~dp0{INSTALLER_SCRIPT}" -Action Install\r\n'
                "exit /b %ERRORLEVEL%\r\n"
            ).encode("ascii")
        )
        sed = stage / "private.sed"
        sed.write_text(render_sed(stage, target), encoding="ascii")
        _run_iexpress(sed, target)
    if digest(archive.read_bytes()) != expected_archive:
        raise ValueError("private_setup_archive_changed_during_build")
    print(
        json.dumps(
            {
                "status": "PRIVATE_SYNTHETIC_UNSIGNED_WINDOWS_SETUP_BUILT_NOT_RELEASED",
                "source_commit": commit,
                "setup": str(target),
                "setup_sha256": digest(target.read_bytes()),
                "binary_sha256": expected_native,
                "archive_sha256": expected_archive,
                "signed": False,
                "clinical_use": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--native-sha256", required=True)
    args = parser.parse_args()
    try:
        build(args.archive, args.repo, args.output, args.archive_sha256, args.native_sha256)
    except (
        OSError,
        ValueError,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
        KeyError,
    ) as error:
        print("MEDORIGIN_PRIVATE_WINDOWS_SETUP_NO_GO: " + str(error), file=sys.stderr)
        sys.exit(2)
