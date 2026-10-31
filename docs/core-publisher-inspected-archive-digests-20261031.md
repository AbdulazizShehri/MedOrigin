# Publisher scope — inspected private archive SHA-256 evidence (2026-10-31)

**Status:** NONPUBLISHING, UNAPPROVED, DRAFT-ONLY. This is a *read-only* strengthening of the canonical Core publisher-scope checker. It does **not** adopt ADR-0045, independently validate artifact source against frozen Git, authorize a tag/release, publish a package, change the frozen research `pyproject.toml`/`uv.lock` or attest clinical use. Stack base is [Draft #776](https://github.com/AbdulazizShehri/MedOrigin/pull/776), immutable parent `da4832eda9877c7460ffef6af982de5d7247532f`. All data is synthetic.

## Contract and exact byte source

The checker returns `inspected_private_snapshot_sha256` with **two fixed keys**, `wheel` and `sdist`, only for `BASE_CORE_PUBLICATION_SCOPE_CLEAN`. Each value is a lowercase, 64-character SHA-256 digest computed in bounded 1 MiB streaming chunks from the **exclusive private Wheel/sdist archive copies whose bytes were parsed** by the checker. The existing POSIX dirfd/Windows native HANDLE acquisition and directory identity checks execute normally. The private files are deleted on context exit. A `BLOCKED` status always has an **empty object**; no positive digest may be interpreted as qualification of a refused artifact.

This evidence identifies bytes the *scope parser* saw. **It does not authenticate those bytes to the source Git tree**, to an approved repository release, a publisher identity, or to a later `dist/*` file open. It is not a signature or hash-based release authorization. `publication_authorized=false` and `independent_security_review_complete=false` are invariant regardless of hashes.

## Test-first proof and known follow-up risk

- **Expected RED before implementation:** source head `8deadaf9ec01537f06ba65a3b3b16dd7362e9a22` on [GitHub nonpublishing workflow #41218453108](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41218453108), Ubuntu3.11/3.12 test failures from missing `inspected_private_snapshot_sha256`. The positive, blocked and source-mutated cases all lacked the new field. This is a missing evidence-contract RED, **not an exploit proof**.
- **Positive synthetic case:** compare receipt Wheel/sdist digests with independent `hashlib.sha256` of the exact archive bytes supplied to the checker before any mutation; require `publication_authorized=false`.
- **Fail-closed negative:** disallowed optional `Provides-Extra` must result in `BLOCKED` with **no hashes**.
- **Important live POSIX mutation test:** after the original archive was copied to the private snapshot but while the metadata was parsed, overwrite the original Wheel with deliberately invalid synthetic bytes. The receipt still identifies the **old private snapshot** bytes, not the now-mutated pathname contents. This intentionally documents an unresolved risk: a later publisher opening the original path could use different bytes, even if the scope checker returned CLEAN. **Do not equate the receipt with an approval of the current or future original path.** A separate future publisher must use a pinned/verifiably identical artifact handoff before any publication can be considered. This is not remediated by adding a hash field alone.
- **Final exact-head qualification:** record the final SHA, full Windows/Ubuntu × Python 3.11/3.12 scope+Ruff matrix, and Windows/macOS/Linux installed Core parity links in PR discussion only once all have completed at that exact SHA.

## Outstanding release NO-GO

Owner/package identity and unapproved ADR #574; unresolved canonical optional research dependencies #622; independent source/artifact security review #603; actual Windows D1 WebView2 descendant network evidence #662; OS maintenance/accessibility #673/#676. No PHI, model inference, real EHR writes, clinical deployment, signed installer, protected-main merge, publication, package upload, or release.
