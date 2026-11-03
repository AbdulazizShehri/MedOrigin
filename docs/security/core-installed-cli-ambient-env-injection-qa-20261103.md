# Core installed CLI — ambient Python startup isolation (2026-11-03)

**Status:** PRIVATE source-only security candidate, synthetic-only, NOT approved for release.

## Confirmed original trust gap (actual offline installed Wheel)

At immutable parent #884 HEAD `48eb8395a728b2b2593de2feb36423ac8b2b752f`, built the source-bound `medscale==0.3.0` Core Wheel from committed Git on local WSL/ext4 with preinstalled `uv build --offline --no-create-gitignore`. Installed just that real local Wheel in an isolated Python3.14.4 virtualenv using `uv pip install --offline --no-deps` (no network, paid inference, other dependencies or PHI/EHR).

The previous `scripts/check_installed_core_fhir_provenance.py::call` copied all parent `os.environ`, then set only HF/Transformer/PIP offline flags. Source-bound qualifier #884 checks **installed package source files** with `-E -s -P`, but **executes the actual installed CLI afterward without equivalent interpreter environmental isolation**.

A task-owned synthetic `sitecustomize.py`, placed **outside** the Wheel and installed virtualenv under a separate temporary directory, appended a fixed marker when `PYTHONPATH` pointed to it. A clean parent Python process set `PYTHONPATH` and a marker-only environment variable **just before** calling the original verifier. The actual installed CLI ran the outside-Wheel startup module **five times**, while the original FHIR QA verifier still returned `status=LOCAL_FHIR_PROVENANCE_ONLY`. It accepted the evidence even though interpreter startup executed unqualified code. This proves ambient Python startup code can run alongside a source-matched CLI; it does **not** prove any real patient data leaked, malicious supply-chain artifact existed, or exploit was used outside this benign controlled proof.

The original verification printed `UNMODIFIED_GATE_STATUS LOCAL_FHIR_PROVENANCE_ONLY`, `UNTRUSTED_PYTHON_SITE_CUSTOMIZE_EXECUTIONS 5`, and `CONFIRMED_ENV_INHERITANCE_WITH_REAL_INSTALLED_WHEEL=true`; that **first shell wrapper** exited 1 afterward because an extraneous here-doc terminator was interpreted as Python code. The observed verifier acceptance and five marker writes occurred **before** the wrapper error. Do not cite that wrapper as a successful end-to-end command exit.

## Bounded code correction

In `scripts/check_installed_core_fhir_provenance.py`, build a **new** environment for the installed CLI rather than forwarding all Python startup/injection flags. Explicitly remove all inherited `PYTHON*` variables, independently of casing (including `PYTHONPATH`, `PYTHONHOME`, `PYTHONUSERBASE`, `PYTHONWARNINGS`, `PYTHONSTARTUP` and `PYTHONINSPECT`), and ambient runtime-loader injection overrides `LD_PRELOAD`, `LD_LIBRARY_PATH`, `DYLD_INSERT_LIBRARIES`, `DYLD_LIBRARY_PATH`, `DYLD_FRAMEWORK_PATH`, `DYLD_FALLBACK_LIBRARY_PATH`, `DYLD_FALLBACK_FRAMEWORK_PATH`. Then set `PYTHONNOUSERSITE=1`, `PYTHONSAFEPATH=1`, `PYTHONDONTWRITEBYTECODE=1`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `PIP_NO_INDEX=1`. The installed CLI still launches via its exact caller-provided executable path, with cwd set to a fresh task-owned temporary directory; no shell, model, external validator or network access is introduced.

This is **not** a total sandbox/attestation: untrusted installed `.pth` or editable packages inside site-packages, OS-wide DLL injection, compromised binaries, untrusted binary extensions, or running Python in an already compromised OS remain separate concerns. The source-bound chain and independent security review are mandatory. Release remains NO-GO.

## Regression and source QA at functional head `5d6afe25b5a403f53e28ccd1441efff3702dddeb`

New tests in `tests/test_installed_core_fhir_provenance.py` verify (1) exact scrubbed `subprocess.run(env=...)` with injected Python and loader overrides, offline flags retained, and (2) an actual child Python interpreter started via the qualified wrapper refuses to load a synthetic outside-Wheel `sitecustomize.py` from inherited `PYTHONPATH`, without writing its marker file.

Combined test modules `tests/test_installed_core_fhir_provenance.py` + `tests/test_core_source_bound_fhir_provenance.py`:
- Windows real Python3.11.15: **44/44 PASS**, exit0 (0.62s)
- Windows real Python3.12.13: **44/44 PASS**, exit0 (0.65s)
- Windows real Python3.14.7: **44/44 PASS**, exit0 (0.80s)
- Ruff check, Ruff format --check and Git diff --check **PASS**.

Python 3.11/3.12 source-controlled pytest used preinstalled pure-Python pytest modules through ephemeral `PYTHONPATH`, plugin auto-loading disabled, `--noconftest`: this is NOT a hermetic per-version pytest environment or hosted full Core CI.

## Real corrected offline-installed Wheel proof

Under new code SHA `5d6afe25b5a403f53e28ccd1441efff3702dddeb`, independently staged source and built a **real** `medscale-0.3.0-py3-none-any.whl` and sdist offline on WSL ext4. Installed Wheel only into fresh Python3.14.4 virtualenv with `uv pip install --offline --no-deps --link-mode=copy`. Just before calling the corrected **actual** installed-CLI FHIR QA verifier, set parent `PYTHONPATH` to an external synthetic sitecustomize directory, set `PYTHONHOME` to an invalid path, and passed a benign marker-only variable. The qualified Wheel's CLI ran normally; output `ACTUAL_QUALIFIER_STATUS=LOCAL_FHIR_PROVENANCE_ONLY`; **external sitecustomize marker file remained nonexistent**. Corrected complete WSL QA command **EXIT0**, printing `REAL_INSTALLED_CLI_AMBIENT_INJECTION_BLOCKED=true` and `FIXED_ENV_ISOLATION_REAL_WHEEL_TEST_EXIT_ZERO`. All task-owned WSL paths were under `/tmp/medorigin-core-cli-env-fixed-qa-20261103` with `trap` cleanup; no protected main mutation or publication.

## Release qualification unchanged

Still NO-GO: #574 owner ADR-0045/version/publisher authority, #603 independent source/artifact/security review, #622 advertised unqualified optional extras and existing advisory findings, #877 no actual FHIR R4 schema/profile/terminology validator, #882 legacy Developer Beta preview/desktop old `valid` receipt incompatibility, hosted current exact-head CI/CodeQL, and native desktop #662/#673/#676 owned by a different agent. Do not modify frozen `pyproject.toml`, `uv.lock`, MRL receipts or historical evidence to get green CI. No protected-main merge, tag, signing, installer, public package distribution, patient data or clinical claim. `publication_authorized=false`.
