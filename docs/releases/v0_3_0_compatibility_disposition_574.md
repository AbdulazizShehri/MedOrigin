# MedOrigin v0.3.0 — bounded compatibility disposition

**Status:** Developer-preview engineering policy; no public distribution, release tag,
research execution or clinical authorization. See issue #574 and accepted ADR-0010,
ADR-0011, ADR-0017, ADR-0020 and ADR-0030.

## Historical data: immutable, no automatic migration

The historical v0.2.0 `dataset freeze` could emit a stale manifest checksum.
Our old/new validation matrix was not bidirectionally compatible. The new
source candidate must never use a successful re-freeze to conceal the
historical failure or rewrite evidence.

- Reject re-freeze of any checksummed or fingerprinted dataset, before writing.
- Fail closed on unreadable existing manifests. Preserve their original bytes.
- Permit a first freeze of an unsigned draft manifest and a new synthetic dataset.
- Do not automatically import, migrate, restamp, overwrite or downgrade old data.
  Existing invalid data remain read-only; validation must report their errors.
- A future migration requires a separately accepted append-only design with a
  new dataset identity, immutable source-byte digests, provenance linkage,
  identifier mapping and tests of both validator versions. No such migration
  is implemented or claimed by v0.3.0.

This is a limited engineering protection, not an assertion that historical
stored datasets are compatible.

## Package metadata: frozen-input isolation

Research qualification freezes the root `pyproject.toml` SHA256
`c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510`
and `uv.lock` SHA256
`6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4`.
The frozen source root still records four historical `TheHalfMoon/MESC`
Project-URLs and must not be edited in place. The **unpublished**
`medscale 0.3.0` Developer Beta in draft PR #598 qualifies an **explicit,
read-only packaging projection** under proposed [ADR-0044](../adr/0044-isolated-core-release-projection.md):
it copies committed source from `git archive HEAD` into a separate staging
directory, replaces exactly those four Project-URLs **in the staged distribution
metadata only**, and emits a source/projection provenance receipt. This is a
declared and audited transformation, **not a hidden metadata overlay** and not
evidence that the frozen root itself contained the new URLs.

For any **future public distribution**, #574 and #603 must first formally
resolve the architecture and package identity: either (a) independently review
and accept the bounded ADR-0044 projection with both source and staged
metadata hashes disclosed, or (b) approve a separately governed successor
root-input identity preserving historical research-manifest lineage. Reject
any silent root rewrite, unrecorded wheel repackaging, or claimed public
`MedOrigin` distribution while the installed package remains `medscale`.
Passing prepublication artifact checks authorizes neither a tag nor publishing.

## Qualification versus publication

Source candidate `medscale 0.3.0` retains the `medscale` import and CLI,
with existing Workspace distribution independently versioned. Exact-head CI,
CodeQL, installed-wheel, security and synthetic CLI E2E evidence may qualify
the source for review or protected merge. They do not authorize a Git tag,
GitHub Release, TestPyPI/PyPI/HF distribution, clinical deployment or science
claims. Explicit separate operator release/tag approval is still required.
The dataset migration and root metadata reconciliation remain public-release
gates, not tasks silently completed by this policy.
