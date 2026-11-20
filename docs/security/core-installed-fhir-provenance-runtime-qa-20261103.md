# MedOrigin Core — installed FHIR provenance-only QA and legacy-demo NO-GO

**2026-11-03 (Asia/Riyadh). PRIVATE, SYNTHETIC ONLY, NO PUBLICATION AUTHORITY.**

## Why this work was required

A previous Core correctness fix (Draft #878, issue #877) changed the local `medscale fhir validate` contract from a misleading unconditional `status=valid` / exit0 to `status=not_validated` with a fixed warning / exit2 because **no real HL7 FHIR R4 schema, terminology or profile validation runs**. This is a necessary fail-closed change, not a demonstration of FHIR conformance.

The existing standalone installed Developer Beta demo and release prepublication rehearsal still require the old `valid` / exit0 report and a pinned old report SHA. The static preview and native Tkinter desktop are owned by a **different UI/desktop agent**; this branch does not edit those interfaces or relax their old allowlist. Verified incompatibility is tracked in [issue #882](https://github.com/AbdulazizShehri/MedOrigin/issues/882).

## Direct reproduction of the legacy blocker

At source-bound immutable Git SHA `3c261c728b88b7a9371fc026626ef6ef9deeb69c` (parent PR #879), on authorized local WSL Linux/ext4, staged 254 Core source files from committed Git, built the Wheel+sdist using preinstalled `uv 0.12.21 --offline --no-create-gitignore`, and installed only the local `medscale==0.3.0` Wheel into a clean Python3.14.4 virtual environment with `uv pip install --offline --no-deps`. Running the **untouched** `examples/synthetic_fhir_developer_beta/reproduce.py --cli <actual installed CLI> --out <fresh directory>` produced **exit 1** with `MEDORIGIN_SYNTHETIC_FHIR_DEMO_FAIL: run_1: FHIR command failed`. There was no qualifying `evidence.json`. This is a correct fail-closed disposition and **must not** be bypassed by restoring false `valid` reporting.

Legacy `scripts/qualify_medorigin_developer_beta.py` also requires the old `MEDORIGIN_SYNTHETIC_FHIR_DEMO_PASS` and expected report SHA256 `991d319d9c567db3a71985661a12abb67c8432ff43b439c08759f8ee1d52fbd9`. `examples/synthetic_fhir_developer_beta/preview.py` explicitly admits only `structural_status=valid` and `valid_exit=0`. Full GUI and original prepublication rehearsal remain **NO-GO** pending separate review. No frozen history, old receipt or UI was changed.

## New, independent Core-only positive check

Source-only `scripts/check_installed_core_fhir_provenance.py` uses **Python standard library only** and runs an already-installed CLI from a verified local Wheel, optionally a second independently installed CLI. It checks:

- CLI `--version` is exactly `medscale 0.3.0`. The caller must separately run the existing exact Git source-bound Wheel/sdist identity checks before trusting the installation.
- Both the pinned fictional `StructureDefinition` and an invented `UnknownFictionalResource` must produce **exit2**, `status=not_validated`, **exactly one nonclinical fixed warning**, empty errors, exact content hashes, fixed timestamp/validator/format and **no extra or duplicated JSON keys**.
- Each CLI output must correspond byte-for-byte to exactly one local, non-symlink, persisted content-addressed report (allowing the CLI's precisely known extra trailing newline).
- Explicit `--summary-only` still returns exit0 for exact synthetic input; malformed JSON must return exit1 without a success report.
- If two *different installed CLI paths* are given, both environments must agree exactly on deterministic report hashes. No actual patient data, full FHIR validation, external validator, network service, inference or model is required.
- The JSON evidence intentionally reports **`status=LOCAL_FHIR_PROVENANCE_ONLY`** and five explicit `false` gates: `fhir_conformance_validated`, `publication_authorized`, `clinical_use_authorized`, `independent_security_review_complete`, `prepublication_rehearsal_qualified`. It can **never** become `TECHNICAL_PREPUBLICATION_REHEARSAL_PASS` nor approve release.
- On error, the script returns exit2 with fixed `CORE_FHIR_PROVENANCE_BLOCKED` and never forwards untrusted CLI stdout, stderr, report contents or local paths.

19 source-controlled tests in `tests/test_installed_core_fhir_provenance.py` cover success, bad/forged `valid`, incorrect warnings/errors/input hash, duplicate JSON keys, changed saved report, an extra stdout newline, wrong exit, missing/double-counted CLI, differing paired receipts, oversize output, subprocess timeout and nonpublication claims.

## Exact functional code and Windows source QA

Functional HEAD **`053390cbec4b6fcb88209bb127f91f6d8e940b26`** (branch `qa/medorigin-core-installed-fhir-provenance-20261103`), source-controlled tests, and clean Rust/UI isolation. An initial candidate `a29c531` was too strict about the CLI's double stdout newline; this was corrected at `94652b0`, and test fixture Ruff issues were formatted at `053390c`. These were **bounded QA harness** changes, not modifications to CLI or FHIR runtime semantics.

- Windows Python **3.11.15**: 19/19 focused new tests PASS, exit0.
- Windows Python **3.12.13**: 19/19 PASS, exit0.
- Windows Python **3.14.7**: 19/19 PASS, exit0.
- On that same source, a broader non-UI source selection of `test_installed_core_fhir_provenance.py`, `test_synthetic_fhir_developer_beta_example.py`, `test_medorigin_prepublication_rehearsal.py`, `test_fhirkit.py`, and `test_fhir_cli.py`: **104 PASS, 1 SKIP, 2 DESELECTED** on Windows Python3.14.7, exit0 (6.60sec). Skip is Windows host inability to create symlinks; two deselected tests require separate standalone wheel/pip fixture path. Not whole-repository 355-test-file CI.
- Ruff lint, Ruff format --check on new script+test and Git diff whitespace check PASS.
- Python 3.11/3.12 focused tests used installed pytest8.4.2 pure-Python files via ephemeral PYTHONPATH, with plugin auto-loading disabled and `--noconftest`: actual interpreter runs but not hermetic per-version pytest installs.

## Actual clean-installed Wheel and paired CLI, Linux and Windows

A local SHA-verified Core source checkout was used to generate a real `medscale-0.3.0-py3-none-any.whl` using `uv build --offline --no-create-gitignore` on WSL Linux/ext4; its SHA256 was **`b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`**, matching previous functional-Core builds because this branch only adds QA scripts and tests, not packaged source bytes.

- **WSL Linux:** installed that Wheel into two independent fresh Python **3.14.4 virtual environments** via `uv pip install --offline --no-deps`; final corrected script, run against both real `venv/bin/medscale` entrypoints, **exit0**, exact output `LOCAL_FHIR_PROVENANCE_ONLY`, `installed_cli_count=2`, five false authority gates. All temporary source/venv/report files were deleted by task-owned cleanup trap. Both virtual environments use **the same Python minor version**; this does **not** count as cross-version Linux qualification. A prior verification wrapper also exited1 due PowerShell here-doc quoting after the Core checker itself exited0; the final verified script used an unambiguous inline Python assertion and exited0.
- **Actual Windows Python 3.11.15 and Python 3.12.13**, separately: copied the **identical SHA256-verified Wheel** onto a task-owned D: folder, created two separate `python -m venv` environments, then `pip install --no-index --no-deps --no-cache-dir --disable-pip-version-check` installed exactly the local Wheel in each, with **no network index**. Both installed `Scripts/medscale.exe --version` returned `medscale 0.3.0`, `pip show` confirmed `Version: 0.3.0`. Running the new source-controlled verifier via installed Windows Python3.14 against **both real Windows executables** returned **exit0**, `LOCAL_FHIR_PROVENANCE_ONLY`, paired SHA256 output:
  - `known_report_sha256=165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08`
  - `unknown_report_sha256=7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c`
  - The same report SHA256 pair occurred in the separate Linux Python3.14.4 pair, confirming **this bounded deterministic synthetic receipt** is identical across these host/interpreter combinations. It does not prove full cross-OS CI or true FHIR standard validation.
- A preliminary Windows install post-check `python -c` command failed only because of PowerShell quotation handling; actual Python3.11 Wheel installation had already succeeded. A subsequent simple installed `medscale --version`, `pip show`, and actual paired verifier run completed successfully on both Python versions; no production failure was inferred.

No network call initiated by this harness, paid compute, PHI/EHR data, Docker, provider/model service, desktop UI, signed artifact, registry upload, tag or public release occurred.

## Remaining gate / handoff

Original synthetic FHIR **UI/preview/native desktop and release rehearsal remain blocked** under issue #882 until the separate desktop/UI owner reconciles report admission and the old pinned SHA, without advertising unperformed validation. No changes were made to `examples/synthetic_fhir_developer_beta/preview.py`, Tk desktop code or other agent worktrees.

Other standing NO-GO: actual qualified HL7 FHIR R4/profile/terminology validator #877; independently attributable source/artifact/security approval #603; optional-extras/dependency advisories #622; founder ADR-0045/package/version/publisher authorization #574; newest exact-head hosted full CI/CodeQL; native desktop #662/#673/#676. The read-only canonical source research root `pyproject.toml`, `uv.lock`, historical `v0.2.0` and sealed MRL evidence remain untouched. `publication_authorized=false`. **PRIVATE DRAFT; NOT RELEASED; NO CLINICAL CLAIMS.**
