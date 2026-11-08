# MedOrigin Core — source-binding installed Windows Python executable before use

**Date:** 2026-11-04 (Asia/Riyadh)
**Status:** PRIVATE DRAFT / source-bound synthetic Core security qualification only. **RELEASE / CLINICAL / VENDOR-SIGNATURE / MAIN MERGE NO-GO.**

## Exact source and ownership

Parent: Draft #897 at exact base SHA `cece16292f5b11af316bf0b6144b7dce80710451`. New branch `security/medorigin-core-windows-interpreter-source-binding-20261104`. Exact tested functional source commit **`f1738afedb447963be0b3b98cabff0ec9da3ece6`**. Five-file change: new `scripts/check_installed_core_python_interpreter.py`, `scripts/qualify_core_source_bound_fhir_provenance.py`, new `tests/test_core_installed_python_interpreter.py`, `tests/test_core_source_bound_fhir_provenance.py`, this evidence file. **NO packaged `src/medscale/` runtime**, native UI/desktop (other agent), frozen project-root `pyproject.toml`/`uv.lock`, MRL research, release workflow, publisher rights, public release or protected-main merge changed.

## Proven missing pre-execution control in parent #897

The earlier source-bound Core verifier checked `pyvenv.cfg` disabled system site-packages, inspected dangerous `.pth`/sitecustomize startup hooks, matched every Wheel-owned `medscale/` package file, and later used `<venv>/Scripts/python.exe` for installed source/FHIR QA. It did **not check the content of `python.exe` itself before invoking it**. The prior status label `source_verified_python_module` therefore overstated the interpreter-executable identity it actually established. This gap is distinct from the console shim gap previously closed in #892-#897.

Real controlled pre-fix reproduction: created **two isolated, task-owned native Windows Python3.11.15 and Python3.12.13 `python -m venv --without-pip`** environments. Copied the genuine 3.12 venv `Scripts/python.exe` executable bytes over the task-owned 3.11 venv `Scripts/python.exe` **without changing `pyvenv.cfg`**. At exact #897 code, `_reject_venv_startup_hooks(swapped_python311, 11)` still **returned success**, while the executable bytes actually represented CPython3.12. No assertion that the *whole* FHIR source-bound pipeline would have passed, and **no test altered a system-wide Python executable or executed malicious code**. Restored the test-owned original 3.11 binary byte-exactly and verified SHA256. The controlled proof wrapper exited0, logging `OLD_PRE_EXECUTION_PYTHON_BINARY_CHECK_ACCEPTED_WRONG_3_12_EXE=true`.

## Real, pinned local Windows CPython source relationships

On isolated Windows3.11.15 and3.12.13, stdlib `venv` creates `Scripts/python.exe` by copying **`<base Python>/Lib/venv/scripts/nt/python.exe`**, NOT by copying `<base Python>/python.exe`. Confirmed through real `venv.EnvBuilder.setup_python` introspection, actual file bytes and SHA comparisons. Both native `pyvenv.cfg` files point `home` and `executable` to the appropriate base Python and record the version and `include-system-site-packages = false`.

| Local Python profile | `Lib/venv/scripts/nt/python.exe` and venv `Scripts/python.exe` SHA256 | Base `python.exe` SHA256 |
|---|---|---|
| 3.11.15 | `4cca2027319c08dca5cc4b64c9ba415cc89205152202cb6805081277c43b610f` | `ae7e969410d751d010c2ca03394fe5c53230fbf48ca7d368b897e455eca14fba` |
| 3.12.13 | `0a864203aee170314ece97beaad6e50e226e76f0a3d73380a93ec472ed74f040` | `88b9e780cfdc38597c7f53e20f7165262befa28d9a5e9470360d349e172ecf37` |

Expected real venv launcher size is **262144 bytes** and base Python `python.exe` is **91648 bytes** for these local distributions only. Inspection of these local executable files with Windows `Get-AuthenticodeSignature` returned **NotSigned**. A SHA match and matching local source copy is **not independent upstream CPython/Python.org vendor authentication**, code signing, DLL integrity, or proof of OS/runtime confinement.

## Code-only correction

New stdlib-only read-only `check_installed_core_python_interpreter.py` requires the actual Windows `<venv>/Scripts/python.exe` and its CPython3.11 or3.12 local source file `<base>/Lib/venv/scripts/nt/python.exe` both byte-match the pinned version-specific SHA+size. It separately pins the base `python.exe` SHA+size, enforces unambiguous `pyvenv.cfg` fields `home`, `executable`, `version`, `include-system-site-packages`, resolves only exact base paths, and refuses symlink/junction/file mismatch at reviewed path surfaces. Unsupported Python versions and other OS profiles **fail closed**, not silently qualified. It never executes the target interpreter while inspecting its binary.

The strict `qualify_core_source_bound_fhir_provenance.py` now checks **both actual installed Python executable profiles first**, before `_reject_venv_startup_hooks`, package file comparisons, source-check subprocesses, launcher-template checks or FHIR module QA. The source-bound receipt adds `installed_python_executable_profiles_checked=2`, `installed_python_executable_profile=windows-cpython-3.11.15-3.12.13-local-pinned`; `python_vendor_authenticity_verified=false`, `python_code_signature_verified=false`, `publication_authorized=false`, `clinical_use_authorized=false`, and `fhir_conformance_validated=false` remain mandatory.

This is deliberately **not** general-purpose Python version allowance; updated distributions or alternative installer origin must be independently reviewed and pinned before admission. The check binds local known files, not all relevant base-DLL binaries or the system-wide OS trust chain. That residual risk remains a release NO-GO matter for #603 / #893.

## Focused proof and negative test

Actual unmodified native Windows venv CPython3.11.15 and3.12.13 executables each returned **exit0** from the new checker with `LOCAL_WINDOWS_VENV_PYTHON_SOURCE_BYTES_ONLY` and `installed_python_source_matches_base=true`. In test-only Windows3.11 venv, swapped its actual executable for the real Python3.12 venv launcher, invoked **new** checker, received **exit2 / INSTALLED_WINDOWS_PYTHON_INTERPRETER_BLOCKED**, **no positive JSON**, and restored the original executable SHA. The **same swap against the entire exact-Git Core source-bound qualification** also returned **exit2 / SOURCE_BOUND_LOCAL_FHIR_PROVENANCE_BLOCKED**, no positive receipt, **before executing the unqualified Python**; again restored task-owned original bytes and verified SHA.

Source-controlled synthetic adversarial tests additionally cover mismatching base interpreter bytes, incorrect canonical venv stub, changed/shortened/missing source, changed or duplicated config values, wrong Python version, forged positive receipt from a mock helper, and reject-before-FHIR ordering. No patient data or executable malware fixtures.

## Windows three-version test matrix

Eight selected non-UI Core test modules at exact functional source SHA `f1738afedb447963be0b3b98cabff0ec9da3ece6`:

`test_core_installed_python_interpreter.py`, `test_core_installed_console_launcher.py`, `test_core_source_bound_fhir_provenance.py`, `test_installed_core_fhir_provenance.py`, `test_fhirkit.py`, `test_fhir_cli.py`, `test_base_core_publication_scope.py`, `test_medorigin_prepublication_rehearsal.py`.

| Native Windows interpreter | Passed | Skipped | Deselected | Exit |
|---|---:|---:|---:|---:|
| Python3.11.15 | **253** | 2 | 2 | 0 |
| Python3.12.13 | **253** | 2 | 2 | 0 |
| Python3.14.7 | **253** | 2 | 2 | 0 |

**759 passing cases total**, no failing cases. The two skips per runtime are Windows symlink privilege limitations; the two deselections per runtime are existing independent standalone-Wheel fixtures. Python3.11/3.12 source-controlled pytest used the preinstalled pure-Python pytest via temporary `PYTHONPATH`, plugins disabled, `--noconftest`; **not a hermetic per-version test environment or hosted 20-job CI**. Ruff check, Ruff format--check on four code/test files and `git diff --check` passed.

## Actual offline source-bound Wheel / sdist + installed Windows QA

From isolated WSL/ext4 Git clone of exact SHA `f1738afedb447963be0b3b98cabff0ec9da3ece6`, source projection staged Core, built **genuine** `medscale==0.3.0` Wheel and sdist offline with installed `uv build --offline --no-create-gitignore`, and independently qualified both against that precise Git commit (both source identity checkers exit0). The publisher scope gate **STILL EXIT2/BLOCKED** due to research optional dependencies/unapproved publication scope.
- Exact Git source-bound Wheel SHA256 **`b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`** (no packaged production runtime change).
- Exact Git source-bound sdist one-build SHA256 **`b8c855d6399c069a85b8971a723d973cdfd3751eb961b81528d2b17321ebdb77`**.

Native Windows Python3.11.15+3.12.13 separate task-only stdlib venvs `--without-pip` installed only this same Wheel from local disk through preinstalled Python3.14.7 `pip26.2.1 --python <venv> install --no-index --no-deps --no-compile`. Actual local installer-generated Windows PE CLI shims match the pip vendor executable/RECORD identity gate from #897.

The **full exact-Git Core chain**, including Git source↔Wheel/sdist, 2 reviewed Python source-copy executables and pinned base binaries, venv startup-hook inventory, 250 Wheel-owned installed package files, 249 `.py` hashes per version, 2 pip-RECORD-bound console PE shims and the synthetic `not_validated` FHIR-module provenance reports, returned **exit0 TWICE on the same actual native Windows3.11/3.12 installations**. No extra `__pycache__` files were created during either full run. All clinical/publication, independent vendor-authenticity, Python code-signature, launcher-signature, FHIR-conformance and merge/tag authorization flags **false**.

## Residual NO-GO

The explicit exact-version local CPython pins are **not** an independent signed release provenance contract; base runtime DLLs, third-party module search, host OS integrity, Authenticode, independently authored binary hashes, supported alternative Python versions and macOS/Linux environments remain separately unqualified. #603 independent artifact/security signoff and #893 launcher/vendor identity review remain OPEN. Other release blockers: #574 founder ADR-0045/version/publisher authorization, #622 optional extras + default-branch advisory remediation, #877 true FHIR R4/profile/terminology validation, #882 legacy Developer Beta/native Desktop false-`valid` contract (other agent), full hosted exact-final-head CI/CodeQL, native desktop #662/#673/#676 (other agent).

**Never merge protected main, release/tag/sign/publish an installer or registry artifact, process PHI/EHR, claim clinical or FHIR conformance, edit frozen root/lock/MRL or other-agent UI/desktop.** The result is local source-integrity hardening only, with a private draft and publication still NO-GO.
