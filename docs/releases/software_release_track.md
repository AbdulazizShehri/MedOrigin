# MedOrigin — Synthetic-only Software Release Track

- **Status:** Founder-prioritized planning / release-candidate qualification track; not a publication approval
- **Direction date:** 2026-10-16
- **Tracking:** [Issue #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574)
- **Successor version decision:** [Proposal and frozen-input impact dossier](successor_version_decision_574.md) — requires independent founder approval; no authorized new version or tag
- **Authority:** [ADR-0010](../adr/0010-release-architecture.md), [release process](release_process.md), [R1–R7](../governance/rules.md), and canonical specifications continue to govern; this document cannot override them

## Why there are two lanes

A blocked GPU runtime-feasibility experiment is not, by itself, a defect in the downloadable Python research tooling. The Founder directed the team to qualify a **synthetic-only developer software release** separately from claims about real scientific model performance or clinical suitability.

**Lane A — Software release candidate:** qualify and document source, the existing `medscale` Python package/CLI and any separately installable synthetic Workspace developer interfaces as they actually exist. Passing tests is necessary but not enough: verify the artifact installed in a clean environment, compatibility, trust boundaries, licensing, release CI and reproducibility.

**Lane B — Research and clinical:** MRL-0809, MRL-0899, real GPU candidate feasibility, experiments, training/model promotion, clinical pilots, PHI and real-world evaluation remain separate and unmet unless their own canonical evidence gates are proven. The Colab T4 memory failure and proposed Kaggle follow-up in [#429](https://github.com/AbdulazizShehri/MedOrigin/issues/429), [#450](https://github.com/AbdulazizShehri/MedOrigin/issues/450), and [#545](https://github.com/AbdulazizShehri/MedOrigin/issues/545) do not block **planning or validating Lane A**. They still block any scientific-execution-readiness claim.

A **shared security, licensing, integrity, PHI/no-backflow, or build defect** discovered while pursuing either lane can block the software candidate. Separate lanes are not an exemption from necessary engineering checks.

## Truthful deliverable boundary

The first proposed deliverable is a **developer-oriented, offline, synthetic-only Python software candidate**, not a clinician-facing product:

- MedOrigin is the public repository/project identity; `medscale` remains the intentionally preserved package/CLI namespace until a separately qualified compatibility migration.
- Research Core: existing evidence, reproducibility, benchmark, provenance, and FHIR boundary *software*. Implementation does not establish scientific accuracy or model superiority.
- Clinical Workspace: an **independently buildable and installed-wheel-tested** local Python/synthetic offline shell and APIs under `apps/workspace/`, verified on Python 3.11/3.12 on Windows and Linux (see [installation and evidence](developer_package_install.md)). This is package installability, **not** evidence of a clinician UI, production protected-key provider, clinical readiness or an authorized public distribution.
- There is **no completed general-purpose desktop/web GUI**, approved PHI ingestion, production clinical deployment, autonomous medical diagnosis, or live EHR write flow. Do not present a developer source preview as an application deployed for clinicians.
- No scientific corpus, sealed Tier-3 material, real patient data or workspace-to-research training/evaluation backflow.

The historical `v0.2.0` tag and its [release record](../../RELEASES.md) are immutable. A new version/tag must be selected and independently qualified before a new release is declared.

## Candidate gates (not yet satisfied by this document)

The tracker records concrete execution evidence, not optimistic checkmarks. Keep every item **open** until the linked exact-head results exist.

1. **Scope and dependency closure:** reconcile the normal protected merges of FHIR input-safety [#568](https://github.com/AbdulazizShehri/MedOrigin/pull/568) and strict Workspace MyPy [#569](https://github.com/AbdulazizShehri/MedOrigin/pull/569). [#464](https://github.com/AbdulazizShehri/MedOrigin/issues/464) package-version single-sourcing and the centralized `SYNTHETIC` constant **are already implemented on main** (68 focused tests passed on 2026-10-16); do not duplicate their repair. Preserve the frozen research root files.
2. **Exact artifact and version:** decide an authorized successor package version and compatible Workspace source/packaging scope; preserve `v0.2.0`. If a package-version update requires frozen research inputs (`pyproject.toml` / `uv.lock`), obtain and record the explicit evidence reconciliation **before** editing them.
3. **Offline shell and installed-artifact journey:** Core and Workspace independently pass preliminary clean-wheel imports/CLI/synthetic-shell smokes on Python 3.11/3.12 ([commands and bounded evidence](developer_package_install.md)); Workspace has a read-only GitHub-hosted Linux build + sdist + installed-wheel CI matrix. **Remaining:** qualify the *final versioned Core wheel and sdist* through the [exact-artifact release workflow](../../.github/workflows/release.yml) and protected final-head/tag tests, with version/CLI identity and immutable receipts. No claim of independent clinical app or network-free installation.
4. **Trust and quality:** require full protected exact-head CI (including both Python quality jobs and all shards), CodeQL, applicable optional-extras/packaging checks, licenses/attributions, credentials and no-network boundaries, no-PHI/no-backflow contract tests, and review-thread resolution.
5. **Reproducibility and documentation:** record candidate commit/tree, source-derived version, immutable artifact hashes, build environment, relevant CI/release qualification links and limitations; publish install/reproduce steps and a clear synthetic-only safety disclaimer. A release document with missing receipts is `NOT_QUALIFIED`.
6. **Explicit release decision:** submit the documented candidate for founder/operator authorization under ADR-0010 and R5/R6, then use the qualified **CI-only GitHub Release** tag/artifact path if approved. TestPyPI, PyPI, Hugging Face, hosted docs and external mirrors remain **separately configured and approved**; do not enable distribution automatically.

### Evidence and status vocabulary

| State | Meaning |
| --- | --- |
| `SOFTWARE_WORK_IN_PROGRESS` | Software implementation/qualification incomplete |
| `SOFTWARE_CANDIDATE_QUALIFIED` | Exact source, artifact, quality, release-path and limits recorded; no tag/publication claim |
| `SOFTWARE_RELEASED` | Explicit release authority + immutable tag/GitHub artifact + actual CI publication receipts |
| `SCIENTIFIC_NOT_QUALIFIED` | Real-experiment/model-performance gate incomplete, regardless of software delivery |
| `CLINICAL_NOT_AUTHORIZED` | Real patient/PHI, EHR writes and clinical deployment explicitly excluded |

These labels are human-readable planning vocabulary **only**, not a replacement for canonical machine-state evidence or adopted task statuses.

## Non-grants and preservation

```text
NEW_GPU_OR_PAID_COMPUTE = NOT_AUTHORIZED
SCIENTIFIC_MODEL_EXECUTION = NOT_AUTHORIZED
TRAINING_OR_WEIGHT_MUTATION = NOT_AUTHORIZED
SEALED_TIER3_OR_PHI_ACCESS = NOT_AUTHORIZED
CLINICAL_PILOT_OR_PRODUCTION = NOT_AUTHORIZED
EHR_WRITE = NOT_AUTHORIZED
MODEL_PROMOTION_OR_EFFICACY_CLAIM = NOT_AUTHORIZED
TAG_OR_RELEASE_PUBLICATION = SEPARATE_EXPLICIT_APPROVAL_REQUIRED
FROZEN_RESEARCH_EVIDENCE_MUTATION = NOT_AUTHORIZED_BY_THIS_DOCUMENT
```

This track does not modify ADR-0038, CW-020/021 authorization, MRL task states, scientific protocol freeze, artifact provenance or existing historic releases. A package candidate is **not** research completion, clinical qualification, or a substitute for user-facing product engineering.
