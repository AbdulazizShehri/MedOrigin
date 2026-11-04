# Windows live source-pinned Core encrypted Workspace → real native D2 GUI

2026-11-04 · **private synthetic-only functional qualification** · not clinical product or release.

## What now works on real Windows

On the authorized Windows 11 PC the existing D2 native exe at exact functional commit `09ca2b42cee49f1eb8a16c6312f193028eb9aed2` (SHA256 `a40eba852412f04e958808cd1143e9a96944b0535073353afde412a06a75121f`) has been exercised with a **fresh live encrypted Core+Workspace demo output**, not just the prior static source JSON.

The independent `scripts/qualify_windows_core_workspace_to_native_gui.py` QA harness verifies a *clean* Git source checkout pinned to Core `0351b667ec910480fd61c30f18cf3bb0dd0ae842` with 255 tracked Core files and 33 Workspace source files, checks its Python file inventory for untracked startup shims/symlinks/native loader modules **AND Git-ignored `__pycache__`, `.pyc`, `.pyo`, `.pth`, `.pyd`, `.dll`, `.so`, `.dylib`**, pins the actual CPython 3.14.7 interpreter EXE SHA256 `4942b86a6597e5aee0128daa00050ed79bc21f6e709a78eb19cbfeb0c2f39ac9`, and pins the D2 EXE SHA before/after. Uses `python -I -S -B -c`, explicit Git source-only import roots, system-installed cryptography 50.0.1 and cffi 2.1.1, fixed `workspace-demo --synthetic-only --ephemeral-demo` flags, disposable private temporary folders and a bounded 25-second subprocess. Never accepts a patient input, FHIR file path, arbitrary Python code, model, URL or encryption key.

**This Windows proof runs the source checkout, not two installed and byte-attested Wheels**. In contrast, the Mac proof in parent #924 ran two installed Core/Workspace Wheels and real macOS Seatbelt restrictions. The Windows site's third-party native cryptography DLL chain has not been separately attested; network/DNS/TCP/UDP and descendants are **not** OS-confined by this QA harness. No release trust follows from these results.

After the real encrypted fictional demo returns success, the QA code admits **only the source-compiled, fixed 391-byte aggregate JSON** with SHA256 `25acdb57db8ca3f11d353cf311167973760caaa95bb64de7339fe21e3b05cc2e`: 3 fictional FHIR resources, 3 provenance records, 1 audit event, successful encrypted reopen and temporary-store removal, and explicit `clinical_use_authorized=false`, `production_key_provider_used=false`, `full_fhir_r4_conformance_established=false` and `publication_authorized=false`. Core's platform-specific print suffix may be exactly ONE LF or ONE CRLF; all other bytes remain strictly equal to the canonical embedded report. A malformed, duplicate, modified, extra-content or forged receipt cannot be accepted.

The source-controlled Windows PowerShell UIAutomation QA accepts an **optional exact-hash-verified 391-byte source file** within this disposable harness, then feeds its bytes to the actual D2 `--synthetic-workspace-receipt-stdin` option (still time-bounded, **does not launch Python itself**). Actual PID-specific Windows UIAutomation confirms SHA, counts, encrypted reopen/deletion, nonclinical and untrusted-source disclosures. It separately forges `clinical_use_authorized=true` and requires that D2 exit nonzero before accepting it. The temporary file and its entire private directory are removed by the harness at test completion. The original fixed-fixture Windows UIA behavior remains available unchanged when no optional live path is supplied.

## Observed exact Windows evidence

First run of the new QA harness rejected a byte-exact match because Windows Python print adds CRLF while Mac Python prints LF. A reviewed strict one-terminal-newline normalizer fixed the *QA transport* only; the D2 source hash and canonical JSON admission remained unchanged. New adversarial tests verify neither trailing whitespace nor extra newlines become approved. No error was waived.

Final source-bound Windows 11 run used exact Git source files checked against private GitHub blob SHAs, passed **6/6 Python source/negative tests**, and exited 0:

```
WINDOWS_SOURCE_FIXED_CORE_WORKSPACE_GIT_INVENTORY_ATTESTED
WINDOWS_SOURCE_CORE_AES_GCM_FICTIONAL_REOPEN_CLEANUP_VERIFIED
WINDOWS_LIVE_SYNTHETIC_CORE_GUI_UIA_COUNTS_SHA_AND_FORGERY_PASS
WINDOWS_SOURCE_FIXED_CORE_WORKSPACE_GIT_INVENTORY_ATTESTED
WINDOWS_LIVE_CORE_ENCRYPTED_WORKSPACE_TO_REAL_D2_NATIVE_GUI_PASS_NOT_CLINICAL
```

The independent previous on-device Windows GUI acceptance (parent #924) also passed **the original 4/4 native UIA fixtures**, static encrypted Workspace source view, and forged medical approval refusal. The new full source-driven Core demo is a separate, stricter proof.

## Repro and limits

Use the existing authorized Windows 11 test desktop with an isolated clean Git worktree at exact Core SHA, Python EXE and native D2 EXE with these pinned hashes, then run this source-controlled file:

```powershell
python scripts/qualify_windows_core_workspace_to_native_gui.py `
  --core-source <PRIVATE-EXACT-GIT-CORE-WORKTREE> `
  --python <PINNED-PYTHON-3.14-EXECUTABLE> `
  --python-sha256 4942b86a6597e5aee0128daa00050ed79bc21f6e709a78eb19cbfeb0c2f39ac9 `
  --site <LOCAL-PYTHON-3.14-SITE-PACKAGES> `
  --native-gui <EXACT-LOCALLY-BUILT-D2-EXE> `
  --native-sha256 a40eba852412f04e958808cd1143e9a96944b0535073353afde412a06a75121f
```

All angle-placeholder paths above are documentation-only, not valid literal test arguments.

This is **not** a production Python Core launcher. The native GUI has no authenticated/fresh worker transport, secure persisted patient store, production hardware/OS keystore, real RBAC/consent, FHIR R4 full profile/terminology validation, independently proven three-OS network egress restriction or independent medical/security approval. Preserve the protected-main/clinical NO-GO, issues #574/#603/#662/#673/#676 and unresolved default-branch Dependabot warnings. Do not merge, sign, notarize, publish or process real patient data on this evidence.
