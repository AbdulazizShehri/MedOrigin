# FHIR Windows native pinned report store — security evidence (2026-10-31)

**NONPUBLISHING / SYNTHETIC-ONLY / OPEN DRAFT #782.** This source-only change is stacked on [#781](https://github.com/AbdulazizShehri/MedOrigin/pull/781), immutable parent `c35838ad2bc5dac2cf8dca76af6592e47aa0b2c0`. It does not merge to protected `main`, modify canonical frozen `pyproject.toml`, `uv.lock`, research/MRL, version/installer/publisher or clinical data contracts, or authorize a release. There is no PHI, EHR write, model training or cloud upload.

## Genuine Windows test-first RED

Earlier #781 had addressed Windows FHIR **report loading** using native `NtCreateFile` and `OBJ_DONT_REPARSE`. The Windows `store_report` path remained vulnerable to post-preflight directory mutation because it still used `Path.mkdir(parents=True)`, `NamedTemporaryFile(dir=...)`, path-based `os.link()`, and path-based cleanup.

At the **test-only** commit `01c422be82d155e1efd706bcc65a75e24d701dd6`, the hosted Windows 2025 read-only CI [#41223467029](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41223467029) failed the three new real-NTFS `cmd /d /c mklink /J` adversarial regressions, including one where the old implementation created a new `fhirkit/` directory inside the attacker-controlled synthetic decoy **after its lexical root preflight**. Both Windows Python 3.11 and 3.12 reported failure; Ubuntu/macOS baseline tests succeeded. This is a real **unexpected local filesystem write** in synthetic tests, not patient data disclosure.

## Native Windows implementation

New `src/medscale/fhirkit/_windows_native_store.py` replaces all Windows FHIR report creation, temp file writes, no-clobber hard-link publication and temp cleanup. It uses documented NT handle-relative APIs rather than following the generated public pathname during each mutation:
- `NtCreateFile` opens the Windows drive anchor, then *one directory component at a time* using the previous directory HANDLE as `OBJECT_ATTRIBUTES.RootDirectory`, `OBJ_DONT_REPARSE`, `FILE_OPEN_REPARSE_POINT`, `FILE_DIRECTORY_FILE`, and attribute checks refusing any reparse directory. Missing subdirectories are created relative to the pinned parent HANDLE, not via a fresh lexical path traversal.
- The final digest directory HANDLE stays open through the whole transaction; it is reopened root-first at pre-publication and post-publication checkpoints and compared with the held object's volume serial + file index. Missing, different or reparse-alias paths fail closed.
- The temporary file name is random, exclusively created via `NtCreateFile(FILE_CREATE)` relative to that exact directory HANDLE, flushed with `os.fsync` using the original file HANDLE as owned Python FD.
- `NtSetInformationFile(FileLinkInformation)` publishes the same open temporary file as `report.json` **relative to the pinned directory HANDLE** with `ReplaceIfExists=FALSE`. On an existing file, re-open only `report.json` relative to the same HANDLE, read under the existing 8 MiB regular-file bound, and refuse noncanonical bytes. No symlink fallback and no overwriting an existing report.
- Temporary file disposal uses native `SetFileInformationByHandle(FileDispositionInfo)` on that still-open temporary HANDLE; cleanup never follows a potentially swapped pathname.
- All native errors fail closed without a legacy path-based write fallback. POSIX continues with its existing `O_NOFOLLOW` dirfd implementation. The failure-injection tests now hook the actual native link boundary only on Windows; POSIX still hooks `os.link`.

## Qualification ledger

- **Pre-fix real Windows RED:** [#41223467029](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41223467029), includes observed untrusted synthetic decoy directory creation.
- **Functionally GREEN at earlier source HEAD `69f1e8813c2080c04044b733595ad9083f56af18`:** [hosted PR CI #41224378816](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41224378816), **6/6 Windows2025/Ubuntu24.04/macOS15 × Python3.11/3.12** successful, including the three real NTFS negative tests, atomic collision/failure/idempotence, load, CLI and formatting.
- **Additional adversarial last-window test:** after the temporary file is open but before `NtSetInformationFile`, the test attempts an actual directory rename and junction insertion. Hosted Windows proved a genuine `PermissionError (WinError 5)` from rename while the descendant file HANDLE is held. The corrected test explicitly allows only (a) Windows OS blocking the attempted rename and normal publication in the original directory, or (b) successful substitution followed by fail-closed application refusal. The test **never accepts writes under the decoy**, and always checks temporary cleanup. Do not describe an OS-denied rename as successful test relocation.
- **Final exact-head evidence:** only record complete 6/6 after the last test and this document have passed on the current SHA; earlier CI is not final-head qualification.

## Explicit boundaries and remaining NO-GO

This is **one-machine-family native Win32/NTFS technical evidence** on hosted Windows Server 2025, not a proof that all Windows filesystem filters, network shares, non-NTFS volumes or older Windows builds provide identical semantics. No cross-process hardened ACL policy, protection from a pre-existing privileged writer changing file contents, atomic root-to-leaf transaction, post-return storage custody or clinical suitability is claimed. Directory identity is sampled at bounded checkpoints; an adversarial swap-back entirely between checks is not formally ruled out, though all writes and cleanup use pinned handles. If an untrusted actor controls the parent directory with conflicting privileges, place the store in a trusted user-owned location or fail closed. See Microsoft's `NtCreateFile` RootDirectory and `FILE_LINK_INFORMATION` documentation.

**Release remains NO-GO:** independent source/security review #603, frozen optional research dependency advisories #622, version/ADR/owner approval #574, actual WebView2 runtime network isolation #662, Linux AccessKit maintenance #673, macOS VoiceOver #676. No main merge, tag, installer, package upload, PHI, EHR write or release until separate approval.
