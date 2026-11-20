# Windows: real fictional Core encrypted readback under a Job Object

Private D2 developer QA, **NO-GO for patient/clinical production**. This is real Windows process-lifetime engineering, not just an invented source-only packet. It builds on the reviewed private #920 Windows Job subtree proof and #929 Core encrypted memory-readback UX, stacked on #931 installed Wheel QA.

## Problem fixed

Earlier Windows `scripts/qualify_windows_encrypted_readback_native_gui.py` ran the real source-bound encrypted Core import/reopen/readback with `subprocess.run`, which did not enroll Core or its descendants in the already independently tested private Windows **kill-on-job-close** contract. A timeout would terminate the initial worker but was not itself proof of child/grandchild cleanup.

New `scripts/supervise_windows_encrypted_core_job.py` now implements the Windows source-only Core worker as follows:

1. Validate exact reviewed interpreter, Core source checkout and local system-crypto package prerequisites through the caller. Accept only the fixed 3-resource fictional Core source code; no user JSON, patient paths, URL, model command or encryption key. Worker receives an owned disposable output file path within this QA runner's temporary directory.
2. Create a **private non-admin Job Object** with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Build an explicit minimal child environment (no inherited `PYTHONPATH`, credentials or cloud app configuration).
3. Call Win32 `CreateProcessW(CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT)` using the exact reviewed `python.exe` as `lpApplicationName`, fixed `-I -S -B -c` code and only source-installed QA import roots.
4. Call `AssignProcessToJobObject`, then **verify `IsProcessInJob`**, *before* calling `ResumeThread`. No Python instruction executes before the Job membership is verified.
5. Wait no more than 45 seconds for that worker; insist on `WAIT_OBJECT_0`, actual Win32 `GetExitCodeProcess == 0`, one exact 1,164-byte synthetic readback output and a verified regular non-symlink result. The caller still compares **every output byte and SHA-256** to the source-compiled fixture `c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49`.
6. In `finally`, terminate/close the **owned Job Object** (killing any descendant), wait/terminate the owned original worker if necessary, close its exact process and thread handles. The caller then drives actual D2 Windows UIAutomation and removes its private temp directory.

The original independent `scripts/qualify_windows_job_subtree.py` OS test remains as evidence that Job closing *really* terminates a Windows parent and an explicitly spawned descendant, including proof both were alive beforehand. Neither script changes host firewall settings, kernel policy, users, unrelated processes or registry.

## Real Windows 11 execution, exact private source

On the authorized Windows 11 PC, the review-qualified private D2 source commit was **`1cbcc873701bed48ad85700ac344805e9ff81467`**. Local Rust 1.97.1 offline compiled D2 exe SHA-256 `BA770CB387040A8D4FC92DA3F1AA22B524EEC317932C4631DA596547CD9F18B9`. Source pinned Core to exact `8e5ed5430f4ab2ebc8981c52c67234023382954b`; Python 3.14.7 exe SHA `4942B86A6597E5AEE0128DAA00050ED79BC21F6E709A78EB19CBFEB0C2F39AC9`, installed system cryptography `50.0.1` and cffi `2.1.1` (these native package DLLs are **NOT independently audited or cryptographically attested** by this QA).

Real host command `scripts/qualify_windows_job_subtree.py` returned EXIT 0 and verified the parent/child actual OS lifetime. The new real `qualify_windows_encrypted_readback_native_gui.py` with Job supervisor ran exactly the fictional encrypted Core import, closed/reopened it, verified anchored audit, read back three originally encrypted FHIR resources in RAM, emitted only the canonical 1,164-byte invented resource/relationship projection, then launched the actual D2 GUI and verified recovered source digest, links and navigation with Windows UIAutomation (Observation→Patient→Back and Observation→Encounter→Back; clear). Entire end-to-end process exited **0**:

```text
WINDOWS_REAL_CORE_CREATED_SUSPENDED_ASSIGNED_JOB_BEFORE_EXECUTION
WINDOWS_REAL_CORE_JOB_WORKER_EXIT_ZERO_AND_OUTPUT_BOUNDED
WINDOWS_REAL_ENCRYPTED_CORE_THREE_RESOURCE_READBACK_SOURCE_VERIFIED
WINDOWS_REAL_ENCRYPTED_CORE_READBACK_THREE_RESOURCES_LINK_AND_BACK_UIA_PASS_NOT_CLINICAL
WINDOWS_LIVE_ENCRYPTED_CORE_READBACK_TO_NATIVE_D2_GUI_PASS_NOT_CLINICAL
WINDOWS_LIVE_ENCRYPTED_CORE_JOB_TO_D2_NATIVE_UIA_EXIT=0
```

Mac source tests `test_encrypted_readback_projection_source.py` 5/5 PASS and legacy independent `test_windows_job_subtree.py` 4/4 PASS. D2's own Rust source guard remains unchanged: native D2 **does not spawn Python or use a network API**. No real patient data was loaded or retained. Hosted Windows/Ubuntu CI tests are static Python source/Rust tests, NOT replacement for the separately recorded actual Windows GUI/Job execution.

## Important limits and NO-GO gates

- A Job Object guarantees lifetime/descendant cleanup **only when correctly assigned**, as this developer test proved. **It does not block network, DNS, UDP/TCP, filesystem access, EHR endpoints or memory disclosure.** Windows OS-enforced restricted worker identity and egress confinement are still NOT verified.
- The real Core import on Windows uses a pinned clean **source checkout**, not a byte-attested **installed Wheel**. Mac #931 independently attests pure-Python Wheels and installed source but its locally cached crypto versions do NOT satisfy the production package dependency. Do not combine their evidence to assert a cross-OS production chain.
- D2's one-shot stdin accepts only replayable source-compiled synthetic bytes, **not** a fresh authenticated Core session. No client session ID/HMAC/signature, production root key provider, clinical RBAC, consent, local encrypted persistent patient store, full FHIR R4 profile/terminology conformance or independent security/clinical/VoiceOver review has been approved.
- Main remains protected. No signing, notarization, production distribution, real PHI, user EHR import or public release. Existing release gates #574 #603 #662 #673 #676 and 66 default-branch Dependabot notices remain. External security/medical reviewers and formal release authority still required.

**Verdict: actual synthetic Core worker lifetime and real D2 readback GUI qualified on Windows; full MedOrigin product still NO-GO for clinical use.**
