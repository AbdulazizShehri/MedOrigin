#!/usr/bin/env python3
"""Windows Job Object owned fixed Core encrypted catalog worker (fictional).

Actual source Core process is created SUSPENDED, assigned to private
kill-on-close Windows Job, and ONLY THEN resumed. This controls its lifetime
and descendants, NOT its network/FS/secret permissions. No PHI/production.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess

from qualify_windows_job_subtree import (
    CREATE_NO_WINDOW, CREATE_SUSPENDED,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION_STRUCT,
    PROCESS_INFORMATION, STARTUPINFOW,
    WAIT_OBJECT_0, WAIT_TIMEOUT, _require, _win32,
)

CREATE_UNICODE_ENVIRONMENT = 0x00000400
CATALOG_BYTES = 799
PINNED_CODE = (
    "import sys,pathlib,importlib.metadata as m;"
    "sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]];"
    "assert m.version('cryptography')=='50.0.1';"
    "assert m.version('cffi')=='2.1.1';"
    "from medscale.fhirkit.workspace_catalog_demo import receipt_json;"
    "body=receipt_json().encode('utf-8');"
    "assert len(body)==799;"
    "pathlib.Path(sys.argv[4]).write_bytes(body)"
)


def real_catalog_under_windows_job(
    python: Path, core: Path, site: Path, work: Path,
) -> bytes:
    if (
        os.name != "nt" or python.is_symlink()
        or not python.is_file() or python.name.lower() != "python.exe"
        or core.is_symlink() or not (core / "src/medscale").is_dir()
        or not (core / "apps/workspace/src/medscale_workspace").is_dir()
        or site.is_symlink() or not site.is_dir()
        or work.is_symlink() or not work.is_dir()
    ):
        raise ValueError("reviewed_synthetic_catalog_windows_job_preconditions_refused")
    target = work / "real-verified-synthetic-import-catalog-job.json"
    if target.exists() or target.is_symlink():
        raise ValueError("synthetic_catalog_job_result_preexisting_refused")
    system_root = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    child_env = {
        "PATH": os.pathsep.join((str(python.parent), str(system_root / "System32"))),
        "SYSTEMROOT": str(system_root),
        "WINDIR": str(system_root),
        "TEMP": str(work),
        "TMP": str(work),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env_block = ctypes.create_unicode_buffer(
        "\x00".join(f"{key}={value}" for key,value in sorted(child_env.items())) + "\x00\x00"
    )
    api = _win32()
    api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    api.GetExitCodeProcess.restype = wintypes.BOOL
    policy = JOBOBJECT_EXTENDED_LIMIT_INFORMATION_STRUCT()
    policy.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    proc = PROCESS_INFORMATION()
    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(startup)
    job = None
    try:
        job = api.CreateJobObjectW(None, None)
        _require(job, "create_private_synthetic_catalog_job")
        _require(
            api.SetInformationJobObject(
                job, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(policy), ctypes.sizeof(policy),
            ),
            "set_synthetic_catalog_kill_on_close",
        )
        cmd = subprocess.list2cmdline([
            str(python), "-I", "-S", "-B", "-c", PINNED_CODE,
            str(core / "src"), str(core / "apps/workspace/src"),
            str(site), str(target),
        ])
        cmd_buffer = ctypes.create_unicode_buffer(cmd)
        _require(
            api.CreateProcessW(
                str(python), cmd_buffer, None, None, False,
                CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
                ctypes.cast(env_block, ctypes.c_void_p), str(work),
                ctypes.byref(startup), ctypes.byref(proc),
            ),
            "create_real_core_catalog_suspended",
        )
        _require(
            api.AssignProcessToJobObject(job, proc.hProcess),
            "real_catalog_core_job_assigned_before_python_start",
        )
        confirmed = wintypes.BOOL(False)
        _require(
            api.IsProcessInJob(proc.hProcess, job, ctypes.byref(confirmed))
            and confirmed.value,
            "real_catalog_core_job_membership_refused",
        )
        print("WINDOWS_REAL_CATALOG_CORE_ASSIGNED_JOB_BEFORE_PYTHON_EXECUTION")
        if api.ResumeThread(proc.hThread) != 1:
            raise ValueError("real_catalog_initial_thread_resume_refused")
        if api.WaitForSingleObject(proc.hProcess, 45000) != WAIT_OBJECT_0:
            raise ValueError("supervised_catalog_Core_timeout_or_child_not_exited")
        exit_code = wintypes.DWORD(255)
        _require(
            api.GetExitCodeProcess(proc.hProcess, ctypes.byref(exit_code)),
            "read_synthetic_catalog_Core_exit_code",
        )
        if exit_code.value != 0:
            raise ValueError("real_catalog_Core_worker_exit_nonzero")
        if target.is_symlink() or not target.is_file() or target.stat().st_size != CATALOG_BYTES:
            raise ValueError("real_catalog_Core_job_result_not_exact_size")
        value = target.read_bytes()
        if len(value) != CATALOG_BYTES:
            raise ValueError("real_catalog_Core_job_result_size_changed")
        print("WINDOWS_REAL_CORE_ENCRYPTED_CATALOG_JOB_FINISHED_AND_BOUNDED")
        return value
    finally:
        if job:
            api.TerminateJobObject(job, 1)
            api.CloseHandle(job)
        if proc.hProcess:
            if api.WaitForSingleObject(proc.hProcess, 0) == WAIT_TIMEOUT:
                api.TerminateProcess(proc.hProcess, 1)
                api.WaitForSingleObject(proc.hProcess, 3000)
            api.CloseHandle(proc.hProcess)
        if proc.hThread:
            api.CloseHandle(proc.hThread)
