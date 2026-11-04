# Windows Job Object — real synthetic descendant cleanup qualification

Date: 2026-11-04. **Private, non-clinical engineering evidence, no release.**

## Product security gap and tested contract

The previous D2 Mac installed-Core → GUI one-shot acceptance and its newly deadline-bounded stdin **do not supervise a real Python worker**. A Python worker can spawn subprocesses; killing only the parent PID may leave children running. Before integrating any real Python Core launcher on Windows, we need an OS-backed lifecycle primitive that also terminates descendants.

`scripts/qualify_windows_job_subtree.py` implements a **synthetic-only, no-dependency Windows Job Object proof** through the Windows kernel32 API (ctypes, CPython stdlib). It cannot accept arbitrary process paths or clinical input. Its Windows-only QA uses the current local Python interpreter with `-I -S -B`, and only fixed Python parent/child sleepers that write two process IDs to a disposable temporary path:

1. Create a private Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, without altering global Windows settings or requesting administrator privileges.
2. Start the exact fictional parent with `CreateProcessW(CREATE_SUSPENDED | CREATE_NO_WINDOW)`; importantly, it executes **zero instructions before** `AssignProcessToJobObject`.
3. Call `IsProcessInJob` on the suspended parent, then `ResumeThread` exactly once.
4. Parent spawns a fictional child. Read only the synthetic PID marker and open **that exact child** process handle. Check both processes are inside the same private Job Object and alive.
5. Close the **last private Job Object handle**; require both parent and child Win32 process handles become signaled within 5s. On every failed path, `finally` additionally kills only the owned job and handles and closes them; no broad process enumeration or machine-wide operations.

This is an actual Windows OS process-descendant lifecycle test; not merely source analysis. No external network, extra packages, Cloud GPU, patient data, EHR adapters, installer, administrator settings, or system firewall changes.

## Verified authorized Windows 11 result

Retrieved the exact private GitHub source blob (`4c6ff92da81d337d32aadc30e560f75c193ce6d5`) and checked it locally before executing. The following came from **real kernel32 calls** on the user's authorized Windows 11 PC, with exit 0:

```
WINDOWS_D2_JOB_PARENT_WAS_CREATED_SUSPENDED_ASSIGNED_BEFORE_RESUME
WINDOWS_D2_JOB_CHILD_INHERITED_SAME_JOB_AND_WAS_ALIVE_BEFORE_CLOSE
WINDOWS_D2_JOB_HANDLE_CLOSE_TERMINATED_PARENT_AND_CHILD
WINDOWS_D2_SOURCE_ONLY_JOB_OBJECT_PARENT_AND_CHILD_KILLED_ON_CLOSE_PASS
```

Source-controlled negative/source tests `scripts/test_windows_job_subtree.py`: **4/4 PASS** independently on the authorized Windows PC (and 4/4 on Mac for source-only checks). Hosted Windows and Ubuntu D2 CI run the **source-only** regression collection. The Windows runner **additionally executes this exact synthetic Job Object kernel proof** in a dedicated nonpublishing step; Ubuntu does not claim to exercise Windows Job Objects. A hosted failure is a real unresolved Windows compatibility gate, not an authorized waiver.

## Strictly unresolved

**Job Objects solve lifetime handling of assigned child processes, not their authority.** The tested parent is a synthetic sleeper, NOT a signed or verified installed Python Core interpreter, and the job does NOT block DNS/TCP/UDP, prevent malicious filesystem reads, implement low-integrity/AppContainer isolation, inspect DLL loads, enforce memory or CPU limits, or certify every possible breakaway/privileged process pattern. Cross-OS macOS/Linux child-lifetime and OS-enforced packet isolation remain unresolved. Clinical Core launch would need independently reviewed interpreter + installed-wheel + venv attestation, policy setup before first instruction, authenticated IPC, safe failure/recovery, no-PHI leaks, signed update chain, genuine credential/key custody and RBAC/consent, full FHIR R4/profile/terminology conformance, and independent security/medical approval.

This source is intentionally **a QA script, not yet called by the D2 GUI**; the original D2 Rust browserless/no-child-process source guard is unchanged. Do not call this production sandboxing, merge to main, sign, distribute or use with real patient data. Preserve open #574/#603/#662/#673/#676 and Dependabot security debt (66 default-branch alerts observed in this development cycle).
