# MedOrigin Core — installed pip RECORD / console-launcher vendor resource integrity

**Date:** 2026-11-04 Asia/Riyadh
**Decision:** Private synthetic-only source-bound Core QA. **RELEASE / FHIR CONFORMANCE / INDEPENDENT VENDOR SIGNOFF STILL NO-GO.**

## Source, boundaries and reproducible finding

Private Draft stacked on PR #895 at exact base `4c1a15e7396ab2dc25e3e0503ebc9a9c2318edc0`, new branch `security/medorigin-core-pip-record-attested-launcher-20261104`. Exact tested functional Git source **`b57af20d3675d0e60c08f45f450c8b42930a5b4e`**. Changes only four source/QA files plus this report: `scripts/check_installed_core_console_launcher.py`, `scripts/qualify_core_source_bound_fhir_provenance.py`, `tests/test_core_installed_console_launcher.py`, `tests/test_core_source_bound_fhir_provenance.py`. No shipping `src/medscale` code, native UI/desktop, frozen `pyproject.toml`/`uv.lock`, historical research MRL, release workflow, release publishing or owner-approved authority modified.

**Confirmed issue in previous #895 pinned Windows launcher template:** The 108,032-byte, SHA256 `acd47a82dc01132e3b8414f683c2e117c18aedbf650a370249fe9fdbc445cda1` executable prefix was exactly equal to the local vendored `pip/_vendor/distlib/t64.exe` in **two installed Python runtimes**, Python3.11.15 and3.12.13 running `pip 26.1.2`. However their installed `pip-26.1.2.dist-info/RECORD` entries for that exact path both listed `sha256=gaYY8hy4fbkHYTTnA4i26ct8IQZzkBG2pRdy0iyuBrc`, equivalent to **SHA256 `81a618f21cb87db9076134e70388b6e9cb7c2106739011b6a51772d22cae06b7`**, **NOT** the actual resource. The file length (108,032) did match RECORD. This is a real **local installation-integrity mismatch**, not by itself evidence of compromise, malicious modification or which tool caused it. The previous template hash came from locally installed bytes without comparing the vendor resource to its own RECORD; it was insufficient to attest a distro identity.

An independent installed **Python3.14.7 + pip26.2.1** had vendored `t64.exe` bytes SHA `81a618f21cb87db9076134e70388b6e9cb7c2106739011b6a51772d22cae06b7`; its local `pip-26.2.1.dist-info/RECORD` listed the **same matching sha256 and 108032 byte length**. This installed pip version itself is **not** a trusted or remotely signed upstream distribution merely because its local RECORD matches.

## New fail-closed vendor-resource chain

The strict Core launcher checker on Windows x64 now **revokes the former `acd47...` template** and only accepts a locally observed, explicitly pinned `pip26.2.1` `t64.exe` executable prefix SHA `81a618...`. It requires:
1. The actual installed `medscale.exe` must have that exact SHA-pinned 108032-byte PE prefix, the target-vEnv-Python shebang and exact 260-byte one-entry ZIP `__main__.py` envelope. No unknown prefixes, modified payload, extra ZIP entry or trailing bytes.
2. Match the **same entire PE prefix bytes** to the read-only installed pip `_vendor/distlib/t64.exe` resource.
3. Inspect `pip-26.2.1.dist-info/METADATA` and require unique `Name: pip` and `Version: 26.2.1`. Inspect `RECORD` as CSV, require exactly one `pip/_vendor/distlib/t64.exe` member with correct raw SHA256-base64 digest and exact file size; fail on missing, duplicate, wrong-size, mis-hashed or unreviewed vendor resources. Validate file/directory existence, symlinks and bounded sizes; do not import/execute the vendor package.
4. By default the *source verifier's Python installation* is the source of its `pip` resource (`sys.prefix/Lib/site-packages/pip`). A caller can explicitly provide `--installer-pip-root` for a different source, which still must match the pinned digest **and** its own RECORD. This does **not** cryptographically prove that such a pip actually performed the install, only that the launcher matches the selected and locally RECORD-consistent resource.
5. The full `scripts/qualify_core_source_bound_fhir_provenance.py` refuses a Windows installed-laucher receipt without `installer_pip_resource_record_matched=true`. It still **never executes** the unreviewed launcher for FHIR QA: it uses source-qualified interpreter module execution with `-E -s -P -B`. Output explicitly keeps `launcher_vendor_authenticity_verified=false`, `launcher_code_signature_verified=false`, `publication_authorized=false`, `clinical_use_authorized=false`, `fhir_conformance_validated=false`, and `independent_security_review_complete=false`. Linux keeps its separately pinned uv-script template, not a fabricated pip RECORD check.

**Known installer requirement:** Use a task-owned isolated stdlib `python3.11/3.12 -m venv --without-pip`, then already-installed **Python3.14 pip26.2.1** `python -m pip --python <venv>/Scripts/python.exe install --no-index --no-deps --no-compile <source-bound-wheel>`. This uses no downloaded package and leaves generated PE bytes matching the locally RECORD-consistent pip vendor resource. Do not overwrite/delete a user's existing Python installation or vendor files.

## Actual offline Wheel and native Windows proof at FINAL functional Git SHA

A fresh isolated WSL/ext4 Git clone at `b57af20d3675d0e60c08f45f450c8b42930a5b4e` staged and built actual `medscale 0.3.0` Wheel and sdist using preinstalled uv `--offline --no-create-gitignore`. Existing independent Git↔Wheel and Git↔sdist identity verifiers passed; **base publisher-scope gate returned expected exit2/BLOCKED**, as research optional extras/publisher decisions still lack approval. Source artifact SHA256:
- Wheel: **`b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`**.
- Exact functional Git HEAD sdist, one WSL build: **`37b6587c6106938782e4c7301220664cb44db7d5139d27cd1640ac8c636bc61d`**. No cross-host sdist reproducibility claim.

Two native Windows CPython3.11.15 and3.12.13 **task-only independent venvs** installed the same real offline Wheel using host Python3.14.7 `pip26.2.1 --python`, `--no-index --no-deps --no-compile`. The generated PE launcher prefixes were both SHA `81a618...`, identical to source pip26.2.1 vendored `t64.exe`, whose local RECORD also matched. Standalone updated launcher checker returned **exit0** on both; `installer_pip_resource_record_matched=true`, version 26.2.1 and all release/signature/vendor flags false.

**The whole strict source-bound chain** (exact Git clean checkout → Wheel/sdist Git-source identity → startup-hook constraints → 250 installed package member bytes → 249 installed source `.py` files per Python version → BOTH PE launchers+pip RECORD → source-verified Python FHIR synthetic report) returned **EXIT0 TWICE** on the same native Win3.11/3.12 venvs, `SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY`, `installer_pip_resource_record_matched=true`, profile `windows-x64-pip-26.2.1-record-bound`, and **zero new `__pycache__` bytes** after either run.

**Negative actual Windows tests:** Swapping the selected pip vendor root to the earlier, non-RECORD-matching `pip26.1.2` source returned **exit2** and **no success JSON**, even when the installed launcher itself was clean. A new task-only Python3.11 venv installing the exact same Wheel with the older pip26.1.2 generated the previous `acd47...` prefix and now correctly returned **exit2/BLOCKED**, no positive JSON. Separately, a single-byte edit to the task-owned clean Win3.12 `medscale.exe` prefix made the **entire strict source-bound chain** exit **2 / SOURCE_BOUND_LOCAL_FHIR_PROVENANCE_BLOCKED**, emit no success JSON and refuse before installed FHIR execution. The test-only modified executable was restored **byte-exactly with matching SHA**.

## Source-controlled regression matrix

Combined seven non-UI Core modules: `test_core_installed_console_launcher.py`, `test_core_source_bound_fhir_provenance.py`, `test_installed_core_fhir_provenance.py`, `test_fhirkit.py`, `test_fhir_cli.py`, `test_base_core_publication_scope.py`, `test_medorigin_prepublication_rehearsal.py`.

At functional commit `b57af20d3675d0e60c08f45f450c8b42930a5b4e`:

| Native Windows Python | PASS | SKIP | DESELECTED | Exit |
|---|---:|---:|---:|---:|
| 3.11.15 | **231** | 2 | 2 | 0 |
| 3.12.13 | **231** | 2 | 2 | 0 |
| 3.14.7 | **231** | 2 | 2 | 0 |

**693 passing cases** across these three source-only interpreter runs, Ruff lint/format, Git diff--check all PASS. The two Windows symlink cases are skipped per version for host privileges, and two existing standalone Wheel fixture tests were intentionally deselected per version; tests use `--noconftest` and the already-installed pure-Python pytest via ephemeral PYTHONPATH for Python3.11/3.12, not hosted full 20-job CI or per-version hermetic pytest distribution.

## Residual release NO-GO

The local installed pip `RECORD` is **not an independently authenticated upstream vendor signature**. A local attacker with write access to both pip files and their RECORD could alter their contents; the hardcoded PE hash blocks arbitrary alterations within this pinned profile but is not Windows Authenticode, supply-chain review or validated DLL-loading confinement. A genuine authorized independent vendor-origin review for the exact PE stub, signer and version is **still mandatory**, especially for user-distributed Windows installers. macOS and all unreviewed installer/version/long-shebang combinations fail closed. Issue #893 and independent security issue #603 must **remain open** pending those decisions.

All other blockers remain: #574 founder ADR-0045/version/publisher authority, #622 optional dependencies/advisories, #877 true FHIR R4/profile/terminology validator, #882 old Developer Beta/native false-`valid` report (other agent), latest exact-head hosted CI/CodeQL, and other-agent-native desktop #662/#673/#676.

No protected-main merge, release tag, signing, installer/PyPI/TestPyPI distribution, PHI/EHR use, live clinical validation claim, frozen root/lock/MRL mutation or agent-owned UI/desktop work. **PRIVATE DRAFT — SOURCE/INSTALLATION INTEGRITY ONLY — RELEASE NO-GO.**
