# ADR-0045 unpublished comparator: pinned archive snapshots + real built-artifact rehearsal

**2026-11-02 Asia/Riyadh • nonpublishing synthetic-only engineering • source-
and archive-SHA-bound evidence • ADR-0045 NOT accepted • RELEASE NO-GO.**

This report is a bounded author-side qualification of the **unapproved
base-only Core proposal**, not a change to the canonical frozen research
`pyproject.toml`, `uv.lock`, MRL, published `medscale` package, or a
clinical application. The parent is
[Draft #821](https://github.com/AbdulazizShehri/MedOrigin/pull/821),
immutable head `e605cef5b9941b1a622e61ea9352eef7a782e0b1`.
The executable/source code HEAD used for the final actual build is
`cb64fb27e69a7cb8385c5908a24f32019dbbef52`, **before this
append-only evidence file**.

## Actual integrity flaw closed in the distinct comparator

The earlier `scripts/compare_medorigin_base_only_archives.py` called
the parent source-bound `verify()`, then independently reopened
**caller-owned mutable original** Wheel/sdist paths to read archive
members, ZIP/TAR headers, compressed streams and final reported SHA.
An external path swap after verification could make comparison
diagnostics about bytes that the verifier did not qualify. This does
**not** prove an active publisher bypass; ADR-0045 was unapproved.

The new comparator:

- Calls the parent's `read_stable_dist_bytes` **once** per distinct
  original dist directory, with bounded file-descriptor and identity
  checks established in #821. It snapshots both sides before
  verification or diagnostic extraction. The original paths are
  **never** reopened in comparator diagnostics afterward.
- Writes only the two pinned archives into private disposable
  scratch directories; invokes the *actual* `verify()` separately
  on each private pair. It requires status
  `BASE_ONLY_PROPOSAL_SOURCE_BOUND_VERIFIED`, matched source commit,
  exact Wheel/sdist receipt hashes equal to original snapshot bytes,
  and **explicit false** release, ADR acceptance and independent
  reviewer flags.
- Computes reported SHA-256 from original immutable in-memory byte
  snapshots. Compares member bytes, ZIP/TAR envelopes, compressed
  streams and gzip/TAR diagnostics on private scratch copies only.
  Checks these private copies for unexpected mutation after all
  diagnostic reads.
- Keeps `--require-identical` fail-closed, rejects the same
  source directory and source member differences. Scratch and all
  hosted-built archives are automatically deleted, with no uploads.

This narrows the verifier/comparator TOCTOU gap. It does **not**
prevent mutations to the original files *after* the snapshot or
protect a separate future publisher from reopening them; it is not
a signed artifact, OS kernel snapshot, reviewer authority, or ADR
acceptance.

## Adversarial RED → GREEN and cross-platform source checks

- New test-first source at `d7706f174ca53b8ae3ff8a138a567ce2f6127a19`;
  [actual hosted Windows/Linux RED #41357530843](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41357530843):
  **four intended comparator failures**, with **40 PASS, 1 SKIP**
  on Linux; regressions exposed original path reopens, false
  verifier digest acceptance, and snapshot mutation.
- The repaired source refactors comparator diagnostics to
  independently verified private snapshots; updates old synthetic
  test fakes to include explicit source-bound SHA receipts.
  On authorized local Windows Python3.14.7, at code SHA
  `ab3da4ccb9cb1f1c71e1e732c5fc7a65fab06f8f`,
  **42 PASS / 3 SKIP**, Ruff `0.14.4` lint/format PASS;
  three skips include optional actual built archive and
  Windows-restricted link fixtures.
- Source files were committed with the exact pinned Ruff formatting.
  Hosted [GREEN run #41357899645](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41357899645):
  **4/4 SUCCESS** on Ubuntu24.04+Windows2025 × Python3.11/3.12;
  each job **44 PASS, 1 SKIP**, Ruff check/format PASS.
  The one skipped fixture was the real-built-proposal artifact
  not yet supplied to that source-only matrix.
- Final exact-code-head source workflow
  [#41358425696](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41358425696)
  tests the same source with the actual-build workflow unchanged.
  This is **source-only**, not native/real-artifact build.

## Actual, separately built private Wheel and sdist (no upload)

- [Exact-code-head real artifact run #41358425735](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41358425735):
  **COMPLETED SUCCESS**; 1/1 hosted Linux job; job log inspected.
- Used `uv 0.12.19`, Python 3.11 and an **isolated ephemeral**
  build virtualenv with **`hatchling==1.32.4`**. Frozen canonical
  `pyproject.toml` declares an unconstrained Hatchling requirement,
  but the original independent exact-Git Wheel verifier requires
  Generator Hatchling 1.32.4. No canonical root mutation was made.
- Ran `stage_medorigin_base_only_proposal.py` independently twice
  from exact committed source, then `uv build --no-build-isolation`
  twice (second time offline). Builder outputs contain an extra
  `.gitignore` sentinel generated by `uv`; **do not relax**
  the strict verifier's exact-two-file rule. The hosted workflow
  fail-closed checks the builder's **exact three expected file names**
  and regular-file types before copying ONLY ordinary bounded
  Wheel + sdist into a separate, private, exact-two archive directory.
  Unexpected names, directories or symlinks are rejected.
- Both built archive pairs independently passed `verify()` against
  exact frozen Git source. The newly repaired real comparator ran
  `--require-identical` and reported
  `SOURCE_BOUND_ARCHIVES_BYTE_IDENTICAL`; exact identical
  per-artifact SHA-256 values were printed in the **actual CI log**:

| Proposed artifact | Build 1 SHA-256 | Build 2 |
| --- | --- | --- |
| `medscale-0.3.0-py3-none-any.whl` | `f971dd8e09683d0c29e2bf48b19bf30dcf3866f583fd7f6143eb4855e43fc7c5` | Identical |
| `medscale-0.3.0.tar.gz` | `f216795afcd3a714a72a1d2f5c0a0dd46234a831378067a5dd2cd5aeedd92c17` | Identical |

- The previously skipped `MEDORIGIN_PROPOSAL_TEST_DIST`
  **actual built-artifact positive fixture executed** in the same
  job with both new comparator and inherited source verifier tests:
  **45 PASS, 0 SKIP, 0 FAIL**.
- The initial actual build replay correctly failed because
  `uv build` added the extra builder `.gitignore`. A second
  iteration correctly failed because the unconstrained Hatchling
  installed by isolated builder differed from the audited fixed
  generator. Both were repaired by strictly checked private
  staging and a **builder-only** Hatchling 1.32.4 pin, rather
  than weakening the strict original security gate.
- Full build and artifacts stayed in ephemeral CI temp directories;
  no artifact upload, release bundle or package-registry action.

## Why this is still NOT release qualification

**ADR-0045 remains PROPOSED, owner approval and independent
source-to-artifact review not obtained.** The ORIGINAL optional
`pillow==12.3.0` and `accelerate==1.14.0` metadata
under [issue #622](https://github.com/AbdulazizShehri/MedOrigin/issues/622)
remains not security-qualified. Passing tests on an **unapproved
alternative base-only package** does not remove that issue, and
does not prove current canonical optional extras safe.

Independent reviewer [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603),
founder version/ADR/release approval
[#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574),
independent Windows WebView2 OS packet isolation
[#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662),
Linux zbus5 maintenance #673 and spoken VoiceOver #676
remain separate blockers.

**No frozen research root mutation, protected-main merge, PHI,
clinical use, file export, signed installer, TestPyPI/PyPI upload,
tag, public package or deployment was performed.**
`publication_authorized=false`; **RELEASE NO-GO**.
