# Main-branch independent review preflight (read-only)

**Scope:** release-governance finding [#631](https://github.com/AbdulazizShehri/MedOrigin/issues/631)
and security review [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603).
This preflight **never** mutates branch rules, merges a PR, adopts ADR-0045,
creates tags, or authorizes publication.

Run with a credential restricted to reading GitHub repository rulesets and PRs:

```bash
python scripts/check_medorigin_independent_review_governance.py \
  --repository AbdulazizShehri/MedOrigin --pr 630
```

The command requires:
- Active exact-`main` branch protection with no exclusion and delete/force-push safeguards.
- An enforced minimum of one PR approving review, stale-approval dismissal,
  review-thread resolution, and `require_last_push_approval=true`.
- Strictly required existing `quality (py3.11)`, `quality (py3.12)`, and
  `analyze (python)` (CodeQL) checks.
- A current-head GitHub `APPROVED` review by a human account other than the
  PR author; previous-head approvals, bots, pending/commented reviews, and
  dismissed or change-requested reviews do not qualify.
- Administrator-visible confirmation that there are no unqualified bypass
  actors. GitHub masks `bypass_actors` to a **non-admin token**, so a
  non-admin run fails closed rather than inventing authorization.

As observed on October 26, 2026, the `main` ruleset **#20172239** still
requires **zero** approving reviews and does not require last-push approval.
The available CLI token has **no admin permission**, so this branch cannot
be safely remediated with its credentials. The original ruleset also bears
a legacy MedScale name; that name is not proof of weaker enforcement.

**Administrator action:** after independently reviewing existing conditions
and inherited policies, change the ruleset's required approvals to at least
one and enable last-push approval, **preserving** all other existing
protections and required check contexts. Recheck the exact saved ruleset
after modification. Do not simply add `require_code_owner_review` as a
substitute for an independent review: current `.github/CODEOWNERS` names
the repository owner throughout.

**Reviewer action:** request a real independent human security review at
the *current candidate SHA*, including the exact source-to-artifact and
publisher authorization analysis in #603. A GitHub PR approval alone is
necessary evidence for this governance diagnostic, **not** the full
independent security verdict. PR #630 currently remains Draft and
ADR-0045 is proposed, not adopted.

A passing audit outputs `REVIEW_GOVERNANCE_PREFLIGHT_PRESENT_ONLY` and
**still** reports `publication_authorized=false`,
`independent_security_review_603_completed=false`, and
`adr_0045_accepted=false`. A blocked/unknown audit exits 2 and never
claims release qualification. The attached CI runs only synthetic
unit tests on its own workflow branch, with a read-only GitHub token,
no admin secrets, and no package/deployment upload.
