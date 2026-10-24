# MedOrigin Core — protected v-tag governance and read-only owner review

**State (2026-10-24): Active protection verified; publication remains NO-GO.**
This page does not approve a tag, a release, a merge, clinical use or external distribution.

## Verified repository configuration

- Repository: [AbdulazizShehri/MedOrigin](https://github.com/AbdulazizShehri/MedOrigin)
- Protected `main` ruleset: **20172239**.
- Active release-tag ruleset: **25773765**, name `MedOrigin protected release v-tags v1`, matching `refs/tags/v*` with **no exclusions**. Creation, update and deletion are restricted.
- The repository administrator readback returned the *only* configured bypass actor as `RepositoryRole` ID `5` (Administrator), mode `always`. No tag was created or moved. Existing `v0.1.0`/`v0.2.0` references were preserved.

**GitHub permission limitation:** a non-admin ruleset API response masks `bypass_actors` as null, even if the active ruleset has an admin-only bypass. The GitHub Actions `GITHUB_TOKEN` is not a substitute for an administrator's verified ruleset read. Do not add an administrator PAT or write-capable token to a PR-triggered workflow, source code, build job or artifact.

## Two distinct read-only checks

1. **CI tag protection presence** (read-only/default; usable with `GITHUB_TOKEN`):

   ```shell
   python scripts/check_release_tag_governance.py --repository AbdulazizShehri/MedOrigin --tag-ref refs/tags/v0.3.0
   ```

   `RELEASE_TAG_RULESET_PRESENT_ONLY` means the active v-tag restrictions were seen; `bypass_actors_verified: false` means that the API caller could not verify exemptions. It is **not** a publisher go-ahead. The existing `release.yml` uses only this nonpublishing rule-presence test.

2. **Administrator-only bypass review** (read-only/manual; run outside untrusted CI):

   ```shell
   python scripts/check_release_tag_governance.py --repository AbdulazizShehri/MedOrigin --tag-ref refs/tags/v0.3.0 --verify-bypass-actors
   ```

   An authenticated repository administrator must see `bypass_actors_verified: true`, the expected ruleset ID and `issues: []`. Missing/masked exemptions, an unexpected team/app/non-admin bypass, a disabled rule or an unexpected condition fails closed. Save the reviewer identity, ruleset ID, command result, date and exact candidate SHA as a separate independent release review receipt. Do **not** copy the admin credential into that receipt.

Neither command creates an actual `v0.3.0` tag. Both always report `publication_authorized: false`. A `GITHUB_TOKEN` run can confirm only the first, less privileged, condition; successful administrator review is separately required before any future release approval.

## Other publication prerequisites (all remain independent)

- The exact source and binary candidate must pass complete Linux Python 3.11/3.12 CI, Core and read-only artifact qualification, security scanning, and source-to-artifact review [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603).
- Resolve ADR-0044 identity and release/version policy, scope and the *known incompatible* v0.2.0 historical persisted dataset validation in [#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574). No silent migration, byte rewrite or clinical-data use.
- Require an **independent reviewer** who signs the exact candidate SHA and an operator's separate explicit permission to create a protected release tag or enable GitHub publishing.
- Keep `GITHUB_RELEASE_PUBLISH_ENABLED` and `TESTPYPI_PUBLISH_ENABLED` disabled until they are individually authorized. GitHub Actions PR and manual qualification paths are read-only; do not confuse passing CI with publication authority.

**NO-GO until all required evidence and approvals exist.** Never infer completion from this administrator handoff alone.
