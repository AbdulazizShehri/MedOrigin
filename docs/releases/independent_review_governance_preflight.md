# MedOrigin main-branch independent review preflight (read-only)

**Snapshot (27 October 2026): main protection repaired; PR #641 still needs independent approval. Re-run the commands below against the latest head before relying on these findings.**

Track [#631](https://github.com/AbdulazizShehri/MedOrigin/issues/631) (closed after the owner-admin repair) and independent security review [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603) (open). The main-target Developer Beta is [Draft PR #641](https://github.com/AbdulazizShehri/MedOrigin/pull/641), source SHA `00319ab78dfe28e5f2241c22005c52b251d428a4`, incorporating the synthetic-preview security fix from [Draft #644](https://github.com/AbdulazizShehri/MedOrigin/pull/644). The stacked cross-OS audit [Draft #642](https://github.com/AbdulazizShehri/MedOrigin/pull/642) retains its previous `671bd66b` head and must not be mistaken for qualification of the newer source. Nothing is merged into protected `main`, published or approved.

## What is now configured

The repository owner repaired existing branch ruleset **#20172239 in place** on 26 October 2026. Its name is now **MedOrigin canonical main protection v1** (no longer the legacy MedScale label). The active rule still targets only `refs/heads/main` with no exclusion or bypass actor, requires **at least one PR approval**, disallows approval from the **last pusher**, dismisses stale approvals after a push, requires review-conversation resolution, disallows deleting/non-fast-forward updates, and retains strict checks:
- `quality (py3.11)`
- `quality (py3.12)`
- `analyze (python)` (CodeQL)

The owner read back the saved ruleset and programmatically compared all preserved checks and protections. See [#631 resolution evidence](https://github.com/AbdulazizShehri/MedOrigin/issues/631). **The change of settings is not a reviewer approval.** A fresh GitHub PR check on 27 October returned `isDraft=true` and `reviewDecision=REVIEW_REQUIRED` for PR #641. Mergeable code and green checks do not replace a review approval.

## Re-run the read-only preflight

Use an authorized **GitHub account with repository-admin read visibility** to inspect the ruleset and PR. This command requests no publishing, merging or settings changes:

```bash
python scripts/check_medorigin_independent_review_governance.py \
  --repository AbdulazizShehri/MedOrigin --pr 641
```

The checker refuses incomplete ruleset conditions, weak PR review policy, missing required checks, hidden/unqualified bypass actors, bot/self/old-SHA approvals, dismissals, malformed responses, and Draft PRs. With no current-head independent review it correctly returns `BLOCKED` (exit 2). A non-admin GitHub token may mask bypass actors, which also correctly fails closed.

The older `--pr 630` command and zero-approval finding were historical diagnostics **before** the owner repair; they must not be reused as the current repository state. Unit-test fixtures mentioning PR 630 are synthetic and do not change the real target.

Even when every governance preflight requirement is eventually met, its success status `REVIEW_GOVERNANCE_PREFLIGHT_PRESENT_ONLY` is **necessary but not sufficient** for source-to-artifact security approval. A named independent reviewer must evaluate the exact head and sign [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603), including source/metadata/rights, publisher gates, and the research-extras advisory scope [#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622). Founder approval of proposed ADR-0045 is a separate decision.

## No release authority

The `00319ab7` candidate has [20/20 successful full CI](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/40432519457), [4/4 three-OS Core/source identity checks](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/40432519453), and 36/36 focused synthetic-preview tests in a local Python 3.14 smoke run (additional coverage, not a substitute for Python 3.11/3.12), **but** every reviewer/security-gate report still requires `publication_authorized=false`, `adr_0045_accepted=false` and `independent_security_review_603_completed=false`. Do not merge main, create a release tag, activate a publisher, process patient data, or misstate author CI as independent approval.
