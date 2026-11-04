# Native MedOrigin D2 fictional first-run persistent Workspace workflow

**2026-11-04 — PRIVATE, stacked on #946, no patients or clinical use.**

## Product-facing change

A developer previously needed two independent entrypoints: first explicitly run the Windows fictional persistent encrypted Workspace creator, then run the portable native GUI launcher with an existing QA path. The Windows portable Desktop now offers one **explicit, repeatable first-run opt-in**. It automatically creates the fixed test-only AES-256-GCM SQLite Workspace **only if it is absent**, using the exact already reviewed three fictional Core FHIR-shaped resources and one SHA-verified external audit anchor protected by current-user Windows DPAPI. It then runs a **second independent, installed-source, suspended-before-first-instruction Windows Job Object Core worker** to re-open and decrypt the same persistent Workspace, and displays a byte-exact reviewed 1215-byte redacted projection inside the real native Rust Desktop through a fresh per-launch integrity-framed HMAC session. On subsequent launches it only re-opens the existing vault, never regenerates a test root key or replaces/deletes it.

The feature does not alter the pre-existing default ephemeral mode or normal unflagged native GUI. It introduces no Rust crates, network API, process access within the native GUI, cloud services or actual user/patient input. No user-modifiable generic FHIR records, clinical workflow, or production key-provider resolution are enabled.

## Repeated GUI launch (opt-in, private QA only)

Prepare the exact reviewed Windows portable kit with the historical SHA-pinned two offline Wheels and 290 exact Git/Wheel/installed pure Python source files. Then use the same launcher command each time:

```powershell
python -B <PRIVATE_PORTABLE_KIT>\scripts\launch_windows_portable_fictional_core.py `
  --python <REVIEWED_LOCAL_WINDOWS_PYTHON_EXE> `
  --crypto-site <EXACT_LOCAL_PYTHON_CRYPTOGRAPHY_SITE_PACKAGES> `
  --python-sha <REVIEWED_LOCAL_PYTHON_SHA256> `
  --fictional-persistent-qa-root <EXISTING_PRIVATE_PARENT>\medorigin-d2-fixed-fictional-persistent-vault-qa `
  --ensure-fictional-demo
```

Explicit `--ensure-fictional-demo` requires the literal **fixed-name fictional QA vault path**; the parent must already exist. An absent vault is created exactly once, a present vault is opened and checked. The existing `--qa-uia` or `--qa-auto-close` options perform automated native-Windows visual navigation checks without a human-driven window. Without `--fictional-persistent-qa-root`, the default 1164-byte ephemeral encrypted readback still runs, and `--ensure-fictional-demo` is rejected when the path is omitted. Without `--ensure-fictional-demo`, passing a nonexistent vault remains an error; historical explicit-open behavior is preserved. The existing vault is **never repaired by silently recreating it**; damaged DPAPI key, external audit anchor, SQLite store, wrong path, symlink or unexpected source returns the generic fail-closed code. In case a first-run initialization fails after creating a partial test directory, the launcher intentionally **does not delete or overwrite** it. Diagnose and clean only that explicitly owned test path independently.

Every first-run creation uses the same Win32 `CreateProcessW(CREATE_SUSPENDED | CREATE_NO_WINDOW)`, `AssignProcessToJobObject`, `IsProcessInJob`, `ResumeThread` order as the existing exact-pinned source worker. No supervised Python instructions execute before successful job assignment. The first worker returns a single fixed bytes marker after authentic creation and is terminated/closed; a **separate second worker** must perform a successful cold reopen, audit and source SHA verification and report exact canonical bytes before the native GUI opens. GUI cryptographic owner-bound HMAC is not a production sender authentication, and a Job Object controls lifetime **not network egress**.

## Actual Windows 11 and Ubuntu evidence

- Built the historical Core+Workspace Wheels offline, exact hashes `9aad845ecec6b09e27b38a29a2fb521b3958218aef5ae4b0415abb88ee5fc24b` and `86488f14f113ec2e56f0c5185b91fbd61e546dc73f06587730b6794436e8d465`; all **290 pure-Python files Git↔Wheels↔installed site verified**. Created a private portable kit from the latest native Rust D2 build; no compiled artifacts, production data or DPAPI secrets enter Git.
- **First real Windows portable launch** with `--ensure-fictional-demo --qa-uia` created the owner-only fictional DPAPI vault in a previously empty test parent. Process markers: `WINDOWS_REAL_CORE_CREATED_SUSPENDED_ASSIGNED_JOB_BEFORE_EXECUTION` twice (separate initialization and independent cold reopen), `WINDOWS_PRIVATE_FICTIONAL_FIRST_RUN_VAULT_CREATED_NOT_CLINICAL`, `WINDOWS_PORTABLE_FICTIONAL_CORE_TO_NATIVE_D2_GRAPH_UIA_PASS_NONCLINICAL`. Returned EXIT 0.
- **Second independent real Windows portable launch** with the **same command and exact existing path**: executed only the Core cold reopen and GUI (no creation marker). Verified byte-identical DPAPI key/anchor protected file SHA256 before/after. Actual native Windows UIAutomation traversed type search, source-defined Observation/Patient/Encounter link graph, breadcrumb history and Clear. Returned EXIT 0: `WINDOWS_SECOND_INDEPENDENT_LAUNCH_SAME_DPAPI_KEY_AND_AUDIT_ANCHOR_UNCHANGED_NATIVE_UIA_PASS`.
- **Corruption negative:** flipped a byte of the existing DPAPI audit-anchor file in a task-owned QA vault, ran the **same `--ensure-fictional-demo` command**. It returned EXIT 2 `WINDOWS_PORTABLE_FICTIONAL_CORE_NATIVE_D2_NO_GO`, not GUI success or reinitialization, and the original anchor was byte-restored in a `finally` block. `WINDOWS_EXISTING_CORRUPT_DPAPI_AUDIT_REFUSED_NO_SILENT_RECREATE_EXIT2`.
- Source-only `test_windows_fictional_demo_first_run.py` verifies creation happens once, independent cold reopen, second run uses only reopen, missing required path fails before worker, precise installed-Core source runner and Win32 suspended/job-assignment ordering. Python source-only tests passed on **Windows and Linux/WSL**.
- Prior default ephemeral Core -> actual native UIAutomation regression was re-executed unchanged. Hosted CI must be checked independently after pushing the exact PR head; do not claim hosted success until it is observed.

## Mandatory unresolved release gates

This is an **explicitly nonclinical fixed fictional demonstration**, not first-run onboarding for real patient workspaces. It still uses Core's production-unselectable `InMemoryTestKeyProvider` reconstructed from current-user Windows DPAPI for tests. It is not an audited production protected key provider or RBAC/consent, independent rollback-resistance, OS network egress confinement, full FHIR R4 profile/terminology validation, clinical audit, dependency remediation, multitenancy, signed installer, or macOS/Linux parity. Current Windows Python/cryptography/cffi native runtime remains an external unverified supply-chain dependency. Do not process real patient information, merge protected main, publish, sign, notarize, ship, or claim clinical readiness. The fixed test root may be discarded only by its authorized owner; program intentionally never auto-recovers or deletes a possibly damaged existing vault.
