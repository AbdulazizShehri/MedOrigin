#!/usr/bin/env python3
"""Real Windows Job Object descendant lifetime proof — fictional QA only.

This proof never launches Core, user-specified code, EHR or patient data.
No admin rights, firewall, system settings or permanent job profile changes.
The synthetic parent MUST be created suspended and assigned to the job
BEFORE its very first instruction executes, then spawn a fictional child.
Closing the private job handle MUST terminate both.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOBOBJECT_EXTENDED_LIMIT_INFORMATION = 9
PROCESS_QUERY_LIMITED_INFORMATION = 0x00001000
SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
INVALID_RESUME = 0xFFFFFFFF
SUCCESS = "WINDOWS_D2_SOURCE_ONLY_JOB_OBJECT_PARENT_AND_CHILD_KILLED_ON_CLOSE_PASS"
CHILD_CODE = "import time;time.sleep(60)"
PARENT_CODE = (
    "import os,pathlib,subprocess,sys,time;"
    "child=subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time;time.sleep(60)'],"
    "close_fds=True);"
    "pathlib.Path(sys.argv[1]).write_text(f'{os.getpid()} {child.pid}',encoding='ascii');"
    "time.sleep(60)"
)


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):  # noqa: N801
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):  # noqa: N801
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):  # noqa: N801
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION_STRUCT(ctypes.Structure):  # noqa: N801
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def _win32():
    if sys.platform != "win32":
        raise ValueError("windows_host_required_no_macos_linux_approval")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    api.CreateJobObjectW.restype = wintypes.HANDLE
    api.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    api.SetInformationJobObject.restype = wintypes.BOOL
    api.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW),
        ctypes.POINTER(PROCESS_INFORMATION),
    ]
    api.CreateProcessW.restype = wintypes.BOOL
    api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    api.AssignProcessToJobObject.restype = wintypes.BOOL
    api.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    api.IsProcessInJob.restype = wintypes.BOOL
    api.ResumeThread.argtypes = [wintypes.HANDLE]
    api.ResumeThread.restype = wintypes.DWORD
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    api.TerminateJobObject.restype = wintypes.BOOL
    api.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    api.TerminateProcess.restype = wintypes.BOOL
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    return api


def _require(success, label: str):
    if not success:
        code = ctypes.get_last_error()
        raise ValueError(f"{label}_win32_error_{code}")


def qualify() -> None:
    api = _win32()
    if not Path(sys.executable).is_file():
        raise ValueError("local_python_interpreter_not_regular")
    if os.environ.get("MEDORIGIN_ALLOW_PATIENT_QA") is not None:
        raise ValueError("clinical_environment_variable_prohibited")
    job = None
    parent = PROCESS_INFORMATION()
    child_handle = None
    with tempfile.TemporaryDirectory(prefix="medorigin-d2-synthetic-job-") as tmp:
        marker = Path(tmp) / "fictional-pids-only.txt"
        startup = STARTUPINFOW()
        startup.cb = ctypes.sizeof(startup)
        limit = JOBOBJECT_EXTENDED_LIMIT_INFORMATION_STRUCT()
        limit.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        try:
            job = api.CreateJobObjectW(None, None)
            _require(job, "create_private_job")
            _require(
                api.SetInformationJobObject(
                    job,
                    JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
                    ctypes.byref(limit),
                    ctypes.sizeof(limit),
                ),
                "set_kill_on_job_handle_close",
            )
            # No arbitrary command. Fixed Python with -I/-S/-B and only
            # two synthetic 60-second sleepers for lifecycle verification.
            cmd = subprocess.list2cmdline(
                [sys.executable, "-I", "-S", "-B", "-c", PARENT_CODE, str(marker)]
            )
            cmdline = ctypes.create_unicode_buffer(cmd)
            _require(
                api.CreateProcessW(
                    str(Path(sys.executable).resolve()),
                    cmdline,
                    None,
                    None,
                    False,
                    CREATE_SUSPENDED | CREATE_NO_WINDOW,
                    None,
                    tmp,
                    ctypes.byref(startup),
                    ctypes.byref(parent),
                ),
                "create_suspended_fictional_worker",
            )
            _require(
                api.AssignProcessToJobObject(job, parent.hProcess),
                "assign_before_first_instruction",
            )
            included = wintypes.BOOL(False)
            _require(
                api.IsProcessInJob(parent.hProcess, job, ctypes.byref(included)) and included.value,
                "suspended_parent_job_membership",
            )
            if api.ResumeThread(parent.hThread) != 1:
                raise ValueError("resume_exactly_one_suspended_parent_thread_refused")
            pids = None
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if marker.exists():
                    tokens = marker.read_text(encoding="ascii").strip().split(" ")
                    if len(tokens) == 2 and all(x.isdecimal() for x in tokens):
                        pids = (int(tokens[0]), int(tokens[1]))
                        break
                time.sleep(0.1)
            if pids is None or pids[0] != parent.dwProcessId or pids[1] == pids[0]:
                raise ValueError("supervised_worker_did_not_produce_fictional_child")
            child_handle = api.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pids[1]
            )
            _require(child_handle, "open_owned_fictional_child")
            child_in_job = wintypes.BOOL(False)
            _require(
                api.IsProcessInJob(child_handle, job, ctypes.byref(child_in_job))
                and child_in_job.value,
                "spawned_child_missing_job_membership",
            )
            if (
                api.WaitForSingleObject(parent.hProcess, 0) != WAIT_TIMEOUT
                or api.WaitForSingleObject(child_handle, 0) != WAIT_TIMEOUT
            ):
                raise ValueError("synthetic_parent_or_child_exited_before_job_close")
            # This is the tested policy: last private job handle close MUST
            # terminate *both* parent and child without querying parent PID
            # to chase/check descendants manually.
            _require(api.CloseHandle(job), "close_private_job_with_children")
            job = None
            if (
                api.WaitForSingleObject(parent.hProcess, 5000) != WAIT_OBJECT_0
                or api.WaitForSingleObject(child_handle, 5000) != WAIT_OBJECT_0
            ):
                raise ValueError("job_handle_close_failed_to_terminate_descendants")
            print("WINDOWS_D2_JOB_PARENT_WAS_CREATED_SUSPENDED_ASSIGNED_BEFORE_RESUME")
            print("WINDOWS_D2_JOB_CHILD_INHERITED_SAME_JOB_AND_WAS_ALIVE_BEFORE_CLOSE")
            print("WINDOWS_D2_JOB_HANDLE_CLOSE_TERMINATED_PARENT_AND_CHILD")
            print(SUCCESS)
        finally:
            # Only our own test job and its exact created child handles.
            # Never enumerate, change or kill unrelated processes.
            if job:
                api.TerminateJobObject(job, 1)
                api.CloseHandle(job)
            if parent.hProcess:
                if api.WaitForSingleObject(parent.hProcess, 0) == WAIT_TIMEOUT:
                    api.TerminateProcess(parent.hProcess, 1)
                    api.WaitForSingleObject(parent.hProcess, 3000)
                api.CloseHandle(parent.hProcess)
            if child_handle:
                if api.WaitForSingleObject(child_handle, 0) == WAIT_TIMEOUT:
                    api.TerminateProcess(child_handle, 1)
                    api.WaitForSingleObject(child_handle, 3000)
                api.CloseHandle(child_handle)
            if parent.hThread:
                api.CloseHandle(parent.hThread)


if __name__ == "__main__":
    try:
        qualify()
    except (OSError, ValueError, UnicodeError) as exc:
        print("WINDOWS_D2_JOB_SUBTREE_LIFETIME_NO_GO:" + str(exc), file=sys.stderr)
        sys.exit(2)
