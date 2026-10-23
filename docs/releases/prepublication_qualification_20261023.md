# MedOrigin — Read-only software prepublication qualification

**Assessment date:** 2026-10-23
**Target:** Synthetic-only developer source/wheel candidates, **not** a clinician-facing product
**Authority:** [Issue #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574), ADR-0010, published release process
**Status:** **NO-GO for public package publication.** Research/clinical readiness is not inferred from package tests.

## Qualified technical scope

- Research Core: source version `medscale 0.3.0`; built a real wheel and clean-installed it in an isolated Python 3.14.7 environment outside the repository. Import, installed version and `medscale --version` succeeded.
- Clinical Workspace: `medscale-workspace 0.1.0.dev1`; built an independent wheel with canonical public project URLs, then clean-installed it with `cryptography==50.0.1` in a separate Windows Python 3.14.7 environment. Import, installed version and synthetic-only offline shell succeeded with `{"application":"medscale-workspace","data_class":"SYNTHETIC","mode":"offline-shell","ready":true}`.
- Root test and research inputs `pyproject.toml` and `uv.lock` remained byte identical to the frozen research source contracts. Historical provenance was not regenerated, and no version tag/release or package index operation occurred.
- Updated the tagged-release installed-wheel URL guard to the **current** public owner `AbdulazizShehri/MedOrigin`. It is still a fail-closed publication blocker, not a workaround. The standalone `scripts/inspect_release_wheel_metadata.py` audits the actual candidate wheel ZIP bytes with no network or write to source. The verified `pypa/gh-action-pypi-publish` v1.14.3 GitHub commit remains behind preexisting explicit publisher and environment gates.

## Exact isolated Windows evidence

These are **unpublished local test-build hashes**, not universal/cross-platform reproducibility claims. Base protected main at assessment: `e2e5fd9e0c746e031683dd0978a76b629dffe8b2`.

| Candidate wheel | Windows SHA-256 | URL metadata check |
| --- | --- | --- |
| `medscale-0.3.0-py3-none-any.whl` | `b1259032d3db0a106eaf82907c1ddbe1dcc1a1a15c287f58c676bfea5a95ae6e` | **BLOCKED:** all four stale project URLs |
| `medscale_workspace-0.1.0.dev1-py3-none-any.whl` | `643e3d10bfd41d57761842c6152538ab88fa13265a86af5dcf5c3c656a97c574` | **METADATA_QUALIFIED_ONLY:** four canonical URLs |

**Frozen source checksums, unchanged:** `pyproject.toml` = `c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510`; `uv.lock` = `6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4`.

Windows Python 3.14 evidence complements but does not substitute for exact new-head hosted Linux/Windows 3.11/3.12 CI qualification.

## Reproduce metadata preflight without a release

```bash
uv build --wheel --out-dir .release-readiness-evidence/dist
python scripts/inspect_release_wheel_metadata.py \
  --wheel .release-readiness-evidence/dist/medscale-0.3.0-py3-none-any.whl \
  --expected-version 0.3.0
# Exit 2 = intentionally BLOCKED until a governed canonical successor source exists.

uv build apps/workspace --wheel --out-dir .release-readiness-evidence/workspace-dist
python scripts/inspect_release_wheel_metadata.py \
  --wheel .release-readiness-evidence/workspace-dist/medscale_workspace-0.1.0.dev1-py3-none-any.whl \
  --distribution medscale-workspace --expected-version 0.1.0.dev1
# Exit 0 means only wheel *metadata* is compliant, NOT publication permission.
```

The script always reports `publication_authorized: false` and never uploads artifacts.

## Remaining non-negotiable gates

1. **Core source identity reconciliation:** current root `pyproject.toml` embeds historical `TheHalfMoon/MESC` public URLs. A fresh MedOrigin-branded release cannot use those bytes. Do not mutate a frozen prerequisite without an adopted, immutable successor-root trust identity retaining prior evidence and independently verified source/lockfile/manifest lineage. Issue #574 and [successor decision](successor_version_decision_574.md) are authoritative. Rebuild and inspect the **actual installed** wheel after that authorized work.
2. **Future exact-release verification:** independent current-head Linux + Windows Python 3.11/3.12 wheel and sdist build/install, hash and dependency attestation, API/CLI/persisted-format compatibility, license notices, no-PHI/no-backflow, clean CI, CodeQL and necessary independent review.
3. **Publisher identity and explicit permissions:** review tag/version under ADR-0010/R5/R6. A tag, GitHub Release, PyPI/TestPyPI/Hugging Face and any publisher activation each need their own distinct authorization. Do **not** turn on `GITHUB_RELEASE_PUBLISH_ENABLED` or `TESTPYPI_PUBLISH_ENABLED` while this report is NO-GO.
4. **No clinical/scientific extrapolation:** MRL-0809/MRL-0899, GPU evidence, training, PHI, clinician-facing UI and clinical deployment remain separate and unqualified.

**Disposition:** Engineering release preflight is stronger and reproducible; **public release remains blocked**, intentionally, until those listed gates are evidenced. A clean publication preflight is not itself a release approval.
