# MedOrigin Core — Wheel member inventory fail-closed security (2026-11-03)

**Scope:** private, nonpublishing Core packaging validation. This Draft branch stacks on exact Core integration PR #873 HEAD `9a3a802ee1e4f4574817e5a124183efb6b5ad9b0`. It does not touch the desktop/UI, frozen research root, `uv.lock`, MRL manifests, licenses, build/publish workflows, clinical data, or actual publication.

## Confirmed false admissions before correction

On an authorized real Windows 11 PC, tested the original immutable `9a3a802` production script using synthetic Wheel/sdist pairs. The original `check_base_core_publication_scope.py` checked local header identity and METADATA but did not refuse unsafe *other* ZIP members.

Independent paired before/after execution used the exact original script bytes via `git show 9a3a802:scripts/check_base_core_publication_scope.py` and the corrected checked-out script. Results:

| Member condition | Original guard | Corrected guard |
|---|---|---|
| Normal member `medscale/safe.py` | CLEAN | CLEAN |
| Unix symlink ZIP entry `medscale/unread-link.py` | CLEAN | BLOCKED — unsupported member type |
| `medscale/../escape.py` | CLEAN | BLOCKED — unsafe member path |
| `/medscale/escape.py` | CLEAN | BLOCKED — unsafe member path |
| `C:/medscale/escape.py` | CLEAN | BLOCKED — unsafe member path |
| `medscale//escape.py` | CLEAN | BLOCKED — unsafe member path |
| Duplicate ZIP filenames `medscale/repeat.py` | CLEAN | BLOCKED — duplicate member path |
| Windows case-folding collision `Same.py` versus `same.py` | CLEAN | BLOCKED — duplicate member path |
| Literal backslash filename stored in ZIP | BLOCKED — pre-existing local-header mismatch | BLOCKED — same pre-existing protection |

The backslash case is **not** reported as a newly discovered bypass: Python's `zipfile` canonicalizes separators on Windows when creating ordinary `ZipInfo` objects. A second test explicitly forced the raw stored name to contain `\\`; the pre-existing #869 local-header identity check rejected it on Windows. The new inventory validator independently rejects it on platforms that expose it unchanged.

All inputs were synthetic and local. No untrusted code, package, link, model, EHR or clinical data was executed, installed or transmitted.

## Narrow source fix

- New `_verify_wheel_member_inventory` in `scripts/check_base_core_publication_scope.py` inspects **all central directory members** before reading METADATA. It rejects empty, relative `.`/`..`, empty-component, absolute, backslash, drive-colon, trailing space/dot paths, case-folded duplicate aliases (including file/directory alias collisions) and Unix special files or inconsistent regular/directory mode types. It retains the existing ZIP physical envelope/filename/CRC/flags checks and all size/member/metadata bounds. No new dependency.
- Eight parametrized source-controlled `pytest` cases in `tests/test_base_core_publication_scope.py` demand `BLOCKED` and `publication_authorized=false` for the unsafe cases, while asserting the untouched `dist-info/METADATA` is still readable and unchanged. Existing positive and negative tests are unchanged.
- Separate `check_core_wheel_source_identity.py` remains active and unchanged; this hardens the independent **base-publication** guard so it cannot silently trust a source-identity check not necessarily invoked by another caller.

## Windows exact-source QA

- Dedicated task-owned sparse Git clone: `D:\\MedOrigin-Core-MemberSafety-QA-20261103`, fetched exact corrected functional commit `9ef81e680abc8eefef714f35303fc98d910846a2`.
- Git blob IDs of source-controlled production gate and test: `80b25cef3f2299e6c161abeeec98ff352a1fcbd8`, `5f3a9b92c33cf3e710ba5b0375dc90c8026ba807`.
- **Python 3.14** full `tests/test_base_core_publication_scope.py`: **56/56 PASS** in 4.93s, exit 0.
- **Python 3.11.15**: **56/56 PASS** in 4.79s, exit 0.
- **Python 3.12.13**: **56/56 PASS** in 4.40s, exit 0.
- Ruff 0.16.9 `check` and `format --check`: PASS on both edited Python files.
- `git diff --check 9a3a802... HEAD`: PASS. No tracked changes in the test worktree.
- A first partial sparse test run produced 54 PASS, 2 FAIL: one due to an omitted unchanged CI file needed by an existing regression test, and one due to the Windows ZipInfo filename-normalization artifact described above. The missing unchanged workflow was included in the sparse checkout and the test fixture corrected to force real raw ZIP backslash bytes; the subsequent exact-HEAD three-interpreter runs all passed 56/56. No production failure or release approval was inferred from the initial setup errors.
- Python 3.11/3.12 reused existing Python3.14 `pytest 8.4.2` pure-Python site-packages via temporary process-local `PYTHONPATH`, with third-party plugin auto-loading disabled. These are actual independent Python interpreter executions, **not** hermetic separately installed pytest environments. The focused module was run using `--noconftest`, not the entire project test suite.

## Release and safety status

**Release NO-GO**. Full current-source hosted 20-job CI, independently attributable source/artifact security review #603, optional research/extras advisory #622, approved ADR-0045 and package/version decision #574, explicit owner publication authority and separate desktop #662/#673/#676 remain unresolved. No public tag, release, installer, signing, registry upload, protected-main merge, network build or PHI/clinical use. Every inspected artifact continues to return `publication_authorized=false` even when its internal synthetic-only scope is otherwise clean.
