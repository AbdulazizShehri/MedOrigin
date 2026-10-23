# ADR-0044 — Explicit isolated Core release packaging projection

- **Status:** Proposed — founder adoption required before this packaging route can replace the existing one
- **Date:** 2026-10-23
- **Scope:** Prepublication packaging architecture only; no release, no model training, no clinical use
- **Tracking:** [Software release Issue #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574)
- **Alternative:** [Unmerged successor-root proposal PR #597](https://github.com/AbdulazizShehri/MedOrigin/pull/597)

## Problem observed, not theorized

A direct change to the frozen root `pyproject.toml` makes the package URLs
correct but breaks the MRL-0809 research prerequisite gate. The draft
successor-root candidate in PR #597 produced eight failing frozen-research
tests on GitHub even though its source wheel and sdist could be built.
Changing those test expectations or old evidence to force green CI would be
scientifically incorrect.

An unrestricted Hatchling sdist also attempted to package deeply nested
research receipts on Windows, leading to a real long-path build failure.
A package containing those research artifacts would not be appropriately
scoped for a developer-preview distribution.

## Proposed alternative — declared projection with byte-level provenance

Keep `pyproject.toml`, `uv.lock`, all frozen MRL manifests, retained
training/research evidence, historical version tags, and import namespaces
**unchanged** in the source repository.

The read-only `scripts/stage_medorigin_core_projection.py` makes an
isolated distribution source directory from **`git archive HEAD`**, not
uncommitted working-tree source:

1. Reject any Git source whose root, lock, or MRL-0809 v1 manifest byte SHA
   differs from the frozen historical contract.
2. Copy exactly tracked `src/medscale` source, README, LICENSE,
   THIRD_PARTY_NOTICES, and identical `apps/workspace/LICENSE` bytes.
3. In the **separate package staging tree only**, change exactly the four
   known obsolete Project-URL values to `AbdulazizShehri/MedOrigin` and
   add an explicit Hatchling sdist allowlist. No source Python files or
   dependency constraints are rewritten.
4. Emit `MEDORIGIN_SOURCE_PROVENANCE.json` in the sdist, containing exact
   Git commit, SHA-256 for every copied source file and the two root metadata
   identities, with `publication_authorized: false`.
5. Verify the actual archive has only allowed payloads; rehash its source
   bytes against the receipt; reject missing notices, links, path traversal,
   non-Core Workspace code, research payloads, and out-of-budget inputs.
6. Build and inspect actual `medscale 0.3.0` wheel and sdist, unpack sdist
   and rebuild wheel, clean-install and test CLI in non-source venvs.
7. Keep this lane **separate from tag-triggered release workflows** until
   ADR acceptance and an additional explicit publication authorization.

The source Git repository and the package-stage `pyproject.toml` deliberately
have different hashes; the transformation is published in source control
and the receipt. This is neither a concealed overlay nor a pretense that the
historical frozen project metadata contained the new URLs. Research gates
continue to validate their original source identity and remain fail-closed.

## Known limits and decision needed

This approach duplicates a *minimal*, bounded packaging metadata surface.
It cannot by itself establish full API compatibility with v0.2.0, clinical
qualification, redistribution rights for optional extras, release tagging
permission, or scientific reproducibility for new experiments.

**Decision:** Accept this auditable packaging boundary as a successor software
distribution lane, or reject it and separately authorize a new research-root
identity with appropriate scientific migration. Do not merge PR #597's
root-metadata mutation simply to bypass frozen research gates.

**Until this ADR becomes Accepted:** this implementation is an experimental
read-only qualification prototype, not an adopted publisher workflow.
It creates no tag, GitHub Release, package-index upload or deployment.
