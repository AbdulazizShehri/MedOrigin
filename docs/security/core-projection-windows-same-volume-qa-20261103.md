# MedOrigin Core — same-volume atomic package projection on Windows (2026-11-03)

**PRIVATE / DRAFT / NONPUBLISHING / NO CLINICAL DATA.** This is a Core packaging/portability fix only; no changes to UI, native desktop, Windows firewall, research root, model training, frozen `pyproject.toml`, `uv.lock`, or PHI.

## Exact parent and first-hand red phase

- Stacked on Core package-security Draft PR #869, exact immutable parent `9069af014f627952639969a40e9299960463a758`.
- The Core staging function `scripts/stage_medorigin_core_projection.py::stage` created its private work under the operating system's default `tempfile.TemporaryDirectory()` (C: on the authorized PC) but used `work.rename(target)` to install a package directory under the user-supplied output (D: in the isolated task).
- In a real Windows Python 3.11 `pytest` execution against exact original source `7f817a5450d8cf6fe7cbdfde7be22323838f200f`, the independent source-distribution integrity test `test_rehashed_source_receipt_cannot_hide_missing_git_module` failed its **first normal staging prerequisite** before reaching its adversarial assertion. Actual error:
  
  ```text
  PROJECTION_BLOCKED: [WinError 17] The system cannot move the file to a different disk drive:
  'C:\Users\Shehr\AppData\Local\Temp\medorigin-projection-...\package'
  -> 'D:\MedOrigin-Core-HeaderQA-PyMatrix-20261103\.pytest-adj-3-11\...\staged'
  ```
  
  This is a concrete Windows cross-volume packaging bug, not a fake-metadata or Python-3.11 syntax problem. A source-bound sparse QA run before fixing it yielded 47 earlier tests passing, with this deterministic blocker at test 48. No host TEMP/folder permissions or global system settings were modified.

## Source fix (only two source paths)

- `scripts/stage_medorigin_core_projection.py`: after all existing immutable Git source/frozen lock checks, create the **destination parent** first, then invoke `tempfile.TemporaryDirectory(prefix="medorigin-projection-", dir=target.parent)`. Build all limited source files and `MEDORIGIN_SOURCE_PROVENANCE.json` in that private sibling scratch directory, then keep the existing `target.exists()` fail-closed check and `work.rename(target)` final move. The scratch and destination now share their parent directory and filesystem; Windows `rename` no longer attempts an illegal C: → D: move. Private scratch automatically cleans on successful staging and on exceptions.
- `tests/test_core_release_projection_identity.py`: new runtime regression `test_projection_stages_on_destination_volume_and_cleans_private_scratch` captures the actual `TemporaryDirectory(dir=...)` argument, asserts it resolves to the requested output's parent even when the parent did not previously exist, checks private scratch removal, verifies the output package and provenance, and confirms `publication_authorized=false`. Original tests verifying source-to-Git byte identity and refusal to overwrite an existing output remain unchanged.
- A Ruff-only format correction made the `TemporaryDirectory` invocation a single correctly formatted line, without changing the algorithm.
- Final exact executable/source branch commit **`d278c66b0b69502972da39233d2a10c0ca582a7a`**, production Git blob `46644bde156df0d09d50f6e88176bab0be4a8bf8`, new regression test blob `58a53005714644c72c0fb7c386f70dc0e3a3092a`. Exact compare to parent: **2 paths only**, no research/desktop/CI mutations.

## Actually executed on authorized Windows

Using an isolated task-owned D: sparse Git worktree `D:\MedOrigin-Core-HeaderQA-PyMatrix-20261103`, with original Git source frozen and `pytest 8.4.2` already present as Python 3.14 pure-Python tooling (temporary `PYTHONPATH` and plugin-autoload-disabled as documented in the #869 QA record; **not** a fresh isolated pytest installation):

1. **Initial functional fix HEAD `83864be657a01c9386b7e677f73780dfbf7d116f`**:
   - Python **3.11.15**: complete `tests/test_core_release_projection_identity.py` **3/3 PASS**, exit 0, **32.33s**.
   - Python **3.12.13**: same complete module **3/3 PASS**, exit 0, **29.70s**.
2. **Final Ruff-formatted exact HEAD `d278c66b0b69502972da39233d2a10c0ca582a7a`** (source SHA was checked out and printed before running):
   - Python **3.11.15**: new same-volume scratch regression **PASS** AND originally failing `tests/test_sdist_publication_scope.py::test_rehashed_source_receipt_cannot_hide_missing_git_module` **PASS** (2/2, 9.01s, exit 0).
   - Python **3.12.13**: same two exact-HEAD regressions **PASS** (2/2, 9.90s, exit 0).
   - Ruff **0.16.9**: `ruff check` PASS and `ruff format --check` PASS for both changed Python files.
3. The original #869 Wheel local/central ZIP-header tests remain source-identical; they were independently qualified earlier on Windows at **42/42 on Python 3.11, 42/42 on Python 3.12, 42/42 on Python 3.14** (original production code HEAD `7f817a54`, unaffected by this branch).

**Limit:** the full `test_sdist_publication_scope.py` suite was not rerun to completion at the new HEAD; its known blocking test was executed and passed on both target Python versions. No hosted CI run of this stacked PR yet.

## Remaining risk, release blockers, and next acceptance

- No change to the existing destination race policy, final output's security context, source-of-truth hashes, optional dependencies, ADR, or release permissions. Existing `target.exists()` refusal remains. A separate future review may strengthen cross-platform no-replace race semantics, but this patch does not claim to solve that larger threat model.
- ADR-0044 **accepted only isolated read-only staging**; ADR-0045 base-only metadata deletion **not adopted**. Frozen research extras #622, independent attributed #603 security/source/artifact review, owner package/version/signing/release decision #574, and separately owned desktop #662/#673/#676 remain **NO-GO**.
- Before any merge or public release: verify exact-HEAD hosted 3-OS CI including D: Windows staging, independent review, ZIP/source-bound audits, and reproducible Wheel+sdist installation. This author-side local proof is not an independent release approval.
- No protected-main merge, signing, tag, installer, publishing, secret access, EHR/PHI, clinical use, OS security-policy alteration, or paid package download was performed.
