# ADR-0045 — Proposed: source-bound base-only distribution projection

**Status: Proposed / NOT ADOPTED**

**Date:** 2026-10-25

## Background and actual issue

ADR-0044 is **Accepted** by the founder for **route B**: a read-only
packaging projection whose approved changes are limited to the four named
Project-URLs plus bounded sdist inclusion and independently verified
provenance. It does **not** authorize dependency-metadata transformations.

The exact `medscale 0.3.0` Developer Beta Wheel has no unconditional
runtime dependencies, and the installed synthetic Core has passed Python
3.11/3.12 qualification. However its **optional** research/training extras
advertise pinned `pillow==12.3.0` and `accelerate==1.14.0` with known
upstream security advisories. See [Issue #622](https://github.com/AbdulazizShehri/MedOrigin/issues/622).

The new publisher fail-closed guard rejects publication of either the
Wheel or sdist if any `Provides-Extra`, `Requires-Dist` or unqualified
dynamic dependency metadata remains. That is deliberate: the original
unpublished Core Wheel/sdist and historical QA ZIP remain source-qualified
technical artifacts, **not approved public release artifacts**.

## Proposed alternative (not an owner decision)

Stage the exact immutable source through the already accepted ADR-0044
projection, then create **another, explicitly labelled, never-published
scratch staging tree** with exactly one further transformation:

- Remove the entire uniquely identified
  `[project.optional-dependencies]` TOML block.
- Preserve the remaining parsed TOML mapping byte-for-byte except for the
  already approved ADR-0044 URL rewrites and bounded sdist scope.
- Preserve all source files, licenses, historical MRL assets, canonical
  `pyproject.toml`, `uv.lock` and v0.2.0 receipts **unchanged**.
- Bind the removed section to its exact known SHA-256
  `8c0db866843e15ec75b764dfff4b4d983856d1e2c6f95f4427f576427e54378a`.
  Fail closed on unknown section, unexpected TOML changes or pre-existing
  destination.
- Emit the proposal provenance as canonical UTF-8 JSON with **LF** line
  endings on all platforms (including Windows), avoiding needless
  cross-platform sdist hash differences caused by newline translation.
  Use a **different** provenance schema:
  `MEDORIGIN-CORE-BASE-ONLY-PROPOSAL-1`, with old and new metadata hashes,
  exact Git source commit, original frozen research identities, and
  `adr_0044_amendment_accepted=false`,
  `independent_security_review_completed=false`, and
  `publication_authorized=false`.

Script: `scripts/stage_medorigin_base_only_proposal.py`.
This script does not create releases, push Git, build models or change
protected main. It uses only the standard library and the existing,
immutable-source ADR-0044 stage implementation.

## Qualification required before any adoption or actual release

A green base-only metadata gate is a **necessary but insufficient**
condition:

1. Founder explicitly approves an **ADR-0044 amendment** to permit exactly
   this isolated dependency-metadata deletion. This ADR currently remains
   PROPOSED. Do not infer authorization from route B alone.
2. Review whether the publicly exposed package/version must be changed
   (for example a new `0.3.1` version), and declare the unchanged
   `medscale` CLI/import compatibility explicitly.
3. Create **new**, provenance-bound Wheel and sdist in isolated environments
   with recorded toolchain versions, content hashes, and byte-for-byte
   source comparisons; never reuse earlier v0.3.0 artifact SHA or CI
   qualifications.
4. Extend/adapt existing Wheel/sdist publication verifiers to explicitly
   validate the **new** provenance schema, its permitted transformation and
   publisher boundary. Current original-source verifiers may correctly
   reject the new variant; bypassing them is not approval.
5. Repeat cross-platform Python 3.11/3.12 offline installation, synthetic
   FHIR E2E, hostile archive controls, CodeQL, free dependency advisory
   checks, redistribution/licensing review and independent #603 review.
6. Preserve all release gates and operator opt-ins. No protected-main
   merge, tag, GitHub Release, TestPyPI/PyPI upload, Desktop installer or
   deployment is authorized by this proposal.

## Rejected shortcuts

- Editing research `pyproject.toml` or `uv.lock` in place.
- Silently upgrading pinned extras and claiming old scientific evidence
  applies.
- Publishing the old Wheel while hiding risk in documentation.
- Treating green unit tests, Bandit, Playwright, CodeQL or author inspection
  as independent #603 signoff.
- Calling a metadata-only proposal an approved signed desktop product.

**Decision remains PENDING.** Technical feasibility experiments may be run
locally for review evidence, but cannot convert this proposal to Accepted
without an explicit founder decision.
