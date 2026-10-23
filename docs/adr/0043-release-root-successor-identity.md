# ADR-0043 — MedOrigin Release Root Successor Identity

- **Status:** Proposed — requires independent founder adoption before protected merge
- **Date:** 2026-10-23
- **Scope:** Packaging / developer release preparation only, not research execution
- **Tracking:** [Issue #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574)
- **Evidence:** [Candidate lineage manifest](../releases/successor_root_identity_candidate_20261023.json)

## Context

The existing Core root `pyproject.toml` is a frozen MRL-0809 static-prerequisite
input (SHA-256 `c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510`).
Its package `Project-URL` metadata points at a historical GitHub repository.
This is acceptable only in archived, nonpublished source research. A new MedOrigin
release must advertise `AbdulazizShehri/MedOrigin` truthfully.

Building the pre-successor sdist on Windows also traversed non-package research
artifacts and failed due to an extremely long filename. This would be a risky
redistribution policy even on platforms where it builds.

## Proposed decision

1. Keep all frozen MRL manifests, historical research records and tags
   **byte-identical and addressable via their original Git commit identity**.
2. Treat the amended root `pyproject.toml` as a **new successor source identity**,
   not as an in-place repair of the predecessor. Record both root digests, the
   unchanged lockfile digest and predecessor manifest identity in a new append-only
   candidate record. Never change the legacy manifest to claim the new root is
   equivalent to the old one.
3. Keep the current `medscale 0.3.0` distribution/import/CLI compatibility for
   the developer-only candidate. Fix its four public package URLs to the actual
   repository. Confirm source wheel and rebuilt-from-sdist wheel use those URLs.
4. Allowlist sdist to `src/medscale`, README, LICENSE and THIRD_PARTY_NOTICES.
   Retain research protocols and receipts in the Git repository, not package bytes.
   No dynamic metadata substitution, archive rewriting, concealed dependency or
   bypass of release CI is permitted.
5. Run full exact-head protected CI, CodeQL, clean installation on supported
   Python versions, deterministic negative tests and licensing/provenance checks.

## Consequences / limits

The old MRL-0809 static prerequisites still refer to predecessor Git bytes; a new
experiment cannot silently reuse a successor root as that old identity. Research
gates remain separate, pending explicitly adopted successor experiment receipts.

This ADR is a **proposal**, not yet an Accepted decision. A draft PR can qualify
the successor bytes, but do **not** merge or tag until this architectural change
is independently approved per R6. Even an approved merge is not approval to
publish; R5 and separate release/tag/publisher gates remain mandatory.

No PHI, clinical use, GPU science claim, model promotion or public distribution
is within this decision.
