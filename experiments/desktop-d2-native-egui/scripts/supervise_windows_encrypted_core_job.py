#!/usr/bin/env python3
"""Private Windows Job Object lifetime owner for fictional encrypted Core readback.

Execute an exact source-pinned Python Core worker suspended and assign it to
our kill-on-close Job BEFORE any Python instruction executes. No admin/global
policy. This is NOT network confinement, authenticated IPC or clinical use.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
from ctypes import wintypes
from pathlib import Path

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

CREATE_UNICODE_ENVIRONMENT = 0x00000400
REVIEWED_PROJECTION_BYTES = 1164
SOURCE_RUNNER = (
    "import sys,runpy,importlib.metadata as m,pathlib;"
    "sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]];"
    "assert m.version('cryptography')=='50.0.1';"
    "assert m.version('cffi')=='2.1.1';"
    "source=sys.argv[4];out=sys.argv[5];sys.argv=[source];"
    "module=runpy.run_path(source,run_name='medorigin_installed_synthetic_QA');"
    "payload=module['exact_synthetic_encrypted_readback_projection']();"
    "assert type(payload) is bytes and len(payload)==1164;"
    "pathlib.Path(out).write_bytes(payload)"
)

# Fully isolated installed-source route: Core modules must resolve ONLY to the
# byte-attested, private target, never to the reviewed source checkout.
INSTALLED_RUNNER = (
    "import sys,runpy,importlib.metadata as m,pathlib;"
    "sys.path[:0]=[sys.argv[1],sys.argv[2]];"
    "import medscale,medscale_workspace;"
    "root=pathlib.Path(sys.argv[1]).resolve();"
    "assert pathlib.Path(medscale.__file__).resolve()==root/'medscale/__init__.py';"
    "assert pathlib.Path(medscale_workspace.__file__).resolve()==root/"
    "'medscale_workspace/__init__.py';"
    "assert m.version('cryptography')=='50.0.1';"
    "assert m.version('cffi')=='2.1.1';"
    "source=sys.argv[3];out=sys.argv[4];sys.argv=[source];"
    "module=runpy.run_path(source,run_name='medorigin_installed_synthetic_QA');"
    "payload=module['exact_synthetic_encrypted_readback_projection']();"
    "assert type(payload) is bytes and len(payload)==1164;"
    "pathlib.Path(out).write_bytes(payload)"
)


def execute_encrypted_source_under_job(
    python: Path,
    core: Path | None,
    site: Path,
    exporter: Path,
    work: Path,
    *,
    installed_site: Path | None = None,
) -> bytes:
    if (
        os.name != "nt"
        or not work.is_dir()
        or not python.is_file()
        or python.name.lower() != "python.exe"
        or (core is None and installed_site is None)
        or (
            core is not None
            and (not (core / "src").is_dir() or not (core / "apps/workspace/src").is_dir())
        )
        or not site.is_dir()
        or not exporter.is_file()
        or any(path.is_symlink() for path in (python, site, exporter, work))
        or (core is not None and core.is_symlink())
    ):
        raise ValueError("reviewed_windows_job_core_prerequisites_refused")
    if installed_site is not None and (
        installed_site.is_symlink()
        or not installed_site.is_dir()
        or (core is not None and installed_site.resolve() == core.resolve())
        or any((installed_site / p).is_symlink() for p in ("medscale", "medscale_workspace"))
    ):
        raise ValueError("installed_core_target_not_attested_or_unavailable")
    output = work / "synthetic-core-readback-job-only.json"
    if output.exists() or output.is_symlink():
        raise ValueError("fictional_job_output_preexisting_refused")
    system = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    env = {
        "PATH": os.pathsep.join((str(python.parent), str(system / "System32"))),
        "SYSTEMROOT": str(system),
        "WINDIR": str(system),
        "TEMP": str(work),
        "TMP": str(work),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    # Unicode environment, sorted, with trailing double NUL. It is owned
    # by this call and applied only to its one suspended worker process.
    envblock = ctypes.create_unicode_buffer(
        "\x00".join(f"{key}={value}" for key, value in sorted(env.items())) + "\x00\x00"
    )
    api = _win32()
    api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    api.GetExitCodeProcess.restype = wintypes.BOOL
    info = PROCESS_INFORMATION()
    start = STARTUPINFOW()
    start.cb = ctypes.sizeof(start)
    policy = JOBOBJECT_EXTENDED_LIMIT_INFORMATION_STRUCT()
    policy.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    job = None
    try:
        job = api.CreateJobObjectW(None, None)
        _require(job, "create_private_encrypted_core_job")
        _require(
            api.SetInformationJobObject(
                job,
                JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(policy),
                ctypes.sizeof(policy),
            ),
            "set_core_job_kill_on_close",
        )
        if installed_site is not None:
            runner = INSTALLED_RUNNER
            worker_args = [str(installed_site), str(site), str(exporter), str(output)]
        else:
            if core is None:
                raise ValueError("source_checkpoint_required_for_noninstalled_worker")
            runner = SOURCE_RUNNER
            worker_args = [
                str(core / "src"),
                str(core / "apps/workspace/src"),
                str(site),
                str(exporter),
                str(output),
            ]
        command = subprocess.list2cmdline(
            [
                str(python),
                "-I",
                "-S",
                "-B",
                "-c",
                runner,
                *worker_args,
            ]
        )
        command_buffer = ctypes.create_unicode_buffer(command)
        _require(
            api.CreateProcessW(
                str(python),
                command_buffer,
                None,
                None,
                False,
                CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
                ctypes.cast(envblock, ctypes.c_void_p),
                str(work),
                ctypes.byref(start),
                ctypes.byref(info),
            ),
            "create_suspended_reviewed_core_source_only",
        )
        _require(
            api.AssignProcessToJobObject(job, info.hProcess),
            "assign_real_encrypted_core_before_first_instruction",
        )
        is_member = wintypes.BOOL(False)
        _require(
            api.IsProcessInJob(info.hProcess, job, ctypes.byref(is_member)) and is_member.value,
            "real_core_job_membership_not_confirmed_before_resume",
        )
        print("WINDOWS_REAL_CORE_CREATED_SUSPENDED_ASSIGNED_JOB_BEFORE_EXECUTION")
        if api.ResumeThread(info.hThread) != 1:
            raise ValueError("real_core_initial_thread_not_resumed_exactly_once")
        if api.WaitForSingleObject(info.hProcess, 45_000) != WAIT_OBJECT_0:
            raise ValueError("real_core_supervised_job_timeout_or_not_exited")
        exit_status = wintypes.DWORD(255)
        _require(
            api.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_status)),
            "get_real_core_supervised_exit_code",
        )
        if exit_status.value != 0:
            raise ValueError("real_core_supervised_worker_returned_nonzero")
        if (
            output.is_symlink()
            or not output.is_file()
            or output.stat().st_size != REVIEWED_PROJECTION_BYTES
        ):
            raise ValueError("real_core_job_output_missing_or_wrong_size")
        raw = output.read_bytes()
        if len(raw) != REVIEWED_PROJECTION_BYTES:
            raise ValueError("real_core_job_output_bytes_refused")
        print("WINDOWS_REAL_CORE_JOB_WORKER_EXIT_ZERO_AND_OUTPUT_BOUNDED")
        return raw
    finally:
        # Closing this exact job kills any accidental child/grandchild that
        # Core might have started. The separate #920 owner-child proof tests
        # this OS mechanism with an actual synthetic descendant.
        if job:
            api.TerminateJobObject(job, 1)
            api.CloseHandle(job)
        if info.hProcess:
            if api.WaitForSingleObject(info.hProcess, 0) == WAIT_TIMEOUT:
                api.TerminateProcess(info.hProcess, 1)
                api.WaitForSingleObject(info.hProcess, 3000)
            api.CloseHandle(info.hProcess)
        if info.hThread:
            api.CloseHandle(info.hThread)
        # The source caller owns the private TemporaryDirectory and deletes
        # it after exact SHA/canonical proof and native GUI use.
