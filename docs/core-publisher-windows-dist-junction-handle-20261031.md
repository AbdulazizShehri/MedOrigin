# Windows NTFS dist junction swap — canonical Core scope gate (31 October 2026)

**Status: UNPUBLISHED, NONCLINICAL, DRAFT-ONLY.** This change extends [Draft PR #773](https://github.com/AbdulazizShehri/MedOrigin/pull/773) at exact immutable parent `8875f0a18478fc4dbe699c91a6a1ac87dab3b80b`. All package metadata, frozen `pyproject.toml`, `uv.lock`, MRL research receipts, actual publisher workflow, release/version, installed product, protected `main`, tags and registries remain untouched. `publication_authorized=false`.

## Threat and reproduced RED

The Windows publisher-scope gate previously rejected directory junctions/reparse ancestors **before** enumerating `dist/*`, then opened each Wheel/sdist using a native final-file `CreateFileW` HANDLE. Without a pinned directory HANDLE, a caller could rename the originally inspected `dist` aside and insert an **unprivileged genuine NTFS junction** at the same path immediately before the later file opens. Original `dist` includes a Wheel or sdist advertising disallowed `Provides-Extra: unreviewed-training`; the junction instead resolves into a separate clean synthetic pair. A clean result after such a swap would be a metadata-scope admission error, **not** a demonstrated bypass of immutable-Git source-attestation or any actual publication.

At test-only source HEAD `ae42735baa0ee368e5a748f12f7d5c23332cc1f4`, [hosted nonpublishing Windows CI #41216495109](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41216495109) intentionally **FAILED** on Windows2025 Python 3.11 and 3.12 for both `wheel` and `sdist` cases: `BASE_CORE_PUBLICATION_SCOPE_CLEAN` was returned where `BLOCKED` was required. Both tests validated `FILE_ATTRIBUTE_REPARSE_POINT` on the actual NTFS junction (created by `cmd /d /c mklink /J`), so this did not merely test a mocked path or symlink requiring privilege. The test-only run also exposed an ordinary Ruff formatting issue; Ubuntu's pre-existing tests remained functionally passing.

## Bounded Windows directory HANDLE fix

The gate now opens the lexical `dist` directory via native `CreateFileW`, requesting `FILE_READ_ATTRIBUTES`, `FILE_SHARE_READ` (**no DELETE sharing**), `OPEN_EXISTING`, and `FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT`. A trusted Win32 `GetFileInformationByHandle` query checks the **opened object**, requiring the directory attribute and refusing `FILE_ATTRIBUTE_REPARSE_POINT`. It also rechecks all lexical ancestors with the existing fail-closed static alias logic while the native directory HANDLE remains open, then re-enumerates exactly the same two ordinary artifact filenames before the previously qualified final-file HANDLE snapshots. The directory HANDLE is closed with `CloseHandle` in a `finally` block; the final-file bounded copies and separate archive metadata ZIP/TAR checks remain unchanged.

A new native Windows test additionally attempts to rename `dist` during `_inspect_scope_metadata`, within the real opened directory HANDLE scope, and expects `PermissionError`. This checks a **real OS sharing behavior** without disabling system-wide security or requiring privileges. All testing uses synthetic bytes, independent temporary directories and hosted free runners.

## Explicit limits

This is not **root-to-leaf Windows ancestry HANDLE pinning**, nor atomic acquisition of both Wheel/sdist, protection against pre-existing privileged writers, a stable publisher artifact handoff, or independent supply-chain security review. An upstream parent component that changes between the initial path use and this directory HANDLE open is bounded by the second lexical alias check and late junction refusal in the tested case, but other path races are not generally proven impossible. A later independent `dist/*` publisher could still reopen different files after this checker returns. The `BASE_CORE_PUBLICATION_SCOPE_CLEAN` result is a **read-only scope assessment** and always preserves `publication_authorized=false`.

## Evidence

- **Real Windows RED:** [#41216495109](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41216495109), Windows3.11/3.12 both parameterized genuine NTFS junction tests failed `CLEAN != BLOCKED` before the fix.
- **Functional GREEN at intermediate fix:** [#41216613174](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41216613174), Windows Python3.12 reported **52 passed, 2 skipped** including the two junction negatives, but this intermediate CI **failed the newly added lint check** for two `ctypes.Structure` field definitions. Do not mislabel it overall green.
- **Final exact-head status:** only claim success after current final SHA's Windows2025/Ubuntu24.04 × Python3.11/3.12 scope+Ruff CI and Windows/macOS/Linux installed Core parity both finish successfully. A true final SHA and links should be recorded in PR discussion.

**Remaining NO-GO:** owner/version/ADR #574, Pillow/Accelerate frozen research extra advisories #622, independent QA/security #603, Windows Tauri WebView2 actual descendant network isolation #662, Linux dependency maintenance #673, macOS spoken accessibility #676. No real patient/PHI data, scientific efficacy claims, production EHR writes, external model inference, package publication, release, installer, tag or protected-main merge. All durable work stored on GitHub; no new user-PC scratch.
