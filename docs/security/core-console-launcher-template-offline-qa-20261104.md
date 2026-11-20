# MedOrigin Core — pinned installed console launcher template qualification

**Date:** 2026-11-04 (Asia/Riyadh)
**Status:** Private source-bound Core security QA, synthetic only. **NO RELEASE / MERGE / CLINICAL GO.**

## Exact source scope

Parent private Draft PR #892 commit `d97b2700de44560c51867b7813c575a43d8eea64`; new private branch `security/medorigin-core-pinned-console-launcher-gate-20261104`. **Functional source SHA `75d0ae0589dc3ff7c1382977439cd952b4895032`**. Changes: `scripts/check_installed_core_console_launcher.py`, `scripts/qualify_core_source_bound_fhir_provenance.py`, `tests/test_core_installed_console_launcher.py`, `tests/test_core_source_bound_fhir_provenance.py`, and this evidence report only. No shipped `src/medscale/` code, UI/Tauri/desktop, frozen research root `pyproject.toml` / `uv.lock`, MRL receipts, release workflow, registry or publisher settings changed.

Separate issue #893 https://github.com/AbdulazizShehri/MedOrigin/issues/893 tracks the **unresolved** true vendor-origin/PE-signature, supported installer and user-facing launcher admission requirement.

## Confirmed root cause from #892

The source-qualified Wheel owns all `medscale/` code, and the strict #892 installed FHIR QA invokes `medscale.cli:main` using its source-verified interpreter rather than the generated `medscale.exe` / `bin/medscale`. But a separately installed console launcher is **not** itself a source-qualified Wheel member. On Linux an added task-only synthetic marker line to a real offline-generated `bin/medscale` wrapper executed while the old stand-alone smoke still returned `LOCAL_FHIR_PROVENANCE_ONLY`. The strict module-mode QA bypasses it, but before this new change did not separately verify launcher bytes.

## New read-only, fail-closed pinned-template gate

`scripts/check_installed_core_console_launcher.py` opens the already-installed launcher as bytes **without executing it** and checks that the supplied launcher is the declared interpreter's sibling, not a symlink. It fails with **exit2** and fixed diagnostic `PINNED_INSTALLED_CONSOLE_LAUNCHER_BLOCKED` when unsupported, missing or modified. It emits `PINNED_CONSOLE_LAUNCHER_TEMPLATE_ONLY`, never a release approval.

For **Windows x86-64**, the observed local system-pip/distlib-generated PE file is decomposed into:
- A pinned **108,032-byte Windows PE executable stub** with SHA256 **`acd47a82dc01132e3b8414f683c2e117c18aedbf650a370249fe9fdbc445cda1`**.
- The **exact** `#!<declared-venv-Python-path>\n` line. Each virtualenv's full launcher SHA differs because this path differs.
- An exact **260-byte ZIP envelope**: a single STORED `__main__.py`, local header at archive offset0, central directory offset181, expected EOCD at the end, no appended or extra archive files, no comments/flags/extra, fixed embedded `medscale.cli:main` script. The `__main__.py` SHA256 observed from three independent real installs is **`e1e49cbbb5734e34d1624d58de3a2d6ce3d1ed804cd3914c87310bd120b94dde`**.

Actual offline-installed Windows system-pip native CPython3.11.15 **launcherA311** and **launcherB311**, plus native CPython3.12.13 **launcherC312** all matched the same PE-prefix SHA, size and embedded script but had different, correctly interpreter-bound shebangs. Their individual total file size was **108,372 bytes** for the task-owned path widths. Actual read-only checker returned **exit0** for all three; full receipts state `publication_authorized=false`, `independent_security_review_complete=false`, `clinical_use_authorized=false`.

For **Linux**, a real stdlib Python3.14.4 venv installed the identical source-qualified Wheel locally using `uv pip --offline --no-deps`. Its `bin/medscale` was the expected UTF-8, fixed `medscale.cli:main` text template and correct shebang. The checker returned `linux-pinned-uv-console-script`, **exit0**; WSL script wrapper exit0. This does **not** attest arbitrary Linux pip templates, shebang wrappers for very long/space-containing paths, or macOS profiles. **Unsupported templates fail closed**, rather than assuming equivalence.

**Critical limitation:** the PE prefix's pinned SHA comes from three **locally observed system-pip installs**, not from independently security-reviewed and signed vendor source/artifacts. The gate is a narrower, deterministic local byte-level template contract, **not independent Microsoft/Python/pip vendor authenticity**, certificate/signature verification, OS sandboxing, DLL-search confinement or full installer attestation. The exact PE trust anchor and independent reviewer signoff under #603 and issue #893 remain mandatory before distribution.

## Source-controlled adversarial tests, exact functional source SHA

`tests/test_core_installed_console_launcher.py` includes a fictional *nonexecutable* 108,032-byte `MZ` prefix, with its test-specific SHA patched locally and a synthetic 260-byte `__main__.py` ZIP. Tests reject altered PE bytes, false shebang/target paths, changed embedded script, bad local/central/trailing ZIP headers, extra bytes or prefix, truncated or double executable, modified Linux script, extra shell lines, wrong interpreter binding, and attempted release authority. This is not an executable PE test fixture and contains no patient data.

Together with `test_core_source_bound_fhir_provenance.py`, `test_installed_core_fhir_provenance.py`, `test_fhirkit.py`, `test_fhir_cli.py`, `test_base_core_publication_scope.py`, and `test_medorigin_prepublication_rehearsal.py` at functional commit `75d0ae0589dc3ff7c1382977439cd952b4895032`:

| Native Windows interpreter | Passed | Skipped | Deselected | Exit |
|---|---:|---:|---:|---:|
| Python3.11.15 | **217** | 2 | 2 | 0 |
| Python3.12.13 | **217** | 2 | 2 | 0 |
| Python3.14.7 | **217** | 2 | 2 | 0 |

**651 passing tests total**. The two skipped tests on each interpreter are Windows symlink permissions; two previously excluded standalone-wheel fixtures per interpreter were explicitly deselected. Py3.11/3.12 source tests reuse preinstalled pure-Python pytest via ephemeral PYTHONPATH, disable plugin autoload, use `--noconftest`; **not** hosted latest-head full 20-job CI nor hermetic per-version pytest installs. Ruff check, Ruff format --check and Git diff --check on changed files PASS.

## Native Windows and WSL actual installed-artifact proof

From an isolated WSL/ext4 Git clone of the **exact functional SHA `75d0ae0589dc3ff7c1382977439cd952b4895032`**, built offline the actual `medscale==0.3.0` Wheel/sdist. Both independent Wheel and sdist Git-source identity checkers returned exit0. The base publisher gate returned **exit2/BLOCKED**, as expected because optional research dependency/publisher approvals remain unresolved.

- Exact SHA source-bound Wheel `medscale-0.3.0-py3-none-any.whl` SHA256: **`b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`** (unchanged runtime payload).
- Exact SHA source-bound sdist `medscale-0.3.0.tar.gz` SHA256: **`06610ad3e635b573169159fafde7f0fff9da838346435270ebba5baac363575b`** (one build on WSL, not cross-host reproducibility evidence).

Reused task-owned native Windows CPython3.11.15 and3.12.13 stdlib venvs created with `python -m venv --without-pip`, installing this same byte-identical local Wheel via preinstalled system pip `--python <venv> install --no-compile --no-index --no-deps`, no network. The real **complete source-bound** Git→Wheel/sdist→venv startup hooks→250 installed package members→249 source file hashes each→**two pinned PE launcher file templates**→source-verified Python FHIR provenance check returned **exit0 TWICE** on the same installations. Receipts: `SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY`, `installed_console_launcher_templates_checked=2`, `installed_console_launcher_profile=windows-x64-pinned-pip-distlib`, `entrypoint_execution_mode=source_verified_python_module`; all publication, clinical, FHIR conformance, independent review, code signature, vendor origin, protected-main/tag flags **false**. Zero new `__pycache__` files after both runs on both venvs.

**Actual Windows negative:** in task-owned CPython3.12 `Scripts/medscale.exe` only, flipped **one byte** in its pinned PE executable prefix and reran the **whole** exact-Git source-bound qualifier. It returned **exit2 / SOURCE_BOUND_LOCAL_FHIR_PROVENANCE_BLOCKED**, emitted no positive JSON receipt, and never launched the mutated shim. Source negative wrapper exited0 after checking the refusal. Restored the original `.exe` **byte-exactly** and reverified its SHA256. A separate read-only checker also rejected that same kind of one-byte PE corruption with exit2 and a fixed, non-leaking error.

## Residual release gates and ownership

Even this pinned template evidence does not approve generated **user-facing CLI** installers: independent verification of binary launcher origin/certificate/signature/version, other supported installer and OS permutations (especially macOS), OS-level confinement, independent reviewer #603, and hosted exact-head CI are outstanding. Issue #893 deliberately **remains open** and cannot be closed on locally pinned PE bytes alone.

Also unresolved: #574 founder ADR-0045/version/publication decision, #622 optional research extras and dependency vulnerabilities, #877 true FHIR R4/profile/terminology validator, #882 old Developer Beta/native preview false-`valid` contract (other agent), and desktop native OS gates #662/#673/#676 (other agent). **No protected main merge, tag, release, signing, installer/PyPI upload, PHI/EHR, clinical use claim, code-signature claim, frozen project metadata/lockfile or UI work.** PRIVATE DRAFT only.
