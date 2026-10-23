# MedOrigin — Isolated Core prepublication packaging prototype

- **Date:** 2026-10-23
- **Status:** PREPUBLICATION PROTOTYPE; NO TAG, NO PUBLISH, NO CLINICAL APPROVAL
- **Proposed architecture:** [ADR-0044](../adr/0044-isolated-core-release-projection.md)
- **Why:** root-metadata edit in draft PR #597 caused actual frozen MRL-0809
  CI failures. This lane leaves old research inputs intact.

## What is real and what is not

The independent `scripts/stage_medorigin_core_projection.py` stages
MedOrigin Core from **tracked Git bytes**, not working-directory source.
It rejects changes to the pinned frozen root, dependency lock and historical
static manifest identities. The only projected metadata change is the four
canonical package URLs and the exact source archive allowlist.

The staged package includes a machine-readable provenance record with
per-file hashes for all archived source. The read-only
`scripts/check_sdist_publication_scope.py` verifies that record against
actual tarball contents, plus byte-identical Core/Workspace Apache-2.0
license files. It rejects hostile archives and extra research/Workspace
payloads. All outputs explicitly state publication is not authorized.

The canonical Research Core wheel stays named `medscale` version `0.3.0`
for compatibility; MedOrigin is the public project and GitHub repository name.
No rename of imported Python interfaces is asserted.

## Commands for independent qualification (without publishing)

```bash
source_dir="$(mktemp -d)"
python scripts/stage_medorigin_core_projection.py --out "$source_dir/core"
uv build --wheel --sdist "$source_dir/core" --out-dir "$source_dir/dist"
python scripts/inspect_release_wheel_metadata.py \
  --wheel "$source_dir/dist/medscale-0.3.0-py3-none-any.whl" \
  --expected-version 0.3.0
python scripts/check_sdist_publication_scope.py \
  --sdist "$source_dir/dist/medscale-0.3.0.tar.gz"
```

The PR-specific **Core release projection qualification** workflow adds
isolated Python 3.11/3.12 Linux builds, source-tarball round-trip and clean
installed-CLI tests. Existing full main CI must continue testing the
unchanged, frozen research source. This workflow has `contents: read`
permissions only, no publisher or package upload jobs.

## Evidence boundaries

Local Windows staging of the current main source produced a valid Core wheel,
a bounded sdist, and a successful metadata check without root mutation.
Adversarial archive and source-projection tests additionally passed locally.
Exact-head GitHub checks are needed before calling the proposed implementation
qualified. Neither those checks nor a merge would authorize a public release.

**No UI is required for the standalone Python research Core to be built,
but a general-purpose clinician-facing desktop application is not supplied.**
A separate production clinical validation and desktop UI program remains out
of scope for this release-preparation request.

The competing direct-root proposal [PR #597](https://github.com/AbdulazizShehri/MedOrigin/pull/597)
is intentionally unmerged because it disrupts historical science contracts.
