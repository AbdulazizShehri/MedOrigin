# MedOrigin Core — Prepublication architecture decision and evidence ledger

- **Prepared:** 2026-10-23
- **Status:** **DECISION REQUIRED / DO NOT PUBLISH**
- **Purpose:** An inspectable, source-specific handoff for release preparation. It is
  **not** acceptance of ADR-0044, a release candidate approval, or authorization to tag.
- **Release tracker:** [#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574)
- **Proposed packaging:** [DRAFT PR #598](https://github.com/AbdulazizShehri/MedOrigin/pull/598)
- **Competing unmerged root mutation:** [PR #597](https://github.com/AbdulazizShehri/MedOrigin/pull/597)
- **Decision record:** [ADR-0044](../adr/0044-isolated-core-release-projection.md) **PROPOSED**
- **Binding policies:** Accepted ADR-0010, ADR-0011, ADR-0020, ADR-0030,
  [release process](release_process.md), and MRL-0809 research prerequisites

## The decision is architectural, not a CI override

Source root `pyproject.toml` SHA-256
`c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510`,
lock `uv.lock` SHA-256
`6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4`,
and historical MRL static prerequisites must **never be overwritten or weakened**.
A previous direct-root update in [PR #597](https://github.com/AbdulazizShehri/MedOrigin/pull/597)
failed eight frozen-research tests. Green packaging checks cannot reverse those
failures or authorize silently changing their expected identities.

| Proposed route | Benefits | Cost/risk | Current decision |
|---|---|---|---|
| **A. Successor frozen-root identity** | Source and public package metadata are identical after newly governed research-root succession | Requires separate immutable MRL prerequisite lineage, successor approval, and new source qualification; direct edit of old root is prohibited | Proposed in [successor decision dossier](successor_version_decision_574.md), **not adopted** |
| **B. Audited isolated Core projection** | Preserves frozen research source exactly, while staging only four canonical GitHub URLs and bounded sdist allowlist | Source metadata and projected distribution metadata differ; strict byte-pinned code, installer and sdist provenance must be upheld | [ADR-0044](../adr/0044-isolated-core-release-projection.md) and [PR #598](https://github.com/AbdulazizShehri/MedOrigin/pull/598) **proposed, unmerged** |
| **C. No successor package yet** | No change to distribution architecture or frozen evidence | No new public MedOrigin Core distribution | Safe default until a route is accepted |

**Required explicit founder decision:** accept B **as a transparent documented
distribution projection only**, or select A and authorize a separately scoped
successor research-root identity; otherwise retain C. Adoption of B must be
recorded by a new explicit Accepted-ADR decision; this file does not grant it.
The older [v0.3.0 compatibility policy](v0_3_0_compatibility_disposition_574.md)
prefers A, and must not be silently superseded by the newer unaccepted B.

## Exact evidence, with limits

| Check | Evidence | Current interpretation |
|---|---|---|
| Frozen dataset writes | [PR #602](https://github.com/AbdulazizShehri/MedOrigin/pull/602) merged as `dd84bb7b4177fbc169a04370772610ec66fa41df`; [postmerge CI 40006130451](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/40006130451) **success** | [Issue #601](https://github.com/AbdulazizShehri/MedOrigin/issues/601) closed; no migration or clinical authorization |
| Historical `v0.2.0` differential | Immutable tag target `d2e651a55c92f2218aca49acaa5b7bd18a75f096`; [synthetic old/new matrices in #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574#issuecomment-6372646966) | Old-on-new and new-on-old validation **fail** for the tested persisted format; current writers reject rewriting old artifacts and preserve their bytes |
| Core wheel Python membership, licenses, PEP 376 RECORD | [Source-bound verifier in draft #598](https://github.com/AbdulazizShehri/MedOrigin/pull/598) | Positive staged-artifact and negative forged-payload checks; limited to candidate commit and known payload |
| Install-time wheel controls | [Forged dependency and CLI negative receipt](https://github.com/AbdulazizShehri/MedOrigin/pull/598#issuecomment-6373117774), proposed head `7e18892fa0779422d94589f963a9de513e66055c` | Actual forged wheel was rejected after hardening; source root remained frozen |
| Candidate Core packaging | [Linux Python 3.11/3.12 qualification](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/40012022218) and [nonpublishing artifact round-trip](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/40012022457) **success** on `7e18892` | Build qualification **only**, not a license or release decision |
| Security | [CodeQL](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/40012022230) **success** on `7e18892` | CodeQL pass is not a substitute for independent architectural/security review |
| Full candidate CI | [CI 40012022243](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/40012022243) **in progress at this preparation snapshot** | Must reach full exact-head success, including eight pytest shards and two final quality jobs |
| Visual identity | [PR #595](https://github.com/AbdulazizShehri/MedOrigin/pull/595) | Separate founder visual acceptance; not a Core code-integrity fact |

## Gate to mark PR #598 *ready for architectural review*, not release

- [x] Preserve Git root metadata, lock and frozen MRL research manifest identities.
- [x] Stage from committed Git bytes and refuse changed source identity.
- [x] Prove sdist scope, source-bound wheel bytes, installer metadata, license
  matching, and clean installation through nonpublishing CI.
- [x] Document failed historical cross-version validation without rewriting
  old checksum or fingerprint evidence.
- [ ] Full exact-head CI including both quality aggregates returns **success**.
- [ ] Independent review of source-to-artifact trust boundaries and distribution
  mechanics is recorded; CodeQL alone does not fill this role.
- [ ] **Founder explicitly accepts or rejects ADR-0044**, resolving the older
  successor-root preference and ruling on whether PR #598 may merge.

## Distinct later publication gate — intentionally not authorized

Even if an architecture is accepted and its PR eventually merges, these
remain **separate**: authorized Core semantic version, applicable public API /
persisted-format compatibility statement, no in-place historical migration,
correct successor citation and changelog, final source+artifact evidence on
the release SHA, all required rights and notices, clear synthetic-only/
no-PHI/no-production-EHR/no-clinical-validation scope, operator tag approval,
and CI-publisher approvals. Release publication must not be activated by a
draft PR, a green CI run, a merge, or this ledger.

**Current disposition:** `SOFTWARE_PREPUBLICATION_PROTOTYPE`,
`publication_authorized = false`. Do not issue a tag, GitHub Release,
TestPyPI/PyPI/Hugging Face upload or clinic-facing deployment.
