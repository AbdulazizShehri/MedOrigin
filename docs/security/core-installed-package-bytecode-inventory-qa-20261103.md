# MedOrigin Core — full installed-package integrity, forged bytecode QA

**Date:** 2026-11-03 (Asia/Riyadh)  
**Status:** Private Draft, synthetic only. **Publication remains NO-GO.**

## Source boundary

Parent: private Draft PR #887, exact Git commit `fcce2c49037067974b748c67a03ce2c367c9bf28`. Functional code/test commit **`97b32ed5fcc32ebdb62ca279352f6c18e2149244`**. This branch changes only `scripts/qualify_core_source_bound_fhir_provenance.py`, `tests/test_core_source_bound_fhir_provenance.py` and this evidence document. No packaged MedScale code, UI/native desktop, frozen canonical research root `pyproject.toml`, `uv.lock`, MRL files, release workflow or registry permissions changed.

## Reproduced true security problem in parent #887

Previous source-to-installed trust bound the Git source to Wheel, then verified **249 expected Python `.py` source file SHA-256s** in each installed interpreter and rejected top-level unreviewed venv startup hooks. This **does not authenticate bytecode files automatically loaded by Python in preference to unchanged `.py`**.

On local WSL/ext4 at exact, unmodified parent Git SHA, staged immutable Core source, built a genuine local `medscale==0.3.0` Wheel/sdist using preinstalled `uv build --offline --no-create-gitignore`, and installed only the Wheel into isolated stdlib Python3.14.4 `venv --without-pip` via `uv pip install --offline --no-deps`. The original source bound and FHIR gate both passed with clean installed package.

The test then kept `medscale/cli/fhir.py` **byte-for-byte untouched**, but created a synthetic **valid timestamp+source-size `medscale/cli/__pycache__/fhir.cpython-314.pyc`**. Its compiled code appended only a harmless temporary marker write to an otherwise unchanged module. On the original verifier, **all 249 `.py` source files still matched** and the real installed CLI still emitted `LOCAL_FHIR_PROVENANCE_ONLY`, but the unauthorized bytecode executed and created the local marker. The **entire test command exited 0** with `AFTER_FORGED_PYC_SOURCE_COUNT 249`, `AFTER_FORGED_PYC_GATE_STATUS LOCAL_FHIR_PROVENANCE_ONLY`, `FORGED_PYC_EXECUTED True`, and `FORGED_PYC_ORIGINAL_GATE_FALSE_ADMISSION_CONFIRMED_EXIT_ZERO`.

This is an actual, reproducible provenance-qualification weakness, **not** evidence of real compromise, exposed PHI or production exploitation.

## Core-only correction

New `_verify_installed_package_inventory(wheel, installed_python, expected_minor)` is called for both installed Python runtimes **before either verifier launches them**. It compares the entire Wheel-owned `medscale/` package subtree (not merely Python sources), using stdlib only:

- Use the already source-qualified Wheel's actual `medscale/` archive member inventory; reject unsafe or duplicate relative names.
- Construct all expected nested package directories; refuse new/extraneous or symlink directory entries. Use `os.walk(followlinks=False)`, fail closed on walk errors.
- Stream SHA-256 comparison of **every installed package file** including non-Python assets, with expected uncompressed byte length and source Wheel SHA-256. Refuse changed/missing/symlink files and every extra `*.pyc`, `*.pyo`, `__pycache__`, unqualified source/native extension or data file; don't execute the target Python during inspection.
- Require identical full installed inventory counts on both native Python3.11 and3.12 environments, then preserve the old 249-`.py` SHA verifier and FHIR synthetic `not_validated`/exit2 receipt chain.
- Keep `SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY`, `publication_authorized=false`, `fhir_conformance_validated=false`, `clinical_use_authorized=false`, `merge_or_tag_authorized=false`, `prepublication_rehearsal_qualified=false`. This does **not** provide full HL7 FHIR validation or release approval.

## Test results — exact functional source SHA

### Linux real offline Wheel
From exact SHA `97b32ed5fcc32ebdb62ca279352f6c18e2149244` on local WSL/ext4, offline staged Core Wheel/sdist passed existing independent Git/source-bound Wheel and sdist checks. Genuine Wheel installed only into clean stdlib Python3.14.4 venv via `uv pip --offline --no-deps --link-mode=copy`. New scanner on clean installed package found **250 files** and the actual CLI FHIR provenance returned `LOCAL_FHIR_PROVENANCE_ONLY`. A deliberately forged timestamp/size-compatible `.pyc` added to the task-owned package was **rejected before starting CLI**, with **no synthetic code execution marker**. Full Linux test script exited **0** and cleaned test-owned temp files via trap.

### Native Windows 3.11 / 3.12 end-to-end
Same exact SHA source Wheel and sdist separately built offline on WSL/ext4; independently qualified against original Git. **Publisher admission still exit2/BLOCKED** for unqualified advertised optional extras. Copied only source-qualified local artifacts into task-owned Windows D: QA directory.

- Wheel SHA256 **`b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`**.
- One build's sdist SHA256 **`2b2691b5e7f03652407f6e00f543f0fb19eff618f79d511159dbba9ada2b3e9e`**. No cross-host sdist reproducibility claim.

Important installation nuance: native Windows `pip install` normally **precompiles `.pyc` files** for installed modules. The strict new source-only Core publication-qualification gate deliberately refuses these unreviewed compiled files, *including legitimate pip cache*. For this isolated QA workflow, create fresh, separate `python3.11/3.12 -m venv --without-pip`, then invoke the **already installed system pip** with `--python <venv_python> install --no-compile --no-index --no-deps --no-cache-dir`. No user-wide files were removed, no downloaded packages. Both resulting isolated environments had **zero `__pycache__` / `.pyc` files** before verification.

At exact source SHA, full native Windows **Git→Wheel+sdist→complete installed package inventory→249 source-byte checks per runtime→FHIR synthetic provenance** returned **exit0** and status `SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY`. Both independent Python3.11.15 and3.12.13 installations passed with 249 source files each and canonical synthetic report hash pair:
- known: `165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08`
- fictional unknown type: `7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c`

On the task-owned Python3.12 installation, added a single synthetic extra `__pycache__/fhir.cpython-312.pyc` (fixed harmless test bytes) and reran the **same full source-bound qualifier**; it returned **exit2**, fixed `SOURCE_BOUND_LOCAL_FHIR_PROVENANCE_BLOCKED`, **no positive JSON**, and the temporary synthetic directory was removed. The negative test wrapper exited0 after verifying refusal and cleanup.

### Windows source-controlled matrix
At exact functional SHA, combined five source-controlled test modules: `test_core_source_bound_fhir_provenance.py`, `test_installed_core_fhir_provenance.py`, `test_fhirkit.py`, `test_fhir_cli.py`, and `test_base_core_publication_scope.py`.

| Interpreter | Passed | Skipped | Deselected | Exit |
|---|---:|---:|---:|---:|
| Python3.11.15 | 176 | 1 | 2 | 0 |
| Python3.12.13 | 176 | 1 | 2 | 0 |
| Python3.14.7 | 176 | 1 | 2 | 0 |

**528 passes total**; the skipped case is Windows host symlink permission and the two deselections per runtime are existing standalone-wheel fixture cases. Additional tests check forged cache directories, legacy `.pyc`, extra `.py`/`.pyd`/JSON, modified source or data asset, missing files, extra empty directories, and symlink file (skipped if Windows privileges disallow). Ruff check, Ruff format --check and `git diff --check` passed. These are process-local `--noconftest` tests with preexisting pure-Python pytest imported via ephemeral `PYTHONPATH` on Windows3.11/3.12, **not full hosted CI**, not hermetic per-version pytest installations. Actual installed native venv QA was done separately.

## Boundaries and remaining NO-GO

This gate checks the installed `medscale/` package subtree and venv startup-hook locations, not a complete operating system sandbox. It does **not** independently attest console `.exe` shims, every dist-info file, all possible import-path shadowing, installed third-party modules or OS-level dynamic library injection. Any proposed exception to unreviewed Python bytecode needs explicit independent review and a reproducible artifact identity.

Remaining absolute release blockers: #574 founder ADR/version/publisher authorization, #622 optional advertised research extras/advisories, #603 genuine independent source/artifact/security signoff, #877 actual FHIR R4/profile/terminology validation, #882 legacy Developer Beta `valid` assumption and native desktop semantics (owned by other agent), exact-final-head hosted 20-job CI/CodeQL, and native desktop issues #662/#673/#676. Private Draft only. **No protected-main merge, tag, signing, installer, registry upload, PHI/EHR, external models, clinical/diagnostic claim, frozen research `pyproject.toml`/`uv.lock` or other-agent UI modification.**
