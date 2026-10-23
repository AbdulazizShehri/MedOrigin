# MedOrigin Core — release v-tag ruleset administrator handoff

**As of 2026-10-24:** NO-GO for public release; this is a prepublication
configuration checklist, not permission to tag, merge, upload or deploy.

## Observed live repository state

- Repository: [AbdulazizShehri/MedOrigin](https://github.com/AbdulazizShehri/MedOrigin)
- Active main-branch ruleset: ID `20172239`, covering `refs/heads/main`.
- No active tag-target ruleset returned by the read-only GitHub repository
  rulesets API at this audit. Main-branch PR checks do not protect tags.
- Read-only CLI command:

  ```shell
  python scripts/check_release_tag_governance.py \
    --repository AbdulazizShehri/MedOrigin \
    --tag-ref refs/tags/v0.3.0
  ```

  This **only queries** GitHub rulesets; it **does not create the example tag**.
  Current result: `BLOCKED` with an active v-tag ruleset absent or unverifiable.
  A nonzero result is a hard release stop.

## Separate repository-admin configuration (not done in this PR)

1. Open [repository Rulesets](https://github.com/AbdulazizShehri/MedOrigin/settings/rules),
   choose **New tag ruleset**, name it `MedOrigin Core protected releases`.
2. Target **all `v*` release tags**, consistently with the repository's
   release workflow (`refs/tags/v*`), with **no exemptions by tag pattern**.
   Select **Active** enforcement.
3. Select **Restrict creations**, **Restrict updates**, and **Restrict
   deletions**. Grant narrowly scoped bypass only to the deliberately
   authorized release actor(s); verify the chosen release actor can create
   a future tag without allowing ordinary contributors to replace or erase it.
4. Read back the effective GitHub ruleset using a read-only API view, rerun
   the CLI command above, and independently review bypass actors as an
   administrator. This automated CLI cannot verify bypass actor membership
   because GitHub hides it from callers without ruleset-write permission.
5. Keep the publication feature flags disabled. Do **not** create a tag until
   ADR-0044 is explicitly resolved, historical compatibility/claim scope is
   signed off, exact main-commit CI and independent security review are
   recorded, and the owner specifically authorizes a future release.

The proposed `release.yml` contains a **read-only gate** ahead of quality,
artifact construction, GitHub Release and TestPyPI. It checks tag-to-main
commit equality and these active tag restrictions. A PR or workflow-dispatch
qualification does not publish and does not require a release tag.

**Authority boundary:** this handoff is advisory; the credential used in this
session does not have repository `admin` or `maintain` access and cannot
change rulesets. Rulesets and bypass decisions must be applied by an
authorized GitHub repository administrator.

Reference: [GitHub rulesets creation documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)
and [available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).
