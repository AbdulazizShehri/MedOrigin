# Nonpublishing Core archive handoff — exact private bytes (2026-10-31)

**Draft PR #778. Source-only proposal, no publication, no owner/ADR approval.** Stacked on Draft #777 (immutable parent `f2fd54e84ed8609db0455b654b8b9c6b1a3e84cc`). The real tagged release workflow still requires all prior owner, protected-main/tag governance, security, optional-extras and installed-wheel qualification checks. Changes to frozen canonical research `pyproject.toml`, `uv.lock`, MRL receipts, clinical deployment or training data are prohibited. No tag, release, external registry, PHI or EHR writes.

## Problem and staged byte handoff

The canonical Core publisher-scope reader gained SHA-256 of the two privately inspected Wheel/sdist copies in #777, but a later `actions/upload-artifact` or GitHub Release job would reopen `dist/*` after the checker returned, potentially using different bytes. A correct digest field alone does **not** constrain downstream artifact bytes.

`scripts/stage_verified_core_handoff.py --dist dist --out qualified-dist` is a **new fail-closed, local-only** stage. It first requires a CLEAN, non-authorizing scope receipt containing two well-formed private-snapshot SHA-256 digests. It subsequently opens a fresh POSIX `O_NOFOLLOW` dirfd / Windows native HANDLE-pinned pair using the *same* existing bounded snapshot implementation, then copies from these **private snapshot files** (not original paths) into a newly created private temporary staging directory. Each copied Wheel/sdist is checked against the **original** receipt's digest and the entire temporary pair passes a **second** full clean scope inspection, including ZIP/TAR physical metadata envelope and the same two SHA-256 values. The source dirfd/HANDLE context must exit successfully, including its final directory identity check, **before** the staging directory is renamed to the previously absent target name.

On any failure, the temporary staged pair is deleted; an existing target is refused without clobber. The output has **exactly two archive files**, no unrelated files, manifests, hidden third entries or weak metadata. Successful CLI output states `STAGED_SCOPE_CLEAN_NOT_AUTHORIZED`, `publication_authorized=false` and `independent_security_review_complete=false`, not release approval.

## Actual tagged workflow integration

The tagged **build** job still refuses any packaged unqualified optional extras with the existing `check_base_core_publication_scope.py --dist dist` command. **Only after that hard refusal** it stages a fresh pair, and `actions/upload-artifact` consumes `qualified-dist/*`, **not** `dist/*`. Likewise the conditional GitHub Release job rechecks the downloaded archive scope, restages it, and provides only `qualified-dist/*` to the release action. The TestPyPI job still downloads the already staged artifact from the build, remains dependent on GitHub Release and requires its own opt-in variable and trusted-publish environment. Its privileges and all tag/main/owner gating are unchanged. This work introduces no new publish trigger or permission.

The PR-safe build/rehearsal jobs remain unchanged and **do not** enter the tag-only handoff path; frozen ADR-0044 research extras remain admitted for local **testing only**, and blocked for public release under #622. The contract suite asserts both tagged artifact-upload sites consume only the staged pair, and revalidates the unchanged tag guards.

## Test-first negatives and validation

- The test-only source head `582827231c1e5737bd6edad7bddafc4d952c8aba` intentionally failed the [hosted Windows/Ubuntu source-only run #41219605441](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41219605441): the new staging helper did not yet exist. This demonstrates the **missing handoff workflow/test contract** before implementation; it is *not* a proof of a malicious package release.
- Synthetic adversarial cases cover: byte-for-byte SHA-256 equality between original and separately staged Wheel/sdist; refusal and zero staging if advertised unsafe optional extras; mutation of the original Wheel **after the first private inspection** and before staging, which must fail rather than certify a stale receipt; pre-existing target contents must not be overwritten.
- A new release workflow contract asserts the order `hard extras refusal -> exact snapshot stage -> upload qualified-dist/*` in tagged build and GitHub Release, and asserts TestPyPI still cannot bypass release gating.
- **Final exact-head CI:** record final SHA and Windows/Ubuntu × Python 3.11/3.12 staging + pinned Ruff CI, and Windows/macOS/Linux installed Core source parity, in the PR discussion after both finish at that exact head. No earlier CI success qualifies a later commit.

## Remaining limits and NO-GO

This mitigates the documented **inter-step filename reopening** within the controlled CI handoff, but does not prove atomic trusted publishing against a hostile actor who can mutate `qualified-dist` **after** staging or swap shared runner directory names. It is not a signed manifest, source-to-Git provenance review, atomic two-file snapshot, or independent security approval. If any release later becomes authorized, the publisher must consume the same isolated staged bytes and maintain a separate final artifact-to-source attestation and reviewer signoff.

**Unresolved no-go:** #574 version/owner/ADR-0045 acceptance; #622 frozen optional research Pillow/Accelerate advisories; #603 independent security review; #662 actual Windows Tauri WebView2 descendant TCP/UDP/DNS isolation; #673 Linux maintenance; #676 macOS accessibility. No GitHub Release/PyPI publication, tag, merge, model training, patient data or clinical deployment.
