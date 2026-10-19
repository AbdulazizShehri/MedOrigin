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

### Fail-closed freeze integrity safeguard (candidate, subject to governance)

A read-only old-v0.2-to-v0.3 differential proved that running the newer
`medscale dataset freeze` against an existing historical dataset would
**silently overwrite the old manifest and checksum receipts** and then pass
validation, erasing the earlier bytes. The candidate therefore rejects
`freeze` when existing `checksums/*.sha256` evidence is present, or an
existing manifest carries a nonempty `dataset_fingerprint` or is unreadable.
This is a deliberate, test-covered **fail-closed behavior change** under
ADR-0030, not proof that old artifacts are importable. The ordinary
pre-freeze `manifest --write` workflow may still generate its unsigned
draft before the first freeze. To migrate an older artifact, preserve
its original bytes and use a distinct new dataset identity and a
separately approved append-only migration protocol; do not re-freeze it
in place. The founder's acceptance of this successor-policy change
under ADR-0017/0020 is addressed for the *bounded source-candidate safety default*
by the [compatibility disposition](v0_3_0_compatibility_disposition_574.md).
This does not authorize a historical-data migration, publication or a change
to frozen root package metadata; those require separate accepted decisions.

### Open compatibility gates

- [ ] Validate full execution, persisted identifiers and semantic behavior
  of every historically stable CLI/API surface under Python 3.11 and 3.12.
- [x] State the fail-closed no-rewrite/no-auto-migration *source-candidate*
  policy in [compatibility disposition](v0_3_0_compatibility_disposition_574.md).
- [ ] Obtain separate approval for any future append-only historical
  import/migration format under ADR-0017/0020; do not imply it exists.
- [x] Disclose the four historic MESC URL redirects as a *temporary,
  unpublished-source* limitation in the
  [compatibility disposition](v0_3_0_compatibility_disposition_574.md).
- [ ] Obtain a governed successor root-input reconciliation before
  an official MedOrigin-branded release; frozen evidence stays immutable.
- [x] Verify source-candidate head `7408827680bfa6999bfe5c3ae97ef735cec2c7f8`
  in CI, CodeQL, installed-wheel matrix and nonpublishing artifact round-trip;
  all completed successfully (see PR #584 exact-head receipts).
- [ ] Requalify any later changed head before its merge/release decision.
- [ ] Obtain explicit final version/tag/public-GitHub-Release approval
  and CI-only publication authorization separately.

## Quality gates for candidate preparation

The PR-safe release workflow must hash-bind a source-derived
`SOURCE_VERSION` in the artifact payload, verify it in the clean wheel
smoke along with installed package metadata/CLI, and **never** invoke a
tag/GitHub Release/TestPyPI step for an ordinary PR. A tag push cannot
publish a GitHub Release unless the separately approved
`GITHUB_RELEASE_PUBLISH_ENABLED` repository variable is explicitly `true`;
TestPyPI remains separately guarded by `TESTPYPI_PUBLISH_ENABLED` and its
external environment/trusted-publisher requirements. No publisher variable
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
