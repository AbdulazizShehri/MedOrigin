# MedOrigin Core — source-verified interpreter entry point, 2026-11-04

**Status:** PRIVATE Core security candidate, synthetic-only. **PUBLICATION / CLINICAL USE / MAIN MERGE NO-GO.** No production Core package bytes, native desktop, frozen root `pyproject.toml` / `uv.lock`, research or MRL receipt was changed.

## Source and scope

Parent: private Draft PR #889, exact SHA `a41117c3b922aa7263c66a18daa42b385bdc03e5`. New branch `security/medorigin-core-trusted-interpreter-entrypoint-20261104`. Functional, source-tested HEAD **`660ac9b7186cb65f32d3544862a061f39d96a5e1`**. Code changes limited to five QA/harness files:
- `scripts/check_installed_core_fhir_provenance.py`
- `scripts/qualify_core_source_bound_fhir_provenance.py`
- `scripts/qualify_medorigin_developer_beta.py` (only isolation flag and explanatory comments, not historical status)
- `tests/test_core_source_bound_fhir_provenance.py`
- `tests/test_installed_core_fhir_provenance.py`.

## Reproduced actual gap in parent #889

#889 verifies all **250 installed `medscale/` package files**, exact Git-bound Wheel/sdist, startup hook absence and all 249 Wheel Python source bytes per Windows interpreter, then invokes a separately generated `medscale.exe` or `bin/medscale` launcher. This console shim does **not** ship inside the reviewed Wheel payload and is not attested by the source-byte inventory.

On WSL/ext4, built a real `medscale 0.3.0` Wheel from immutable parent #889, installed only that offline Wheel into a clean stdlib Python 3.14.4 virtualenv, and **modified only the task-owned `venv/bin/medscale` shell/console script** by adding a benign one-line marker write. The parent package integrity gate still returned **250 exact package files** and `check_installed_core_fhir_provenance.qualify([actual cli])` still returned **`LOCAL_FHIR_PROVENANCE_ONLY`**, while the marker file was created. Complete synthetic proof exited0: `PACKAGE_FILES_MATCH_WHEEL 250`, `PARENT_CLI_GATE_STATUS LOCAL_FHIR_PROVENANCE_ONLY`, `UNQUALIFIED_SHIM_RAN True`. There is **no evidence of real malicious code, PHI exposure, clinical compromise or deployment**.

The stand-alone installed-CLI smoke must **not** be mistaken for launcher identity verification or a release approval.

## New strict execution path

`scripts/check_installed_core_fhir_provenance.py` accepts an optional `interpreters` list for its internal read-only `qualify` function. The source-bound caller passes the exact Python3.11 and3.12 paths **after** Git, Wheel/sdist, venv startup-hook, complete package inventory and Python source identity verification. It checks each interpreter exists and belongs to the same venv bin/Scripts directory as its declared CLI shim.

**Strict mode does not execute either generated CLI shim.** For each fixed version, real known/unknown fictional FHIR report, summary-only and malformed-input check, it invokes the source-verified installed Python by an explicit, fixed module entry point:

```text
<verified-venv-python> -E -s -P -B -c "from medscale.cli import main; raise SystemExit(main())" <arguments>
```

This executes the same committed module target `medscale.cli:main` that the independently qualified Wheel `entry_points.txt` advertises. The Python subprocess environment continues to scrub inherited `PYTHON*` and loader override variables; source bound still checks all installed `medscale/` package file identities, no unreviewed `.pth` hooks, and source/metadata identity. **The `-B` is critical:** `-E` ignores `PYTHONDONTWRITEBYTECODE`, so without explicit `-B` the QA process itself creates unreviewed `__pycache__` and fails subsequent full-inventory verification.

The formerly existing `scripts/qualify_medorigin_developer_beta.py::installed_wheel_matches` also now uses `-E -s -P -B -c` to prevent its source check creating caches. This change leaves the historical full Developer Beta release semantics blocked under #882.

Both modes are **explicitly distinguishable**, even though neither approves release:
- Strict source-bound: `execution_mode=source_verified_python_module` in local gate receipt, `entrypoint_execution_mode=source_verified_python_module` in outer receipt.
- Legacy stand-alone, caller-supplied executable: `execution_mode=unattested_installed_console_shim`. It is a functional smoke only, **NOT shim identity attestation**.
- `fhir_conformance_validated=false`, `publication_authorized=false`, `clinical_use_authorized=false`, `independent_security_review_complete=false`, `prepublication_rehearsal_qualified=false`, and `merge_or_tag_authorized=false` remain mandatory.

## Real controlled Linux proof after fixing the execution path

At code SHA **`cb6ba6cbad15d9c2a3ff875c61d151a3a7e9cfec`**, offline staged and source-verified the actual installed Wheel in WSL Python3.14.4. After inserting a harmless file marker into task-owned `venv/bin/medscale`:
- Strict `qualify([cli], interpreters=[installed_python])` returned `LOCAL_FHIR_PROVENANCE_ONLY` and **did not create the marker**.
- Stand-alone `qualify([cli])` returned explicitly `unattested_installed_console_shim` and the synthetic marker **was created**, confirming the two execution paths do not silently blend.
- Entire controlled offline experiment **exit0**; temporary source and venv cleaned using a task-owned WSL trap.
- Wheel SHA256 **`b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`**; that intermediate build's sdist SHA256 `90ac3e4c458a70def586dd6ae4128ff579153c92f9c038a0934b58316c3228ff`.

## Real Windows Python3.11 and3.12, exact FINAL functional SHA

After adding the explicit `-B` flag and adversarial tests, exact commit SHA **`660ac9b7186cb65f32d3544862a061f39d96a5e1`**. A new offline WSL Git clone of that precise commit staged and built the **exact-head** Wheel + sdist, and both existing source-bound Wheel and sdist verifiers passed; the independent publisher scope gate remained **exit2 / BLOCKED**, as required by unqualified optional extras. Exact final artifacts:
- Wheel SHA256 `b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`. Identical packaged Core source to the previous branch.
- sdist SHA256 **`294c2e8e87804dfe14e64af4371cd8b2f2deb6ddb705b669052820d7aa1ac2d3`**. Rebuilt for final exact Git head; one-build identity only, no cross-OS reproducibility claim.

The first Windows clean-baseline attempt at old SHA `cb6ba6c` passed once; repeating source-bound qualification failed because the `-E` child interpreter generated bytecode caches. This was fixed by explicit `-B` in **both** interpreter execution and source-byte verifier, and source-controlled regression tests were added. A later attempt against HEAD `660ac9b` initially returned BLOCKED because the sdist was still the **earlier HEAD's** artifact; independent `check_sdist_publication_scope.py` correctly reported `sdist source commit is not the checked-out HEAD`. No control was bypassed: rebuilt exact-head sdist before proceeding.

Created two clean, independent native Windows **Python3.11.15** and **Python3.12.13** stdlib virtualenvs with `python -m venv --without-pip`. Installed only the local qualified Wheel via installed system `pip --python <venv> install --no-compile --no-index --no-deps --no-cache-dir` without network downloads, avoiding precompiled unreviewed package bytecode. On the same actual venvs, source-bound verifier full Git → Wheel+sdist → startup-hook inventory → every installed package file → 249 installed Python source files per runtime → synthetic FHIR tests was run **TWICE**:

| Attempt | Source-bound exit | Py3.11 package cache entries | Py3.12 package cache entries | Mode |
|---|---:|---:|---:|---|
| 1 | **0** | **0** | **0** | `source_verified_python_module` |
| 2 | **0** | **0** | **0** | `source_verified_python_module` |

All clinical, publication, independent-review and FHIR conformance flags false. This is **idempotent local QA**, not hosted CI or validation of an installed user-facing console shim.

**Real native Windows shim substitution test:** In the task-owned Python3.12 venv only, changed `Scripts/medscale.exe` temporarily into a non-executable fictional byte string (not a real malware payload). The same strict full source-bound qualifier on Python3.11/3.12 still returned **exit0**, explicit `source_verified_python_module` and unchanged synthetic report hashes. The intentionally unusable CLI shim was not executed. Restored the exact original `.exe` bytes and verified SHA-256. **This test proves only that the QA harness no longer relies on the untrusted shim. It does NOT certify that a user-facing `medscale.exe` is correctly packaged or signed.**

## Source-controlled cross-version regression matrix

At final functional code SHA `660ac9b7186cb65f32d3544862a061f39d96a5e1`, selected six non-UI Core test modules: `test_core_source_bound_fhir_provenance.py`, `test_installed_core_fhir_provenance.py`, `test_fhirkit.py`, `test_fhir_cli.py`, `test_base_core_publication_scope.py`, `test_medorigin_prepublication_rehearsal.py`.

| Windows interpreter | Passed | Skipped | Deselected | Exit |
|---|---:|---:|---:|---:|
| Python3.11.15 | **195** | 2 | 2 | 0 |
| Python3.12.13 | **195** | 2 | 2 | 0 |
| Python3.14.7 | **195** | 2 | 2 | 0 |

**585 passing cases total**, six skipped cases from Windows host inability to create symlinks, six preexisting standalone-wheel cases intentionally deselected. Ruff lint, Ruff format --check on all five edited files and `git diff --check` all exited0. On Python3.11/3.12, tests reused preinstalled pure-Python pytest from Python3.14 by process-local PYTHONPATH, disabled plugin autoload, `--noconftest`; this is **not** hermetic per-version pytest installation or full repo/hosted 20-job CI.

## Residual risk, ownership and release NO-GO

**The generated Windows `medscale.exe` / Linux `bin/medscale` remains an unaudited installation-time launcher.** This PR intentionally bypasses it in the *nonpublishing source-bound verifier* rather than claiming it is signed, authentic or secure for users. Before any public CLI/desktop installer distribution, a separate independent launcher-shim identity/build/signature gate and a real installed user-facing invocation test are required. A separate issue/review packet should track that work; the historical Developer Beta native/preview still assumes false FHIR `valid`/exit0 in #882 and is separately agent-owned.

Other unchanged release blockers: #574 ADR-0045/founder version/publisher authority, #622 unqualified optional research extras/advisories, #603 independent source/artifact/security signoff, #877 missing actual FHIR R4/profile/terminology validator, #882 legacy UI/native report incompatibility, newest exact-head hosted full CI/CodeQL, and other-agent-owned desktop #662/#673/#676.

No protected-main merge, release tag, installer publication, signing, PyPI/TestPyPI upload, model/provider use, PHI/EHR, clinical claim or frozen root/lock/MRL mutation. **PRIVATE DRAFT. SOURCE-BOUND PROVENANCE ONLY. RELEASE NO-GO.**
