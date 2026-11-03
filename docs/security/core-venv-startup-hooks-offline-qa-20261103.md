# Core virtualenv startup-hook integrity — 2026-11-03

**PRIVATE synthetic-only Core Developer Beta security candidate. NOT a publication, clinical-conformance or independent-security approval.** This branch stacks on private Draft #886 at immutable parent `6bf8ca8d71b18723a78c07a02b2462d8a95e3d9a`. Functional, source-tested Git commit `aca78c999c30b597b855a94bbda00298fc4b861d`.

## Proven original false admission on a real offline-installed Wheel

After #886 scrubbed `PYTHONPATH` and other parent environment variables, a different startup vector still remained: Python automatically executes import lines inside `*.pth` files **inside the venv's site-packages** on interpreter initialization. `-E -s -P` ignores the parent PYTHON environment, user-site and current working directory, but **does not disable venv site-packages `.pth` execution**.

From exactly committed parent #886 source, an isolated WSL/ext4 Git clone staged and built an actual `medscale==0.3.0` Wheel/sdist with preinstalled `uv 0.12.21 --offline --no-create-gitignore`; only the local Wheel was installed in an isolated Python 3.14.4 venv. Into **that task-owned venv only**, appended a synthetic `zz_medorigin_fictional_test.pth` containing one harmless `import` line writing a fixed local marker. The real parent `qualify_medorigin_developer_beta.py::installed_wheel_matches(wheel, installed_python, 14)` still returned **249 matching Python source files**, and parent `check_installed_core_fhir_provenance.py::qualify([actual installed medscale CLI])` returned `LOCAL_FHIR_PROVENANCE_ONLY`, while the injected `.pth` **executed and wrote its marker**. The complete original-source reproduction command exited **0** with:
- `SOURCE_BYTE_MATCH_COUNT=249`
- `PARENT_FHIR_GATE_STATUS LOCAL_FHIR_PROVENANCE_ONLY`
- `UNQUALIFIED_PTH_EXECUTED_WHILE_PASSED=true`

This is a confirmed **qualification evidence gap**, not evidence that an actual EHR, patient, external system or deployed release was compromised.

## Fail-closed fix — inspect before launching either installed Python runtime

`scripts/qualify_core_source_bound_fhir_provenance.py` adds `_reject_venv_startup_hooks(installed_python, expected_minor)` **immediately before** calling the existing `installed_wheel_matches` and the real CLI check. It uses only the host's stdlib filesystem APIs; it never starts the target Python as part of its pre-exec scan. It now requires:
- a real, bounded, nonsymlink `pyvenv.cfg`, with one unambiguous `include-system-site-packages = false` setting;
- a real, nonsymlink venv site-packages directory at the expected Windows `Lib/site-packages` or Linux `lib/python3.X/site-packages` path, also inspecting a distinct existing `lib64` site-packages path;
- no unqualified top-level `*.pth` (case-insensitive), `sitecustomize`, `sitecustomize.*`, `usercustomize`, or `usercustomize.*` entries.

This *deliberately rejects* even plausible `.pth` startup files unless they undergo a separately approved, pinned security review. It does not try to accept/execute them based only on their filename. The existing source-bound Wheel+sdist identity, installed 249 source-byte checks and fail-closed `not_validated` FHIR checks remain unchanged. All release/clinical/FHIR-conformance flags remain `false`.

## Important verified installation-tool nuance

**An initially clean `uv venv` on WSL failed the stricter scan.** This is expected from its generated `site-packages/_virtualenv.pth`, whose content was exactly `import _virtualenv`; that in turn loads the tool-generated `_virtualenv.py`. It is *part of uv's environment bootstrap*, not a confirmed malicious file, but neither file belongs to the source-qualified MedOrigin Wheel. The Core trust gate cannot silently treat that executable bootstrap as reviewed.

The supported test installation path uses **`python -m venv --without-pip`**, then installs the exact offline-qualified Wheel with local-only pip tooling (`uv pip --offline --no-deps` on Linux or system `pip --python <isolated_venv_python> install --no-index --no-deps` on Windows). A real WSL Python3.14.4 stdlib venv created this way had an **empty site-packages startup-hook inventory** and `include-system-site-packages = false`; the actual installed Wheel passed the scan and installed CLI FHIR smoke. Adding a benign `.pth` then produced **`QualificationError` before launching the venv interpreter** and no execution marker; after removing the task-owned file, the installed CLI smoke again passed. The entire final offline Linux command exited **0**.

This is an explicit qualification workflow constraint, not a recommendation to delete arbitrary `.pth` files from a developer's existing environment. No global environment or other agent's files were changed.

## Real native Windows 3.11 / 3.12 source-bound installed test

From exact functional Git source `aca78c999c30b597b855a94bbda00298fc4b861d`, WSL/ext4 built genuine artifacts offline and independently verified Wheel/sdist source identity. Base publication-scope gate remained expected **EXIT2/BLOCKED** for unapproved optional extras; `publication_authorized=false`. Copied only these source-qualified artifacts to one task-owned Windows D: QA directory:

- Wheel SHA256: `b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`.
- One build's sdist SHA256: `262aeb3f8ae48e481c6b2f972324b2e03b7a908ab151647403ad87727c15979c`. No cross-host sdist reproducibility claim.

Used native CPython **3.11.15** and **3.12.13** to create independent stdlib venvs via `python -m venv --without-pip`. Installed only the same local Wheel to each with the already-installed system `pip --python <venv_python> install --no-index --no-deps --no-cache-dir`; neither install has any top-level startup hook. Both installed `medscale.exe --version` returned `medscale 0.3.0`.

The **real entire source-bound qualifier** on the clean Git checkout, exact Wheel+sdist and both native installed Python paths **EXIT0**, with `status=SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY`, **249 installed Python source files matched per runtime**, source commit exact, known/unknown synthetic report hashes `165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08` and `7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c`, and every clinical, FHIR-valid, independent-review, merge, tag and publication Boolean `false`.

**Real negative on Windows:** created only a fictional additional `.pth` in the task-owned Python3.12 venv, with a harmless local file-creation line. Re-ran the *whole* source-bound qualifier, which returned **EXIT2**, wrote **no success JSON**, only fixed `SOURCE_BOUND_LOCAL_FHIR_PROVENANCE_BLOCKED`, and the marker file **did not exist**. Removed the synthetic `.pth` afterward. Test wrapper finished **EXIT0** after asserting refusal and cleanup.

## Source-controlled adversarial matrix

`tests/test_core_source_bound_fhir_provenance.py` extends the 23 existing source trust tests with cases for `.pth` case alias, `sitecustomize.py`, `sitecustomize` package, `usercustomize.py`, inherited system site config, duplicate/absent `pyvenv.cfg`, missing site-packages directory, and clean fixture. All rejected cases assert **no call to the installed-runtime verifier**.

At code SHA `aca78c999c30b597b855a94bbda00298fc4b861d`, the combined source-controlled modules for source binding, installed FHIR, FHIR local report/CLI and base publisher gate:
- Windows **Python3.11.15**: **165 PASSED / 2 DESELECTED**, 11.36 sec, exit0.
- Windows **Python3.12.13**: **165 PASSED / 2 DESELECTED**, 5.97 sec, exit0.
- Windows **Python3.14.7**: **165 PASSED / 2 DESELECTED**, 9.97 sec, exit0.
- Ruff lint, Ruff format --check and Git diff --check: **PASS**.

These tests use `--noconftest` and borrowed preinstalled pure-Python pytest8.4.2 on Python3.11/3.12 through ephemeral `PYTHONPATH`, with plugins disabled; **not** full hosted 20-job CI or per-version hermetic pytest install. Two existing standalone packaging cases were intentionally deselected; actual offline installed Wheel qualification is separately demonstrated above.

## Residual boundaries / release decision

The new scan covers these documented venv-level automatic startup hooks only. It **does not** guarantee OS-level process isolation, rule out compromised base interpreters, validate arbitrary installed extensions or certify all third-party site modules. The strict venv policy must remain subject to independent security review #603, and separately reviewed startup files would need a **pinned explicit exception**, not a blanket bypass.

Release stays **NO-GO** for #574 ADR-0045/version/publisher authority, #622 unqualified optional research extras/advisories, #603 independent source/artifact/security signoff, #877 true FHIR R4/profile/terminology validation missing, #882 legacy Developer Beta/desktop FHIR-valid incompatibility, latest exact-HEAD hosted CI/CodeQL, and separate agent-owned desktop #662/#673/#676. No main merge, release, tag, signing, installer, PyPI/TestPyPI, patient data/EHR, clinical claim, canonical research `pyproject.toml`/`uv.lock`, historical MRL receipts or UI/desktop work was changed. **PRIVATE DRAFT only; `publication_authorized=false`.**
