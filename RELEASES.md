# MedOrigin Release History

## MedOrigin v0.3.2 — Corrective Release & Native Desktop Distribution

- **Release date:** 2026-11-20
- **Tag:** `v0.3.2`
- **Python:** 3.11, 3.12
- **Governance Track:** Lane A (Synthetic-Only Developer Software Track — QUALIFIED)
- **Scientific Invariants:** Lane B (MRL-0809/0899 `SCIENTIFIC_NOT_QUALIFIED`, frozen root intact)
- **Clinical Boundaries:** Lane C (CW-021 `CLINICAL_NOT_AUTHORIZED`, zero PHI, zero live EHR)

### Highlights
- **Full Release CI/CD Workflow Qualification**: Fixed shallow clone checkout in `.github/workflows/release.yml` with `fetch-depth: 0`, enabling automated end-to-end `quality gate` and `build artifacts` qualification on tag push.
- **Canonical `medorigin` CLI**: Added `medorigin` command dispatcher alongside `medscale` for forward brand alignment.
- **Desktop D2 Native Packaging**: Native 64-bit Windows setup installer (`MedOrigin-Synthetic-Private-Setup-windows-x86_64.exe`) and portable ZIP archive (`MedOrigin-Synthetic-D2-windows-x86_64-<hash>.zip`).
- **Complete 28-Screen Functional Audit**: Comprehensive verification across all 28 clinical feature screens with WCAG AAA accessibility, dark/light themes, and fail-closed process supervision.
- **ADR-0045 Base Core Projection**: Releases clean base Core wheel and sdist with zero optional research extras and zero runtime third-party dependencies.

---

## MedOrigin v0.3.1 — SUPERSEDED by v0.3.2

> [!NOTE]
> Tag `v0.3.1` was created on canonical `main` at commit `4d2a3d30b68577a78b863094e869b70724164b81`. During the automated tag release run (`44814588191`), the `quality gate` job failed because `actions/checkout` used default shallow clone (`fetch-depth: 1`), causing git-based machine state admission tests to fail on missing `refs/remotes/origin/main`. In accordance with ADR-0010 and founder directives prohibiting tag reassignment or binary replacement, tag `v0.3.1` is preserved immutably and superseded by `v0.3.2`. Full incident documentation in `docs/releases/v0_3_1_workflow_parity_incident.md`.

- **Release date:** 2026-11-20
- **Tag:** `v0.3.1`
- **Python:** 3.11, 3.12
- **Governance Track:** Lane A (Synthetic-Only Developer Software Track — QUALIFIED)
- **Scientific Invariants:** Lane B (MRL-0809/0899 `SCIENTIFIC_NOT_QUALIFIED`, frozen root intact)
- **Clinical Boundaries:** Lane C (CW-021 `CLINICAL_NOT_AUTHORIZED`, zero PHI, zero live EHR)

### Highlights
- **Canonical `medorigin` CLI**: Added `medorigin` command dispatcher alongside `medscale` for brand alignment.
- **Desktop D2 Native Packaging**: Native 64-bit Windows setup installer (`MedOrigin-Synthetic-Private-Setup-windows-x86_64.exe`) and portable ZIP archive (`MedOrigin-Synthetic-D2-windows-x86_64-<hash>.zip`).
- **Complete 28-Screen Functional Audit**: Comprehensive verification across all 28 clinical feature screens with WCAG AAA accessibility, dark/light themes, and fail-closed process supervision.
- **ADR-0045 Base Core Projection**: Releases clean base Core wheel and sdist with zero optional research extras (`pillow`, `accelerate`) and zero runtime third-party dependencies.
- **CI/CD Hardening**: Resolved pytest collection errors in release workflow by provisioning workspace dependencies, and upgraded Actions to pinned versions (`setup-uv@v10.3.3`, `action-gh-release@v3.0.4`).

---

## MedOrigin v0.3.0 — RETRACTED / SUPERSEDED by v0.3.1

> [!WARNING]
> **Status: RETRACTED / SUPERSEDED by v0.3.1**
> Tag `v0.3.0` was published manually following an incomplete CI workflow run (`44780707812`) where test collection failed due to missing test dependencies in `release.yml`. Uploaded artifacts prematurely included `medscale_workspace-0.1.0.dev1-py3-none-any.whl` (outside approved base Core candidate qualification) and omitted native desktop installers. Per ADR-0010 (`docs/releases/artifact_lifecycle.md`), assets and Git tag remain preserved immutably for citation integrity (R7), with `v0.3.0` formally superseded by corrective release `v0.3.1`. Full incident report: `docs/releases/v0_3_0_incident_containment.md`.

- **Release date:** 2026-11-20
- **Tag:** `v0.3.0`
- **Tagged commit:** `88f5fc1f4749694ff99548ae69a9f9478655424c`
- **Successor:** `v0.3.1`

---

## MedScale v0.2.0 (Historical)

This is an **historical MedScale v0.2.0 release**, before the MedOrigin repository rename. Existing tag names, built artifacts and original source provenance are preserved. See [MedOrigin identity policy](docs/BRAND_TRANSITION.md).


- **Release date:** 2026-07-13
- **Tag:** `v0.2.0` (existing annotated tag)
- **Tagged commit:** `d2e651a55c92f2218aca49acaa5b7bd18a75f096`
- **Python:** 3.11, 3.12
- **Historical release qualification:** ruff PASS · mypy PASS · pytest 340/340 PASS

These notes describe the v0.2.0 release baseline. Later repository hardening is not retroactively presented as evidence that it ran on the tag.

## Highlights

- Complete v0.2 milestone set: M1 release engineering, M2 evidence infrastructure, M3 benchmark framework, Dataset v1, S0 stabilization, M4 optional backends, M5 FHIR boundary, and M6 collaboration workflow.
- Deterministic, content-addressed, local-first research intelligence platform with architecture-enforced boundaries.
- Optional backends (`transformers`, `llama.cpp`) isolated behind extras and dedicated qualification.
- FHIR boundary frozen to deterministic `ValidationReport` contracts with optional local validator integration.
- Multi-reviewer collaboration workflow with append-only logs, deterministic merge, conflict visibility, and PRISMA replay.

## New capabilities

### Release engineering

- Structured logging, release workflow, coverage enforcement, storage hygiene checks, and architecture enforcement.

### Evidence infrastructure

- `medscale.evidence` subpackage with frozen models, grading, protocol, and backward-compatible shim.
- Evidence store and checks packages isolated from `litdb`.

### Benchmarks

- Deterministic benchmark spec, task contract, frozen scorers, and artifact-first replay.
- Five frozen run identities: `spec_id`, `snapshot_id`, `software_version`, `git_sha`, `scorer_version`.

### Dataset v1

- Deterministic manifest, schema, and seed-42 content-hash split.
- Sibling `.sha256` checksums and metadata/license enforcement.

### FHIR boundary

- `medscale.fhirkit` package with `ValidationReport`, deterministic serialization, and content-addressed storage.
- Optional local validator boundary with explicit install guidance when the dependency is unavailable.

### Collaboration workflow

- Reviewer-scoped append-only JSONL logs with hash chaining.
- Deterministic merge by timestamp ordering with conflict visibility.
- PRISMA reproducibility from merged reviewer logs.

## Quality at the v0.2.0 baseline

- 340 deterministic tests.
- Ruff, strict Mypy, Pytest, and coverage green in the release qualification recorded for the baseline.
- Optional extras isolated.
- Architecture tests enforce dependency boundaries.

## Current repository release automation

The repository now contains `.github/workflows/release.yml`. On a `v*` tag push it runs a quality gate, builds wheel/sdist artifacts, and can create a GitHub Release from those artifacts. On pull requests that modify the workflow it also performs a PR-safe build/upload/download byte-identity qualification. All referenced third-party Actions in that workflow are SHA-pinned.

The current CI configuration also enforces a coverage floor. These are current repository facts; this section does not claim that every later workflow revision ran against the historical v0.2.0 tag.

## Known limitations of the v0.2.0 release baseline

- ADR-0023, ADR-0024, and ADR-0025 formal registry entries were deferred at the release baseline.
- `Snapshot` alias was not declared in `workspace.py` `__all__` at the release baseline (TD-001).
- The adapter layer used `urllib` for live retrieval; core paths remained offline-only.
- A `v0.2.0` tag exists, but this document does not claim a GitHub Release object was retroactively created for it.

## Tag status

`v0.2.0` already exists. Do not recreate, move, or replace the tag as part of documentation reconciliation.
