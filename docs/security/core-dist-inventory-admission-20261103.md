# MedOrigin Core — fail-closed distribution directory inventory (2026-11-03)

**Scope:** PRIVATE, nonpublishing Core publisher admission hardening. Isolated draft stacked on Wheel header integrity PR #869, with source base `9069af014f627952639969a40e9299960463a758`. Does not change desktop/UI, synthetic FHIR logic, frozen research `pyproject.toml` / `uv.lock`, CI workflow or publication authority.

## Reproduced bypass

The Core publication scope gate originally enumerated only `dist/medscale-*.whl` and `dist/medscale-*.tar.gz`. The PR and release upload jobs in `.github/workflows/release.yml` use a broad `dist/*` upload glob. A third, unqualified `dist/unqualified-9.9.9-py3-none-any.whl` therefore fell outside the admission inventory yet remained in the upload set.

**Actual baseline test on authorized Windows:** A clean synthetic Wheel/sdist pair returned `BASE_CORE_PUBLICATION_SCOPE_CLEAN` with `publication_authorized=false`; adding an unrelated synthetic placeholder Wheel as a third file still returned `BASE_CORE_PUBLICATION_SCOPE_CLEAN` with three items in `dist`. No untrusted binary was executed, installed or uploaded.

## Narrow fix

The gate now builds an expected inventory from its two validated MedScale compatibility-name artifacts and **refuses any other entry** in `dist`, including a foreign Wheel/sdist, sidecar, subdirectory or hidden file. It also refuses a symlinked distribution directory. The existing exact-one expected Wheel/sdist checks and per-artifact size/symlink/metadata checks are retained. All outcomes still set `publication_authorized=false`; no release behavior is activated.

Four source-controlled `pytest` regressions cover foreign Wheel, foreign sdist, `SHA256SUMS` sidecar and an unreviewed subdirectory, each asserting a `BLOCKED` result and no publication authorization. The unchanged valid pair remains clean.

## Exact-source native Windows QA

- Dedicated, separate, task-owned sparse clone: `D:\\MedOrigin-Core-DistInventory-QA-20261103-2005`, source commit `91cfb9012dbeb4e61b955c5f6b7844b0bfa5a236`; no UI worktrees touched.
- Git blob IDs of tested production and test sources: `56cf05d365779ca679d7ba979f440dd6fe3e2249` and `fb564ea6cedf59244f02c9c3730ca440a2b2d084`.
- Python 3.14: **46/46 PASS**, 2.27 seconds, exit 0. Ruff check PASS, Ruff format --check PASS.
- Python 3.11.15: **46/46 PASS**, 2.15 seconds, exit 0.
- Python 3.12.13: **46/46 PASS**, 2.36 seconds, exit 0.
- Python 3.11 and 3.12 used already-installed interpreter builds plus **process-local** `PYTHONPATH` to reuse pure-Python `pytest 8.4.2` from Python 3.14 with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. These are genuine interpreter executions but **not fully isolated/installed per-version virtual environments**. No packages or network services were installed for the tests.

These 138 total individual pytest invocations qualify only this focused source-controlled test module, not the whole project, full multi-OS CI, a production Wheel+sdist or a reproducible packaged release.

## Residual gates / explicit NO-GO

No hosted exact-branch CI or independent #603 security review is claimed. Artifact enumeration does not eliminate time-of-check/time-of-use races; downstream immutable artifact binding and independent provenance checks remain necessary. Unapproved ADR-0045 and packaging/version policy #574, optional research extras and advisories #622, and desktop OS-specific #662/#673/#676 remain unresolved. No main merge, reviewer bypass, installer, tag, signing, public package, PHI/EHR, telemetry, model-training, paid service, or clinical distribution is authorized.

**Release status:** `NO-GO`; `publication_authorized=false`.