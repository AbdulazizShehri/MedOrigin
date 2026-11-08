# MedOrigin Core Wheel ZIP hardening — exact-source real Windows QA (2026-11-03)

**Private Draft PR:** [#869](https://github.com/AbdulazizShehri/MedOrigin/pull/869), source candidate `9660fee43952e28116b51741a59bfd03216f9b2a`, stacked on Core Developer Beta PR #641 (`6953fba7d557d74ace96c1a61b12f87eafbcc8ab`). No desktop/UI changes, no production data, no release or protected-main merge.

## Native Windows source provenance

- Connected authorized Windows Desktop Commander machine `Abdulaziz`. Created **one isolated, task-owned sparse Git worktree** on drive D: at `D:\MedOrigin-Core-HeaderQA-20261103` from exact `FETCH_HEAD` after `git fetch --no-tags origin security/medorigin-core-wheel-header-integrity-20261103`.
- `git rev-parse HEAD` returned **`9660fee43952e28116b51741a59bfd03216f9b2a`**.
- `git hash-object scripts/check_base_core_publication_scope.py` returned `e231c70df74dbfb4c0299f85a178a4a10927d98b`, exactly matching the private GitHub source blob.
- `git hash-object tests/test_base_core_publication_scope.py` returned `723a689a5c45e5e993259e09f79dbb5e262e293c`, exactly matching the private GitHub source blob.
- The clean sparse checkout was limited to these two source files, `.github/workflows/release.yml`, and `pyproject.toml` (added for repository-configured Ruff). No native UI/desktop files checked out or edited.
- **No staged/unstaged changes** were introduced. Only the pytest task-generated temporary directory was untracked before cleanup.

## Exact real pytest execution

The first attempt with the default Windows C: pytest directory **failed for environment reasons**, not because the tested security assertions failed: the user-level temporary folder `C:\Users\Shehr\AppData\Local\Temp\pytest-of-Shehr` returned `PermissionError [WinError 5]: Access is denied`. The first run reported `2 passed, 40 errors` (fixture initialization errors). No OS permissions or shared temp-directory settings were changed.

Re-ran the **same exact committed Python test file** with a D:-scoped, newly-created, task-owned pytest temp directory:

```powershell
Set-Location D:\MedOrigin-Core-HeaderQA-20261103
py -3.14 -m pytest -q --basetemp D:\MedOrigin-Core-HeaderQA-20261103\.pytest-tmp tests/test_base_core_publication_scope.py
```

**Actual output and process outcome:**

```text
..........................................                               [100%]
42 passed in 2.90s
EXIT_CODE=0
```

- Python **3.14**; `pytest 8.4.2`.
- This includes all three newly authored Wheel-local corruption cases (`local-filename`, `local-crc`, `local-flags`), the corresponding unchanged valid Wheel positive control, and the pre-existing adversarial base Core archive/publication scope tests.
- This is a real **42/42 exact-source Windows suite run**, superseding the prior isolated 8/8 algorithm-only receipt.

## Source compatibility and static gates

Using the existing installed isolated uv Python interpreters, without new dependencies or network downloads:

- Python **3.11.15**: `-m py_compile` of the two exact source-controlled Python files **PASS**.
- Python **3.12.13**: same two-file `-m py_compile` **PASS**.
- Ruff **0.16.9**, with the committed repository `pyproject.toml` made available in the sparse checkout:
  - `py -3.14 -m ruff check scripts/check_base_core_publication_scope.py tests/test_base_core_publication_scope.py` — `All checks passed!`
  - `py -3.14 -m ruff format --check scripts/check_base_core_publication_scope.py tests/test_base_core_publication_scope.py` — `2 files already formatted`.

Syntax compilation on 3.11/3.12 is **not equivalent** to executing the full pytest suite on those versions. The previous #641 hosted Core tests are source-bound to an earlier SHA and cannot be transferred to this branch.

## Release and security limitations

- **No hosted exact-branch GitHub Actions workflow runs** are recorded for the new source SHA (commits used `[skip ci]`). No full hosted 20-job CI, artifact install matrix or independent #603 attributable security review of this new source yet.
- The patch closes a concrete Wheel base-only scope gate false admission, not all Wheel supply-chain concerns or complete installer trust. The separate `check_core_wheel_source_identity.py` and other release gates remain in force.
- Unapproved ADR-0045 packaged base-only metadata, unsafe advertised optional extras #622, founder package/version decision #574, independent review #603, and the separately owned desktop #662/#673/#676 continue to block public or clinical distribution.
- No protected-main merge, tag, signed binary, Wheel/sdist publication, installer, clinical use, PHI, EHR writes, dependency installation, Docker/OS policy change, or paid service occurred.

**Decision: author-side Windows regression QUALIFIED 42/42; protected-main/release status remains NO-GO.**
