# MedOrigin Core — secure release build contract and broad non-UI Windows regression QA

**Date:** 2026-11-03 (Asia/Riyadh)
**Status:** Private Draft, unpublished, synthetic only. **Release remains NO-GO.**

## Parent, task scope, regression source

The code-only change is on standalone branch `test/medorigin-core-secure-uv-build-contract-20261103`, stacked on private PR #878, parent functional SHA `00fc3f7ce8d066d690157816415334b29f5ea0bd`. It modifies **only** `tests/test_release_workflow_contract.py`. Production workflows, Python runtime, UI/desktop, frozen research root `pyproject.toml`, `uv.lock`, clinical/MRL receipts, signing, tags and publisher permissions were left unchanged.

Independent source-controlled Windows regression execution against the **unmodified parent** collected 247 tests spanning:

- synthetic FHIR developer-beta source example;
- sdist publication integrity and Core wheel/source identity;
- immutable Core projection;
- both Release Workflow paths, tag governance and tag-main admission;
- wheel metadata inspection and prepublication rehearsal;
- synthetic-only Workspace FHIR adverse-input and no-backflow security boundaries.

Command used Python 3.14.7 with already-installed pytest, temporary task-owned D: `--basetemp`, process-local source/test `PYTHONPATH`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and `--noconftest` (not full 355-file repository CI, not separate hermetic environment). The original exact parent yielded **245 PASSED / 1 SKIPPED / 1 FAILED in 177.74s**, exit 1. The sole failure:

`tests/test_release_workflow_contract.py::test_tag_and_pr_paths_use_identical_audited_core_projection`

The test asserted the **obsolete** literal build command `run: uv build "$RUNNER_TEMP/medorigin-core" --out-dir dist`. Both real release-tag and PR-artifact workflow build steps correctly use **`uv build --no-create-gitignore "$RUNNER_TEMP/medorigin-core" --out-dir dist`**, following the earlier reproduced UV-generated `dist/.gitignore` sidecar rejection by the stricter `dist/*` publishing-inventory gate. Changing the workflow back to satisfy the test would have weakened the production safety contract.

## Minimal, fail-closed source fix

In `tests/test_release_workflow_contract.py`, update the single `required_build` expected string to **include `--no-create-gitignore`** and explain why a hidden sidecar cannot accompany the qualified Wheel/sdist pair. Retain the complete source stage/build/metadata/sdist verifier ordering assertions, exact-once requirements in both tag and PR paths, checks preceding `actions/upload-artifact`, and no release/publisher permission bypass. The change adds no test dependencies, does not touch workflows or production scripts, and does not allow missing/nonadmitted files.

Test code's final functional Git commit **`b4b31b947c26a93d7cedb0344df5141f0d383b40`**, test file Git blob `ba9c4296d7c3d4c37879d5ae4d9a32113017cf30`. Initial test-fix source SHA `96a8e051c8f4baabffa1201abd34e85d7811881f` passed all 11 Release Workflow contract tests, but Ruff correctly identified a 103-character line. The second commit formatted it without semantic changes; all final checks below refer to `b4b31b9` exactly.

## Exact-final-source Windows qualification

Separate authorized task-owned full Git clone at `D:\MedOrigin-Core-BroadQA-20261103-2200`. No modifications to any other agent's worktree.

- Python **3.14.7**: source-controlled 247-case **same broad subset** with `--noconftest`, exact final functional SHA: **246 PASSED / 1 SKIPPED / 0 FAILED**, **159.83 sec**, test process exit **0**. The sole skip is `tests/test_medorigin_prepublication_rehearsal.py:137`: the Windows host does not permit creating symlinks. No bypass or forced symlink privilege was added.
- Python **3.11.15**: complete `tests/test_release_workflow_contract.py`: **11/11 PASS**, exit 0, 0.21 sec.
- Python **3.12.13**: same workflow contract tests: **11/11 PASS**, exit 0, 0.46 sec.
- Python **3.14.7**: same complete workflow contract tests: **11/11 PASS**, exit 0, 0.37 sec (on the intermediate semantic SHA, identical test semantics; the final SHA was also covered by the 247-case broad test).
- Ruff lint and format-check **PASS** on the changed test file; `git diff --check` against parent **PASS**.
- Python 3.11/3.12 reused the existing Python3.14 pure Python `pytest 8.4.2` site-packages via per-process `PYTHONPATH` with plugin auto-loading off. Do not describe these as per-version venvs, full QA or hosted CI.

**Important boundary:** These 247 cases are a *selected* source-bound, non-UI release/trust/FS suite, not the entire repo suite. The full hosted 20-job exact-final-HEAD GitHub Actions/CodeQL run has not been executed and no independent security reviewer has approved these commits.

## Remaining non-negotiable NO-GO

Issue #574 founder owner decision for ADR-0045 package/version and publication authorization, #622 unqualified advertised optional research dependencies and advisories, #603 independently attributable source+artifact/security approval, #877 authentic local FHIR R4 schema/profile/terminology validation, and separately owned native desktop #662/#673/#676. The earlier FHIR fail-closed `not_validated` behavior is still only a developer candidate and is not clinical qualification.

No production package, tag, release, signed installer, PyPI/TestPyPI/Hugging Face upload, PHI/EHR integration, model training, paid compute, external source-trust-root mutation or protected-main merge was made. **Keep PRIVATE DRAFT and `publication_authorized=false`.**
