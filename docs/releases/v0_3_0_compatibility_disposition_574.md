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
The four old `TheHalfMoon/MESC` project URLs presently redirect to the
canonical MedOrigin repository identity. Keep them as a **disclosed temporary
limitation in this unpublished source candidate only**.

For an official, truthfully branded future distribution, use a *separately
governed successor root-input identity*: preserve original research manifests
and hashes, document predecessor/successor lineage, edit the metadata on a
new scoped branch, and qualify the exact source plus wheel/sdist again.
Do not use a hidden wheel metadata overlay or rewrite frozen inputs in place.

Read-only root-identity preflight: `python scripts/audit_successor_package_metadata_574.py`
checks the original SHA-256 of both frozen root inputs and the immutable v1/v2
MRL-0809 prerequisite manifests, and calculates the *in-memory only* successor
`pyproject.toml` SHA-256 after replacing exactly four legacy `Project-URL` lines.
The proposed new URL base is `https://github.com/AbdulazizShehri/MedOrigin`, reflecting the completed native repository transfer; predecessor URLs are observed only to verify the unaltered frozen input.
It fails closed if any prerequisite has drifted and does **not** write files,
modify manifests, reconcile research authority or grant a tag/release. This
preflight is valid only against an archived copy of the frozen old root; a
future approved successor root requires separately governed source lineage.

## Qualification versus publication

Source candidate `medscale 0.3.0` retains the `medscale` import and CLI,
with existing Workspace distribution independently versioned. Exact-head CI,
CodeQL, installed-wheel, security and synthetic CLI E2E evidence may qualify
the source for review or protected merge. They do not authorize a Git tag,
GitHub Release, TestPyPI/PyPI/HF distribution, clinical deployment or science
claims. Explicit separate operator release/tag approval is still required.
The dataset migration and root metadata reconciliation remain public-release
gates, not tasks silently completed by this policy.
