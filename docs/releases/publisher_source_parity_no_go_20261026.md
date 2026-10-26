# MedOrigin v0.3.0 — publisher/source parity blocker (unpublished)

**Observed October 26, 2026. Engineering source:** Draft PR #637 at
`6c1e800f15e5a24dc8e02cdafd144d2b3c7478f9`. This is a
*source-to-publisher* decision record, **not** ADR-0045 approval or a
security review signoff. No tag, package upload, or public release was made.

## What was reproduced

Two isolated Wheel+sdist pairs were built from the **same Git commit**, using
the free cached build backend, without editing the frozen research root,
`uv.lock`, or historical receipts.

| Source projection | Existing publisher metadata guard | Meaning |
| --- | --- | --- |
| `scripts/stage_medorigin_core_projection.py` (actual tag `build` job) | **BLOCKED**, exit 2 | Wheel and sdist advertise optional extras and additional dependency requirements |
| `scripts/stage_medorigin_base_only_proposal.py` (ADR-0045, *not accepted*) | `BASE_CORE_PUBLICATION_SCOPE_CLEAN` | Wheel and sdist advertise neither optional extras nor runtime third-party requirements; independent Git-to-artifact verification passed |

The source-bound Core-only proposal had **254 committed source files, 255
Wheel members and 258 sdist members**. Passing that *metadata scope guard*
is not sufficient for a release or independent review. The versions still
show the compatibility name `medscale 0.3.0`, and the independent
license/publisher, administrative, security and release decisions are open.

The existing `github-release` job already calls
`scripts/check_base_core_publication_scope.py --dist dist`, so it should
reject the canonical tag artifact *late*, after the tag's `build` job has
uploaded an internal artifact. This PR adds **the same independent read-only
gate to the tag `build` job before `actions/upload-artifact`**, ensuring
that an incompatible tagged build fails earlier and cannot pass its artifact
to `install-smoke`, `github-release`, or downstream `testpypi-publish`.

The nonpublishing PR/dispatch source-to-artifact roundtrip is deliberately
unchanged. It may continue to reproduce existing canonical artifacts for
audit; those results are not tagged, distributed, or interpreted as approval.
The tag build is intentionally **NO-GO** while the published-source
identity differs from the independently tested Core-only candidate.

## Owner and reviewer handoff

1. **Founder:** decide whether to accept ADR-0045 and the explicit
   `MedOrigin` vs `medscale` v0.3.0 compatibility identity; the accepted
   ADR-0044 does not itself authorize removing optional metadata.
2. **Independent reviewer (#603):** clone the exact candidate SHA and
   reproduce both projection builds. Examine the actual tag `build`,
   `github-release`, and `testpypi-publish` workflow steps, source and
   dependency/license metadata, and current GitHub ruleset/environment
   bypass controls. Provide a **separate named** approval/block decision;
   passing this gate does not replace that judgment.
3. **Administrator (#631, #621):** enforce appropriate human PR approvals
   while preserving required checks, and disposition missing GitHub
   dependency alert visibility without enabling paid services.
4. **Engineering, only after those decisions:** implement the authorized
   source projection in the publisher, qualify its exact newly built Wheel
   and sdist, clean-install and rerun all checks, preserving historic roots.
   The publisher should remain blocked before this transition.

## Reproduce without publishing

```bash
# Run on a clean, pinned checkout with an already cached build backend.
python scripts/stage_medorigin_core_projection.py --out /tmp/medorigin-canonical
uv build --offline --wheel --sdist /tmp/medorigin-canonical --out-dir /tmp/medorigin-canonical-dist
python scripts/check_base_core_publication_scope.py --dist /tmp/medorigin-canonical-dist
# Expected: BLOCKED, exit 2, because optional extras remain advertised.

python scripts/stage_medorigin_base_only_proposal.py --out /tmp/medorigin-base-only
uv build --offline --wheel --sdist /tmp/medorigin-base-only --out-dir /tmp/medorigin-base-only-dist
python scripts/check_base_core_publication_scope.py --dist /tmp/medorigin-base-only-dist
python scripts/verify_medorigin_base_only_proposal.py --dist /tmp/medorigin-base-only-dist
# Expected: scope clean and source-bound verified, but publication_authorized=false.
```

Do not reuse the historic unpublished QA ZIP checksums for newer source
commits. No real patient data, credential escalation, model inference,
release/environment variable activation, or public package registry use
is needed for this comparison.
