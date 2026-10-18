# MedOrigin — v0.3.0 Core developer package candidate qualification

- **Status:** Engineering review candidate only; neither approved nor published
- **Proposed SemVer:** `medscale 0.3.0`; original `v0.2.0` tag remains immutable
- **Scope:** Python Research Core developer preview on synthetic-only fixtures
- **Governance:** [release decision issue #574](https://github.com/TheHalfMoon/MedOrigin/issues/574), [ADR-0010](../adr/0010-release-architecture.md), [ADR-0011](../adr/0011-versioning-licensing.md), [ADR-0020](../adr/0020-public-api-stability.md)

## Exact review candidate scope

This preparation branch changes `src/medscale/__about__.py` to `0.3.0`.
Hatch dynamically derives wheel/sdist version metadata, and `medscale
--version` reads the same source. `CITATION.cff` advertises the candidate
package version **without `date-released`**, which must be bound to a later,
separately authorized tag/release. The historical `RELEASES.md` v0.2.0
release date, source and tag are unchanged.

The standalone Workspace distribution remains independently versioned as
`medscale-workspace 0.1.0.dev1`; this Core candidate neither republishes
nor changes Workspace. Package imports and original `medscale` CLI name
are preserved; the project/repository's public brand is **MedOrigin**.

## Proven and unproven historical compatibility

The [historical compatibility preflight](historical_compatibility_preflight_574.md)
records static evidence: unchanged root exports and public facade sources;
seven legacy CLI commands remain; six additive dispatchers have appeared.
Independent synthetic Windows differential evidence is preserved in
[PR #583](https://github.com/TheHalfMoon/MedOrigin/pull/583):
the help text for all seven legacy subcommands was byte-identical,
11 top-level public exports and 24 public callable signatures were
identical, but `dataset freeze` behavior is materially different.
Historical frozen output was invalid on its own validator due to stale
manifest SHA-256 and license checksum handling, while current outputs
validate under the current code; **old-on-new and new-on-old validators
were not both compatible**. A no-downgrade policy is required, and no
historical receipt may be rewritten in place.

### Open compatibility gates

- [ ] Validate full execution, persisted identifiers and semantic behavior
  of every historically stable CLI/API surface under Python 3.11 and 3.12.
- [ ] Approve any append-only legacy dataset import/migration format
  policy under ADR-0017/0020; never silently rewrite historic evidence.
- [ ] Decide if the four legacy project URLs in the **frozen**
  `pyproject.toml` are acceptable as redirects temporarily, or record
  an explicit successor-root-input identity/reconciliation authorization.
- [ ] Verify this exact PR head under all CI/CodeQL and applicable
  optional-backend/release-source smoke checks; capture exact hashes.
- [ ] Obtain explicit final version/tag/public-GitHub-Release approval
  and CI-only publication authorization separately.

## Quality gates for candidate preparation

The PR-safe release workflow must hash-bind a source-derived
`SOURCE_VERSION` in the artifact payload, verify it in the clean wheel
smoke along with installed package metadata/CLI, and **never** invoke a
tag/GitHub Release/TestPyPI step for an ordinary PR. No publisher variable
or environment is enabled by this document.

Core research lock/static prerequisites remain **byte-identical**:
`pyproject.toml` SHA-256
`c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510`;
`uv.lock` SHA-256
`6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4`.
The research MRL-0809, MRL-0899 and clinical CW-021 gates remain
unclosed. No GPU training, patient data, hosted EHR writes or clinical
release authority follows from a passing Python package workflow.

This file is a **non-authorization**: a reviewed, green candidate PR is
not a public release, product launch, scientific result or clinical tool.
