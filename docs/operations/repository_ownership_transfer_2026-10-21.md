# MedOrigin repository ownership transfer — verified preflight and execution runbook

**Status:** PREPARATION ONLY — transfer NOT authorized or performed  
**Audit date:** 2026-10-21 (UTC)  
**Source:** `TheHalfMoon/MedOrigin` (GitHub repository ID `1296003634`)  
**Target:** `AbdulazizShehri/MedOrigin` (user ID `222180173`)  
**Release authority:** None conferred by this document  
**Scientific/clinical authority:** None conferred by this document

> This is a decision and verification record. It must not change immutable MRL-0809 research prerequisites, create a tag/release, enable publishing, run GPU workloads, or perform the ownership transfer.

## 0. Evidence and confidence model

The data below were read independently through authenticated GitHub connections on 2026-10-21. The source owner was authenticated as `TheHalfMoon` with `admin=true`. The intended recipient was authenticated as `AbdulazizShehri`. GitHub identifies **TheHalfMoon as a personal User account**, *not* an Organization; use the personal-to-personal transfer procedure. A lookup for `AbdulazizShehri/MedOrigin` returned HTTP 404 and the destination's repository search returned no matches, but this is not a guarantee against a conflicting fork, private name reservation, or a future creation: re-check at cutover.

Evidence:
- Source main SHA: `76e68c9b61a2210607022ff4c44465bd447c6800`; main CI and CodeQL completed successfully at this SHA.
- Main ruleset ID `20172239`, active, repository-level, includes `refs/heads/main`, disallows deletion and non-fast-forward pushes, permits merge commits only, requires resolved review threads and these exact GitHub Actions contexts: `quality (py3.11)`, `quality (py3.12)`, `analyze (python)`. The branch response reports `protected=true`; legacy branch-protection endpoint was inaccessible through the connector (403); the active ruleset is the authoritative observed protection, not the legacy `protection.enabled` shortcut.
- Exactly one open PR was returned: [#586](https://github.com/TheHalfMoon/MedOrigin/pull/586). Its HEAD was `6bbd0f206187826867eb16473e92870b3062f9c4`; base is main. No approving reviews or review threads appeared in the connector's read.
- [#584](https://github.com/TheHalfMoon/MedOrigin/pull/584) and [#585](https://github.com/TheHalfMoon/MedOrigin/pull/585) merged before the snapshot.
- Source `main` CI run [39425505112](https://github.com/TheHalfMoon/MedOrigin/actions/runs/39425505112) and CodeQL [39425505309](https://github.com/TheHalfMoon/MedOrigin/actions/runs/39425505309) completed successfully.
- PR #586 exact-head CI [39604867335](https://github.com/TheHalfMoon/MedOrigin/actions/runs/39604867335) and CodeQL [39604867307](https://github.com/TheHalfMoon/MedOrigin/actions/runs/39604867307) were **queued** at the time of observation; do not replace this with an unverified PASS. Older PR CI run [39591496713](https://github.com/TheHalfMoon/MedOrigin/actions/runs/39591496713) had failing pytest shards due to `ModuleNotFoundError: No module named 'scripts'` during test collection. The newest commit changes test loading to a direct `spec_from_file_location` path, but has not qualified in hosted CI.
- Two tag refs were listed: `v0.1.0` and `v0.2.0`. The release API listed one historical published GitHub Release, `v0.1.0`, with no binary assets. **No `v0.3.0` tag or public Release was listed.**
- Open issues enumerated: [#574](https://github.com/TheHalfMoon/MedOrigin/issues/574), [#429](https://github.com/TheHalfMoon/MedOrigin/issues/429), [#450](https://github.com/TheHalfMoon/MedOrigin/issues/450), [#545](https://github.com/TheHalfMoon/MedOrigin/issues/545). #574 governs synthetic-only developer software release preparation; the others remain separate GPU/science qualification blockers.
- GitHub Actions API reported 6,835 cumulative workflow runs as a snapshot count, **not** a promise of permanently retained logs or artifacts.
- The branches collection returned at least 300 branches across its first three 100-item pages; a full paginated ref inventory is required immediately before cutover.
- The repository is public and unarchived. No action has modified visibility.
- **Independent immutable-input byte check (2026-10-21):** via the authorized Windows `Abdulaziz` device, authenticated `gh api` retrieved the current source bytes of all four frozen inputs; SHA-256 was computed in memory directly from the GitHub-provided Base64 content, with **four out of four exact digest matches** to the recorded research identities: `pyproject.toml` (5,230 bytes), `uv.lock` (641,372 bytes), v1 manifest (2,751 bytes), and v2 manifest (4,261 bytes). No repository file or disk-backed research input was changed.

**Unverified configuration:** Repository secrets (values must never be exported), environment gates/secrets, Actions variables/policies, all GitHub App installations and external providers, webhooks, deploy keys, GitHub Projects v2 associations, discussion categories, all collaborators, security/code-scanning settings, and complete branch/tag/ref list. The connector does not provide administration reads for every endpoint. This is a live-preflight blocker, not proof of absence.

## 1. Transfer preservation matrix

| Object / behavior | Platform behavior | Required verification |
| --- | --- | --- |
| Git commits, full history, branches, tags, commit authorship | GitHub states Git commit data is preserved; native transfer retains repository identity | Before/after `git ls-remote`, branch/tag inventories, commit graph/root and selected SHA checks; compare immutable repo ID |
| Open/merged PRs and issue discussions | Native repository transfer preserves issues and PRs | Count by state, verify #586, reviews/threads, #574/#429/#450/#545 and links after transfer |
| Issue comments, labels, milestones, discussions | Issues transferred; repo-associated settings/data should be checked individually, particularly Discussions and non-repo Projects | Export/reconcile counts and individual sample objects; verify assignments and milestones/labels |
| Wiki, stars, watchers, forks | Explicitly preserved by GitHub documentation | Compare counts/links |
| Historical GitHub Releases | Repo Releases travel with repository | Compare tag associations, asset IDs/counts, download URLs and actual retrieval |
| GitHub Actions workflow source files | Git-tracked workflows move with Git | Check workflows and run newly authorized **nonpublishing** CI; workflow policies may differ |
| Historical Actions runs, checks, logs, artifacts | History and artifacts are governed by retention policies; GitHub transfer docs do not promise indefinite availability | Inventory relevant runs/artifacts before move, archive permissible critical evidence, validate accessible historical runs after; do NOT represent transient artifacts as permanent |
| Branch protections and rulesets | Repository-level ruleset is active now; destination plan/policy can change enforcement | Export ruleset JSON and check contexts/integration IDs, bypass actors, and actual rejected protected operations without destructive experiments |
| Webhooks, repository secrets, deploy keys | GitHub explicitly says they remain associated | Record names/metadata only; check integrations and test event delivery/least privileges post-transfer |
| Environments, variables, organization-level secrets, GitHub Apps, third-party services | Not fully guaranteed by transfer docs | Inventory policy/refs, reauthorize or recreate when needed, validate safe no-publish pathway |
| Redirects | Repository Web and Git operations redirect after transfer | Test old PR/issue/commit URLs and clone endpoints; **never recreate the old source repo** |
| GitHub Pages | GitHub Pages URL does *not* redirect | Inventory site/custom domain, update DNS/canonical link if applicable |
| Git LFS | LFS objects transfer in background | Check LFS inventory/integrity and allow migration to complete if used |
| GitHub Projects | Associated repo projects/settings under new owner can be administered; standalone account/org Projects might require independent changes | Inventory owner, project IDs and field associations; explicitly test board access and automation |
| Collaborators / permissions | Personal-to-personal transfer retains original owner and collaborators as collaborators; destination owner gains administration | Recheck collaborator and automation access; do not assume inherited organization permissions |
| Packages, external registry linkage | Registry-dependent and may lose linkage | Audit package IDs and trusted publishers; no publication during transfer |

**Important edge cases:**
- The destination must not already contain `MedOrigin` or a conflicting fork network.
- Transfer from one personal account to another requires recipient email acceptance **within one day**.
- GitHub may permanently retire the **old** `TheHalfMoon/MedOrigin` name if usage thresholds are met; measure activity and never depend on recreating that name.
- Do not assume old historic `TheHalfMoon/MESC` redirect chains continue to resolve; test their links explicitly after move.
- For OIDC on GitHub.com, repository transfers after 2026-07-15 transition to an immutable-subject format including owner and repo IDs; verify the *actual* post-transfer `sub` before configuring any trust at an external provider.

## 2. Exact ten-stage migration procedure (each step is a gate)

### Gate 1 — Repository inventory (read-only)

**Prerequisite:** Both GitHub accounts reachable; source permission confirmed.  
**Actions:** Snapshot stable repository ID, current `main` SHA/tree, all branches/tags (pagination), PRs/issues/reviews/discussions/milestones/labels/wiki, releases/assets, forks, Git LFS, README/CITATION/CODEOWNERS, workflows, historical runs and important unexpired artifacts, ruleset ID `20172239` and any other protection, repository visibility, collaborators, projects, dependency alerts, webhooks/deploy keys/environments/variable names. Record `gh api` JSON with tokens and secrets stripped.  
**Risks:** Partial API pagination, stale snapshot, accidentally exposing secrets, auto-expired CI artifacts.  
**Verification:** Compare counts with GitHub UI and use a time-stamped SHA-bound inventory manifest; check repo ID.  
**Done when:** All objects enumerated; inaccessible families explicitly registered as open verifications.

### Gate 2 — Owner and target eligibility

**Prerequisite:** Gate 1, source account `TheHalfMoon` admin; target user `AbdulazizShehri` ready to accept email.  
**Actions:** Reconfirm GitHub owner types are User/User, repo name remains `MedOrigin`, target name/fork-network vacancy, account plan visibility and protection entitlement, source/target policies, recipient's access to confirmation email.  
**Risks:** Target collision, loss of paid-only features in destination, wrong recipient identity, expired invitation.  
**Verification:** Check account IDs, admin status, absence of target repo **at cutover**, and GitHub warning screen.  
**Done when:** Recipient and target pass all restrictions with no outstanding identity or feature-loss warning.

### Gate 3 — Recovery package and rollback decision

**Prerequisite:** Snapshot at stable `main`, least-privilege storage chosen; no active release pipeline.  
**Actions:** Use `git clone --mirror` plus `git bundle` (or another verified full-ref mirror); record `git show-ref`, refs and all relevant Git SHA/tree identities. Export non-secret GitHub metadata and accepted research evidence references via API, and download critical eligible ephemeral CI artifacts before expiry. Check any Git LFS objects. Keep temporary backup access-controlled (never put credentials/private config in public Git). GitHub's native transfer preserves issue/PR data but a Git mirror **does not** back up those platform objects. Store only safe audit manifests/recovery instructions in repo.  
**Risks:** Incomplete mirrors, leaked tokens, missing GitHub-hosted metadata, inability to recreate PR/issue review history identically from a backup.  
**Verification:** Run `git fsck` and compare refs/tags/SHA, verify backup accessibility and restore-test into a disposable offline directory without overwriting the repository; verify redaction.  
**Done when:** A tested full Git recovery set and separate essential platform-metadata evidence both exist. Rollback is a **new transfer back**, subject to permission/acceptance; not a guaranteed atomic undo.

### Gate 4 — PR #586 and CI disposition

**Prerequisite:** Capture PR #586 exact HEAD and base, inspect changed files and comments.  
**Actions:** Do **not** merge current HEAD on old CI. Newest `6bbd0f2` is one commit ahead of `008c354`; it fixes test import loading via `spec_from_file_location`. Run exact-head CI Python 3.11/3.12, CodeQL and repository contract tests. Independently review the relevant Python script/test; use actual Alibaba OpenCodeReview where supported and explicitly record whether PStack/TesterArmy E2E were actually available or applicable. **Migration-specific finding:** PR #586's `_NEW` constant is still `https://github.com/TheHalfMoon/MedOrigin`, NOT `https://github.com/AbdulazizShehri/MedOrigin`. This is appropriate for its historical proposal but not the final post-transfer canonical address. Choose a controlled follow-up before merge or defer it until after transfer; preserve separate predecessor/successor provenance.  
**Risks:** Merging incomplete CI, misrepresenting old review as exact-head review, downstream wrong URLs, hidden changes to frozen input.  
**Verification:** Exact HEAD checks green, diff excludes frozen inputs, code reviewer execution receipts, no unresolved threads and protected rules.  
**Done when:** Either a fully qualified, explicitly scoped pre-transfer merge has completed **or** #586 remains preserved/open with an owner/CI-aware post-transfer repair task. **It need not block ownership transfer when publishing stays disabled.**

### Gate 5 — Release / policy freeze

**Prerequisite:** Gates 1–4, research source SHA manifests recorded.  
**Actions:** No `v0.3.0` tag, release, PyPI/TestPyPI, Hugging Face publication, environment/publisher enable, PHI, GPU/scientific publication or frozen root edit. Snapshot repository ruleset and source main CI. Record whether any workflow names, required checks, ruleset integrations, release guards or environments need adaptation.  
**Risks:** Actions running under a different owner/permissions, accidental distribution, loss of gate protection.  
**Verification:** Release variable/guard remains disabled; tag refs `v0.1.0`/`v0.2.0` unchanged; required contexts exactly preserved or safely reconstituted.  
**Done when:** A no-publish cutover window is declared and protection-state inventory is complete.

### Gate 6 — Actual GitHub transfer (explicit founder approval required)

**Prerequisite:** Gates 1–5 complete, live source and destination rechecked, written approval received *specifically for ownership transfer*.  
**Actions:** Log in as `TheHalfMoon` > `TheHalfMoon/MedOrigin` > Settings > General > Danger Zone > Transfer. Choose **Specify an organization or username** and enter `AbdulazizShehri` (personal account). Keep repo name **MedOrigin**, visibility public and all existing history. Read GitHub's warnings; confirm by entering the exact repository name and submitting transfer. Recipient accepts the transfer invitation within 24 hours.  
**Risks:** Transfer denial, wrong user, expired acceptance, feature regression, integrations broken on ownership change.  
**Verification:** Before clicking, show exact source/target, warnings and blockers; after recipient acceptance, verify `full_name=AbdulazizShehri/MedOrigin` and **stable ID `1296003634`**.  
**Done when:** GitHub reports transfer accepted and both stable ID and owner identity match. Creating this runbook or PR is not approval.

### Gate 7 — Destination governance

**Prerequisite:** GitHub completed the transfer and Gate 6 checks passed.  
**Actions:** Confirm public visibility; default branch main; ruleset status, exact required context/provider IDs, merge method, no bypass, branch deletion/force protections, tags/release gates, code/security scanning, collaborators, issue ownership, GitHub Projects/discussions and Pages settings.  
**Risks:** Silent branch protection change, team-scoped permissions unavailable to user repo, missing code scanning.  
**Verification:** Read effective rulesets and checks at destination; ensure a normal draft PR is subject to required checks (never test by force-pushing/deleting protected refs).  
**Done when:** All originally effective security/governance properties are restored and verified with recorded evidence.

### Gate 8 — Actions and integration recovery

**Prerequisite:** Gate 7 protection restored; publishing still disabled.  
**Actions:** Inventory and validate repository secrets and deploy keys **by name and safe test only**; reconfigure any orphaned organization secrets, environment rules, GitHub App installations, GitHub Projects automations, webhook destinations, external CI, badges, cross-repo callers and release variables. Change local/CI remotes from old URL to `https://github.com/AbdulazizShehri/MedOrigin.git`. For OIDC/Trusted Publishers, inspect new actual immutable `sub` and update downstream registries (PyPI/TestPyPI or others) only under their separate authorization; never exercise publish paths as validation.  
**Risks:** Old installation grants no access, wrong OIDC claim, secrets unbound, unintended publishing.  
**Verification:** Nonpublishing CI+CodeQL complete, integration delivery is checked with harmless events, no external artifact distributed and explicit publish flags remain false.  
**Done when:** Normal developer CI works under the new owner and all publication integrations remain safely gated.

### Gate 9 — Append-only scientific provenance and package identity

**Prerequisite:** Transfer verified; original frozen files intact; separate founder decision for any change to canonical research root identity.  
**Actions:** Treat historic root `pyproject.toml`, `uv.lock` and MRL-0809 v1/v2 prerequisite manifests as permanent predecessor evidence. Their **independently verified** SHA256 values (checked against GitHub contents on 2026-10-21) are:
- `pyproject.toml`: `c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510`;
- `uv.lock`: `6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4`;
- v1 manifest: `7773967611e42c3d74338a1ec7c9004f661843df809865f6c6d455923fea89d1`;
- v2 manifest: `56de494cf30b6d3dd3aa005e63d55ea7490f7645dd37cbb388188d635813a36d`.
Recompute and compare each exact SHA again at cutover; the 2026-10-21 independent source-byte verification does not excuse a fresh identity check at transfer time. Existing `pyproject.toml` has four `TheHalfMoon/MESC` `Project-URL` fields; the current tag-publish guard separately requires four `TheHalfMoon/MedOrigin` URLs. Both identities must remain **fail-closed** for future public releases until an explicitly accepted new successor input exists. After a separate root-input authorization, create **new** successor source/lock metadata and append-only lineage describing predecessor repo ID, original Git commit/tree, exact historic SHA bindings, four changed URLs to `AbdulazizShehri/MedOrigin`, new hashes, reproducibility environment and provenance validation. Update forward-facing `CITATION.cff`, README, docs, security contact, active links, current `Project-URL` metadata and release wheel guard on a scoped PR, with tests and clean source/wheel/sdist qualification; **never rewrite past manifests, tags, old commit authors or scientific results**. Keep `medscale` CLI/import and developer version `0.3.0` unless independently decided otherwise.  
**Risks:** Scientific trust-root corruption, false package attribution, broken historical citations, temporary release guard mismatch, accidental external distribution.  
**Verification:** Original input and manifests' SHA remain byte-identical, predecessor/successor lineage explicit, legacy citations still resolvable, fully new package metadata and guards match `AbdulazizShehri/MedOrigin`, independent tests pass; redistribution notices/licenses maintained.  
**Done when:** Repository ownership is correct; scientific history untouched; successor metadata plan independently accepted and then verified before any separate public release.

### Gate 10 — Independent post-transfer acceptance and closeout

**Prerequisite:** Gates 6–9 applicable tasks executed; no release authorization assumed.  
**Actions:** Query both old/new URLs; verify stable repository ID, main SHA if unmodified or approved successor SHA, complete refs/tags, PR/issue/release inventories, redirect chain, data and manifest hashes, historical Action traces and current nonpublishing CI+CodeQL, protection, credentials (names only), linked projects, package source metadata and integrations. Record a pass/fail evidence table with exact URLs and timestamps in GitHub under the new owner.  
**Risks:** Redirect failure, missing refs, expiring artifacts, hidden integration damage, incomplete documentation.  
**Verification:** Independent post-transfer checker compares pre/post snapshots; every discrepancy has a recorded disposition; no unauthorized tag/release.  
**Done when:** `AbdulazizShehri/MedOrigin` is independently verified as owner of the *same* repository ID and all applicable gates are accepted. Only then mark `TRANSFER_COMPLETE`.

## 3. Explicit GO/NO-GO for today

**Current status: NO-GO for executing transfer.** The founder explicitly authorized preparation **only**. Additional live cutover requirements: (a) full metadata/ref and settings inventory and recoverable backup, (b) destination eligibility and policy confirmation, (c) a deliberate disposition of PR #586 pending exact-head CI and new URL issue, (d) branch/ruleset and nonpublishing release safeguards captured, (e) **new express founder approval** for the transfer.

PR #586's scientific source-audit work is separable from *ownership*. Ownership transfer itself does not alter file bytes; the frozen originals should continue to hash exactly as before. **The public Core v0.3.0 release remains unauthorized**, and #429/#450/#545 scientific/GPU evidence requirements remain separate.

## 4. Sources consulted

- GitHub: [Transferring a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository)
- GitHub: [Actions OIDC reference, including post-July-2026 immutable subjects](https://docs.github.com/en/actions/reference/security/oidc)
- GitHub: [Repository Actions settings and log retention](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
- GitHub: [OIDC in PyPI](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-pypi)
- GitHub: [GitHub App installations](https://docs.github.com/en/apps/using-github-apps/installing-a-github-app-from-a-third-party)
- Live [MedOrigin PR #586](https://github.com/TheHalfMoon/MedOrigin/pull/586), [main CI](https://github.com/TheHalfMoon/MedOrigin/actions/runs/39425505112), [active ruleset](https://github.com/TheHalfMoon/MedOrigin/rules/20172239), and [issue #574](https://github.com/TheHalfMoon/MedOrigin/issues/574).

## 5. Execution authorization ledger

- [x] Read-only source and target account identity inspected.
- [x] Current main SHA, PR, issues, available tags/releases and ruleset inspected.
- [x] All four MRL-0809 immutable source/manifest SHA-256 values independently verified from current GitHub file bytes on Windows (read-only).
- [x] Old hosted pytest import failure diagnosed; current PR exact-head CI status disclosed.
- [x] Preparation runbook proposed without changing historical research inputs.
- [ ] Complete private/admin-only pre-transfer inventory and tested backup.
- [ ] Resolve or preserve PR #586 with exact-head qualifications and transfer-aware successor scope.
- [ ] Explicit founder approval for ownership transfer.
- [ ] Actual transfer submitted by source admin and accepted by destination.
- [ ] Post-transfer independently validated and findings saved.
- [ ] Separate release/scientific root authorization (not implied by transfer).

**Next founder decision:** After remaining pre-transfer gates have evidence, explicitly approve *only* the transfer of the stable repository from `TheHalfMoon/MedOrigin` to `AbdulazizShehri/MedOrigin`; do not authorize release or frozen input rewrites by implication.
