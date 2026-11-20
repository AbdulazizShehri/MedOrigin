# MedOrigin Core — Windows CPython runtime loader DLL inventory / no-shadow prerequisite

**2026-11-04 Asia/Riyadh — PRIVATE DRAFT, nonpublishing source-bound Core security QA.** Publication, clinical/PHI use, FHIR R4 conformance, independent binary vendor origin, signature verification and protected-main merge remain **NO-GO**.

## Scope and exact source

Stacked atop private Draft #899 at base SHA `7156c10191896f72f5782e146c22b87bf4518178`. Branch `security/medorigin-core-windows-runtime-loader-inventory-20261104`, tested **functional code+tests SHA `7a78c0ea01ccffa3f32aa65ec857e865e1ca36be`**. Changes only source-owned prepublication verifier `scripts/check_installed_core_python_interpreter.py`, its strict caller `scripts/qualify_core_source_bound_fhir_provenance.py`, and two source-controlled tests `tests/test_core_installed_python_interpreter.py`, `tests/test_core_source_bound_fhir_provenance.py`, plus this evidence note. No production `src/medscale` package source, UI/native desktop, frozen research root `pyproject.toml`/`uv.lock`, MRL receipt, release workflow, registry or protected-main mutation.

## Real gap in #899's pre-execution trust check

#899 already pinned actual task-controlled Windows3.11.15/3.12.13 `venv/Scripts/python.exe` redirectors against their local CPython base stdlib sources and pinned base `python.exe`. It did **not** validate the **base CPython runtime DLLs** or reject unknown native-loader files in `venv/Scripts`.

Reproduced a concrete *missing check* on a genuine Windows3.11.15 task-owned stdlib `venv --without-pip`: wrote one **non-executable fictional text sentinel** named `Scripts/python311.dll` containing `FICTIONAL NONEXECUTABLE DLL SHADOW SENTINEL - DO NOT LOAD`. The previous #899 read-only `check_installed_core_python_interpreter.py` returned **exit0** and `LOCAL_WINDOWS_VENV_PYTHON_SOURCE_BYTES_ONLY`, despite the unqualified native-loader search-path file. **This does not demonstrate that Windows loaded the sentinel or that real malware executed**; it proves the verifier had no DLL-shadow preflight. Removed the test-owned sentinel and checked it absent. No base/system Python runtime was changed.

## New finite, fail-closed local Windows runtime profile

`scripts/check_installed_core_python_interpreter.py` now verifies four additional **fixed SHA256/length** base CPython runtime DLLs for each already-pinned exact local version. Each read-only check requires a regular, non-symlinked file of expected length and exact content digest.

| Local profile | Base runtime file | Expected bytes | Expected SHA256 |
|---|---|---:|---|
| Windows CPython3.11.15 | `python3.dll` | 55,296 | `52fa723f646402678f9fc53157dbe9de0a980bdcd74c293a8a6233c3dfd15e49` |
| Windows CPython3.11.15 | `python311.dll` | 5,842,944 | `e1b53c741751563eca9eac70378de5be36994adac8c27e8ec375971579e23b50` |
| Windows CPython3.12.13 | `python3.dll` | 56,320 | `6a396b3814d727e3715e747a121bcbc2bf1e07906bbe8c292e7a3e719d72b9d4` |
| Windows CPython3.12.13 | `python312.dll` | 6,969,856 | `cf1be428af1ee607d8015e27411912276b9b02815a080457a1ece46c59d9b314` |
| Both reviewed versions | `vcruntime140.dll` | 124,544 | `d5e4d9a3e835fa679450145d6a7d94e36573a509317111904d9b3712c30d9066` |
| Both reviewed versions | `vcruntime140_1.dll` | 49,792 | `1f2d41c4aa5db0bc33ebf7b66d72943a817d7ce6cbe880502a9403823633093f` |

These bytes were observed on the two installed uv-managed local Python distributions; these are **not independent signed reference measurements from python.org**, and no assertion of global package availability or arbitrary Python versions is made.

New read-only pre-execution inventory also scans precisely the **venv root and its Scripts directory** and refuses **any** `*.dll`, `*.pyd`, or `*._pth` file there, and native executables or Python-prefixed links at those surfaces. This disallows an unreviewed adjacent native loader or Python module-path override even when the installed Wheel's `medscale/` source files remain intact. It does **not** scan the whole OS loader search path, all base DLLs, DLL dependencies of arbitrary extension modules, current working directory/PATH, global policy, or defend against files changed after this check. The OS-level process loader/TOCTOU trust boundary remains an independent security-review issue.

Strict `qualify_core_source_bound_fhir_provenance.py` already invokes this Python verifier **before** either installed Python subprocess; now refuses a receipt unless `installed_base_runtime_dlls_verified == 4` and `unqualified_venv_loader_shadow_files_rejected is True` per runtime. Its output adds `installed_base_runtime_dlls_verified_per_runtime=4` and `installed_python_loader_shadow_directories_checked_per_runtime=2`, while retaining `python_vendor_authenticity_verified=false`, `python_code_signature_verified=false`, `launcher_vendor_authenticity_verified=false`, `launcher_code_signature_verified=false`, `fhir_conformance_validated=false`, `publication_authorized=false`, `clinical_use_authorized=false`, `independent_security_review_complete=false`, `merge_or_tag_authorized=false`.

## Actual native Windows no-network testing

On task-owned native Windows3.11.15 and3.12.13 independent stdlib `venv --without-pip`, both genuine `Scripts/python.exe` + base runtime DLL profiles produced exit0 and **four verified DLLs per interpreter**. A new **fictional, nonloadable** `venv311/Scripts/python311.dll` text file made the new standalone checker return **exit2 / INSTALLED_WINDOWS_PYTHON_INTERPRETER_BLOCKED**, with no positive receipt. File removed immediately; unrelated OS Python installations never altered.

New source-controlled adversarial tests cover fake-but-consistent pinned DLL fixtures, wrong runtime SHA, altered `python3.dll`, missing `python3.dll`, changed VC runtime DLL, injected `python311.dll` in venv Scripts, injected `python3.dll` in venv root, `fictional_extension.pyd` and `python311._pth` adjacent to executable, plus overclaimed launcher receipts, exact pre-execution failure order and all existing source-binding tests. Tests use fictional non-executable byte/text files only. New focused source suite **84 passed, 1 skipped** on Windows Python3.14.

Eight non-UI Core source-controlled modules on the exact functional Git SHA `7a78c0ea01ccffa3f32aa65ec857e865e1ca36be`:

| Native Windows interpreter | Passed | Skipped | Deselected | Exit |
|---|---:|---:|---:|---:|
| Python3.11.15 | **262** | 2 | 2 | 0 |
| Python3.12.13 | **262** | 2 | 2 | 0 |
| Python3.14.7 | **262** | 2 | 2 | 0 |

**786 passing cases**, zero failing cases. Two Windows symlink checks per version skipped because the host does not have symlink privileges; two existing standalone-Wheel cases per version intentionally excluded. Python3.11/3.12 reused already-installed pure pytest via ephemeral PYTHONPATH and `--noconftest`, plugin autoload disabled: **NOT** full hermetic or hosted 20-job CI. Ruff check+format and Git diff --check PASS on the four edited source files.

## Real exact-Git source-bound Wheel/sdist + installed Windows proof

From an isolated WSL/ext4 Git clone of precise functional commit `7a78c0ea01ccffa3f32aa65ec857e865e1ca36be`, built genuine `medscale==0.3.0` Core source projection, sdist and Wheel using preinstalled `uv build --offline --no-create-gitignore`; independently source-verified Wheel and sdist against **the same exact commit** (both checks exit0). Base publication-scope checker deliberately returned **exit2/BLOCKED** due to unapproved research optional dependencies.
- Wheel SHA256 `b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1` (production package unchanged).
- Exact functional Git one-build sdist SHA256 `2f01fb4fbcefcaf5dd8d7f73ab7486e660b578dbbb4d48ada4dd97a9da37b33b`.

Installed the same qualified offline Wheel via installed host Python3.14.7 `pip26.2.1 --python <venv>` with `--no-index --no-deps --no-compile` into native task-owned Win3.11 and3.12 separate venvs; both started without package `.pyc` caches. The **FULL** source-bound Git→Wheel/sdist→**2 pinned Windows Python redirector+base executable+4 runtime DLLs each/no shadow files**→venv startup hooks→250 full installed Core package files→249 installed source `.py` files per interpreter→both pinned pip26.2.1 RECORD-bound Windows console launchers→synthetic-only FHIR provenance via source-verified Python module returned **exit0 TWICE on the same installations**, with zero new bytecode files after either run. Both resulting receipts explicitly retain all vendor/clinical/conformance/publication flags false.

**Full-chain negative:** wrote one fictional non-executable text sentinel named `venv311/Scripts/python311.dll` in *only the task-owned installed Python3.11 venv*, reran the **entire Git-bound installed QA**, observed **exit2 / SOURCE_BOUND_LOCAL_FHIR_PROVENANCE_BLOCKED**, **no positive JSON**, rejected before executing either unqualified interpreter. Deleted sentinel and verified absence. This is proof of a finite local preflight, not proof that the Windows dynamic linker would have loaded that content.

## Still not a release approval

#603 independent artifact/security review and #893 independently authenticated Windows launcher/CPython source signature remain OPEN. Local CPython executable and DLL pins are *not cryptographic provenance from the upstream vendor*, and do not close DLL search-directory ordering, all OS native dependencies, malicious host/admin, or TOCTOU threats. Other nonnegotiable blockers: founder #574 ADR-0045/version/publisher authority, #622 optional extras/dependency alerts, #877 true FHIR R4/terminology/profile validation, #882 old Beta/native desktop false-valid semantics (different agent), full hosted exact-latest-HEAD CI/CodeQL, native desktop #662/#673/#676 under another agent.

No merge/tag, public releases, installer/signing/PyPI/TestPyPI publishing, real PHI/EHR, clinical claim, root/lock/MRL or another agent's UI/desktop changes. **PRIVATE DRAFT — SOURCE-BOUND LOCAL RUNTIME PROFILE ONLY — RELEASE NO-GO.**
