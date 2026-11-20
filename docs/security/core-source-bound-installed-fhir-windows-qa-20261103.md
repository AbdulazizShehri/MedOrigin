# MedOrigin Core — source-bound installed FHIR provenance qualification (2026-11-03)

**Status:** PRIVATE, synthetic-only, **RELEASE NO-GO**. This is a separate Core-only enhancement stacked on private Draft #883. Production Core, UI/native desktop, frozen research root and release workflows are unchanged.

## Exact source / affected scope

Functional Git source SHA: **`229f12fa873cd0fb2e869da9b3de6c355471df48`**. Immediate parent #883 HEAD `d9d0144fc3940d191315bf9be174ba96cebb61af`; historical #879/#878/#876/#875/#874/#873 source stack remains separately open/private. Only:
- `scripts/qualify_core_source_bound_fhir_provenance.py` (new stdlib-only Core, no external dependency, publisher or UI change)
- `tests/test_core_source_bound_fhir_provenance.py` (new negative, source-bound test file)
- this documentation.

## The safety boundary that was missing

Previous #883 `scripts/check_installed_core_fhir_provenance.py` proves the result of an *already installed* CLI with synthetic fixtures but **delegated** trust in the code origin to the caller. Checking `medscale --version` plus a self-reported JSON receipt is **not** proof that the installed package bytecode/source matches the reviewed Git artifact. A substituted binary could produce the same public fictional output without being the vetted Wheel. The standalone #883 check is still useful as a local provenance-only smoke, but an end-to-end source-to-install qualification must bind each step independently.

This change supplies the missing read-only source/installation trust chain by invoking the existing (unchanged) canonical source verifiers instead of creating another package hash oracle:

1. Require exact clean Git checkout HEAD identity, canonical 40-hex SHA, no tracked/untracked source modifications.
2. Qualify Wheel **against committed Git source**, `check_core_wheel_source_identity.py`; verify reported Git SHA exactly matches checkout.
3. Qualify sdist **against the same committed Git checkout**, `check_sdist_publication_scope.py`; require `SDIST_SCOPE_QUALIFIED_ONLY`, zero issues and `publication_authorized=false`.
4. Qualify installer-visible Wheel metadata with `inspect_release_wheel_metadata.py`; require canonical `medscale 0.3.0` and report SHA-256 equals independently hashed actual Wheel.
5. Reuse historical source-bound `installed_wheel_matches()` under **actual, independent Windows Python 3.11 and 3.12 interpreters**: the internal `-E -s -P` subprocess checks imported distribution version and the actual installed bytes of *every* expected Python source member against the Wheel using per-file SHA-256. Require same, complete source inventory on both runtimes.
6. Locate both real `Scripts/medscale.exe` entry points and run #883's independent fail-closed FHIR provenance checker. Both must return `not_validated`/exit2 for known fictional StructureDefinition and entirely invented resource type; agree on both saved report SHA256s; allow explicit summary-only without claiming schema conformance.
7. Emit **only** `SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY` with `fhir_conformance_validated=false`, `prepublication_rehearsal_qualified=false`, `publication_authorized=false`, `clinical_use_authorized=false`, `merge_or_tag_authorized=false`, `independent_security_review_complete=false`. A source-bound technical provenance receipt is **never** the former, still-blocked `TECHNICAL_PREPUBLICATION_REHEARSAL_PASS` and never grants release authority.

The new script uses bounded, locally executed subprocesses through the existing source verifier wrapper, exact error/status checks, fixed non-sensitive diagnostics and no network/build/install/publish side effects.

## Source-controlled Windows tests

New `tests/test_core_source_bound_fhir_provenance.py` contains **23 source-controlled cases**: good synthetic source-bound receipt; dirty or malformed Git head; rejection by Wheel source identity, sdist source identity and metadata verifier; wrong Wheel commit/hash/version; missing/tampered/divergent installed Python source inventory; false or coerced FHIR/publication/clinical authority, corrupted report hashes or differing digests; duplicate interpreter paths; missing assets and no leaked secret source path.

After Ruff format and unused import correction, exact **functional code SHA `229f12fa873cd0fb2e869da9b3de6c355471df48`**:
- Windows Python **3.11.15**: **23/23 PASS** (0.77s), exit0
- Windows Python **3.12.13**: **23/23 PASS** (0.73s), exit0
- Windows Python **3.14.7**: **23/23 PASS** (0.66s), exit0
- Ruff check and Ruff format --check for both new source-controlled files: **PASS**
- Git diff whitespace check against parent: **PASS**

For these focused tests, Python3.11/3.12 borrowed preinstalled pure-Python pytest8.4.2 from Python3.14 through process-local `PYTHONPATH` and disabled plugin auto-load, `--noconftest`. These are **not** hermetic per-interpreter pytest environments or full repository tests; actual independent runtime installation is evidenced separately below.

## Real offline Git → Wheel+sdist → installed Windows Python3.11/3.12 → FHIR E2E

A disposable WSL Linux/ext4 Git clone at the **same immutable code SHA `229f12fa873cd0fb2e869da9b3de6c355471df48`** produced an exact Core projection and built using existing `uv 0.12.21 build --offline --no-create-gitignore`. Wheel and sdist passed independent source-identity checks **EXIT0/QUALIFIED_ONLY**. The **publisher gate returned EXIT2/BLOCKED intentionally** due known unapproved optional runtime/research extras; `publication_authorized=false`. Actual immutable Core Wheel was copied to task-owned D: QA path. SHA256:

- Wheel `medscale-0.3.0-py3-none-any.whl`: **`b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`**.
- sdist `medscale-0.3.0.tar.gz`: **`68653a8c030d6a270826f772baca7699022a3a67303eb048d5605b83b85d0941`**. One build's SHA, not a cross-host sdist reproducibility claim.

Two **genuinely separate** native Windows virtualenvs created from existing Python **3.11.15** and **3.12.13**. Each used `pip install --no-index --no-deps --no-cache-dir` to install **exactly** this local Wheel with no downloaded dependencies. Both actual installed `medscale.exe --version` returned `medscale 0.3.0`.

The **new full source-to-install gate** ran using existing Python3.14.7 over that clean source checkout, exact Wheel+sdist and each installed native Python interpreter, **EXIT0**, yielding:
- `status=SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY`
- `source_git_commit=229f12fa873cd0fb2e869da9b3de6c355471df48`
- `installed_python_source_files_verified_per_runtime=249` on **each** Windows 3.11 / 3.12 installation
- `runtimes=["3.11","3.12"]`
- `known_report_sha256=165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08`
- `unknown_report_sha256=7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c`
- all six authority/conformance/readiness Boolean gates explicitly **false**.

### Real tampered-installed-source negative

With baseline success established, in the **task-owned disposable Python3.12 venv only**, appended a benign fictional comment to `site-packages/medscale/__init__.py` without modifying Git, Wheel or sdist. Reran the same source-bound qualifier on both interpreters; **exit 2**, diagnostic `SOURCE_BOUND_LOCAL_FHIR_PROVENANCE_BLOCKED`, no successful JSON receipt. The actual installed file was restored byte-for-byte with original SHA-256 verified. The first test runner's PowerShell `$ErrorActionPreference=Stop` interpreted the intentionally nonzero subprocess stderr as a PowerShell native error; after safely restoring the file, a corrected wrapper that collects the intended negative exit returned **script EXIT0**, with the measured qualifier EXIT2 and restore hash confirmed. No real patient data, network, repository source or reviewed artifact was modified by this synthetic negative.

## Governance and outstanding NO-GO

**This is not a finished release.** The historical full Developer Beta prepublication rehearsal and GUI/static/native preview still require obsolete false `valid` / exit0 and old pinned digest; separate owner reconciliation tracked in #882. Real FHIR R4 schema, profile and terminology validation does not exist (#877). Independent source/artifact/security signoff #603, owner version/ADR-0045/publisher permission #574, optional advertised extras/advisories #622, exact-final-head hosted full 20-job CI/CodeQL, and separate UI/desktop OS gates #662/#673/#676 are still missing. The GitHub remote additionally reported default-branch security advisories during the push (not independently verified per dependency and **not** a finding that this minimal installed Wheel contains those default-branch vulnerabilities).

No protected-main merge, release, tag, signing, installer, PyPI/TestPyPI, model training, PHI/EHR, clinical validation, frozen canonical root `pyproject.toml`, `uv.lock`, MRL receipt or UI/desktop mutation. All private development/practice evidence is source-controlled and release remains **NO-GO**.
