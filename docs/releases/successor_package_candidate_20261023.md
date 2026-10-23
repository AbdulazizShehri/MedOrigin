# MedOrigin — Proposed Successor Source / Prepublication Qualification

**Date:** 2026-10-23
**Status:** **PROPOSED, UNPUBLISHED, NOT MERGE-AUTHORIZED**
**Scope:** Developer-oriented Core `medscale 0.3.0` source/wheel; synthetic-only
**Authority required:** [ADR-0043](../adr/0043-release-root-successor-identity.md) approval under R6, and separately ADR-0010/R5 publication authorization
**Tracker:** [Issue #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574)

## Source identity lineage

This is a proposed **new package source identity**, not an alteration of the historical
MRL-0809 research prerequisite identity.

| Input | Immutable predecessor | Proposed successor |
| --- | --- | --- |
| Git base | `12d76bb7c560a204302b5b4e129644c54ae44f6f` | Review branch exact commit (record after GitHub checks) |
| Root `pyproject.toml` SHA-256 | `c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510` | `48bed28c9d366730f615de6f6d068e70dc78d39d600d6f3c70da247acc349310` |
| `uv.lock` SHA-256 | `6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4` | **Same exact bytes** |
| Frozen MRL-0809 v1 manifest SHA-256 | `7773967611e42c3d74338a1ec7c9004f661843df809865f6c6d455923fea89d1` | **Same exact bytes, NOT regenerated** |

Machine-readable proposed lineage:
[`successor_root_identity_candidate_20261023.json`](successor_root_identity_candidate_20261023.json).
The historical source hashes remain valid only for the historical Git inputs.
No experiment may silently claim the successor root matches those earlier inputs.

## Prepublication artifact tests actually executed

On Windows with `uv 0.12.19`, the source candidate was independently built as
**wheel + sdist**. The previous default sdist source traversal failed on a Windows
long-path research artifact; the successor limits the package to source code and
required notices rather than packaging unrelated research corpora.

| Artifact | SHA-256 | Qualification |
| --- | --- | --- |
| `medscale-0.3.0-py3-none-any.whl` | `be09d43669e8364423f8412227225a3d66b6f349f17166463dd6d5e2363dd437` | Actual wheel metadata: four canonical MedOrigin URLs |
| `medscale-0.3.0.tar.gz` | `5803d871d53d274fbbc2d3c74524076479bb174e39748282b04fbe20db92378a` | 256 entries; 3,196,387 uncompressed bytes; all allowlisted, notices included |

Actual sdist unpacked into a separate directory, rebuilt into a second clean wheel,
and passed metadata inspection with the **same** wheel SHA-256 as above. The
rebuilt wheel was installed without dependencies into two isolated local environments
**outside the source tree**: CPython **3.11.15** and **3.12.13**.
Installed import, `importlib.metadata.version("medscale") == "0.3.0"`,
`medscale --version`, and path-from-site-packages checks passed on each.

Read-only artifact tools: `scripts/inspect_release_wheel_metadata.py` and
`scripts/check_sdist_publication_scope.py`. The latter enforces path/size
limits and rejects research folders, tampered/malformed archives, and missing
license/notice files. Both tools return **publication_authorized: false**
even when their technical inspection passes.

## Not yet established

- The source lineage **has not been formally accepted** as a successor research
  input under ADR-0043; no historical manifest has been substituted or weakened.
- Hosted Linux/macOS/Windows 3.11/3.12 exact-PR-head full CI, CodeQL, release
  round-trip, compatibility and sdist audit must finish before merger.
- The historical v0.2.0 persisted-data migration decision is still intentionally
  fail-closed; see the bounded compatibility disposition.
- No new tag/versioned GitHub Release, package index upload, Hugging Face
  distribution, production EHR write, PHI, patient data, model training,
  clinical efficacy or scientific execution grant is provided.

**No publication performed.** An approved, technically qualified Git merge would
still be separate from explicit operator permission to publish.
