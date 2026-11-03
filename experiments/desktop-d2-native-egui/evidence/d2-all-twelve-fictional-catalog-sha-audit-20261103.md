# D2 exact-source fictional fixture catalog audit — 2026-11-03

**Status:** source integrity VERIFIED; native application / network / clinical / release acceptance **NOT VERIFIED — NO-GO**. Private integration Draft PR #865, never protected main or a public artifact.

## Exact actual source checked

Read from this PR branch using GitHub source fetch, without user data, credential access, or network calls by the application:

- `experiments/desktop-d0-rust/src/lib.rs` with three built-in raw Rust byte literals, six explicit `include_bytes!` references, and the three deterministic boundary byte constructors.
- All six genuine source-controlled fictional `experiments/desktop-d0-rust/fixtures/bundle-*.json` files.
- All twelve corresponding `FixtureSpec` rows in `experiments/desktop-d2-native-egui/src/app.rs`, including expected original byte counts, 64-digit lowercase SHA-256 and synthetic FHIR-envelope status.

An independently implemented SHA-256 checker was first verified against the standard SHA-256 `abc` test vector (`ba7816bf...`), then operated on **the exact UTF-8/byte content returned from GitHub**, never on D2's claimed digest values. Result: **12/12 source byte lengths match, 12/12 independently computed SHA-256 match, 0 discrepancies**. The twelve original source byte lengths, in canonical D2 order, are:

| Fictional vector | Raw bytes |
|---|---:|
| patient-minimal | 57 |
| patient-invalid-utf8 | 1 |
| patient-over-limit | 32769 |
| patient-exact-limit | 32768 |
| observation-minimal | 251 |
| observation-bad-subject | 253 |
| bundle-valid | 531 |
| bundle-bad-reference | 528 |
| bundle-duplicate | 531 |
| bundle-wrong-type | 532 |
| bundle-linked | 559 |
| bundle-dangling | 559 |

The nine valid, bounded, text-preview sources are separate from the three intentional boundary fixtures (invalid UTF-8, oversized bytes and a 32,768-byte case). The audit checks byte length and hash **before** considering JSON parsing. Zero canonicalization or modification of the intentionally invalid/nonclinical source is permitted.

## New durable source-only gate

- `tests/verify_d2_fixture_catalog.py` — independent Python 3 standard-library implementation, derives D0 raw literals, validates the six exact D0 `include_bytes!` references and source files, reconstructs the three boundary cases, checks the complete/unique D2 12-entry catalog, exact byte count, SHA-256, and expected synthetic status, validates nine bounded preview JSON objects, and refuses symlinked bundle sources. It emits an explicitly **source-only, not-release** status even on success; input mismatch returns nonzero.
- `tests/test_verify_d2_fixture_catalog.py` — eight adversarial tests for unchanged fictional source, same-length tamper, wrong declared length, wrong expected SHA, wrong synthetic envelope status, malformed raw JSON with matching alleged SHA, duplicate original Rust literal, and incomplete catalog. The exact authored test suite was executed using Python's `unittest` in an isolated local sandbox: **8/8 PASS**, no network, Rust, Windows or PHI.
- `.github/workflows/medorigin-d2-offline-evidence-validator.yml` — added both test sources, the D0 `src/lib.rs` and `fixtures/**` paths as triggers, plus source-only unit tests and real repository catalog verification on **future eligible CI runs**. No new workflow was started for this private `[skip ci]` commit, and **no hosted exact-HEAD CI PASS is asserted**.

This turns a one-off independent source audit into a reproducible dependency-bound regression gate; it does not replace the existing Rust view-model, UIA/AX/AT-SPI or OS packet confinement tests.

## Additional frozen D0 provider routing gate

After independently verifying all twelve SHA-256 values, the Python audit was extended to ensure the nine source-previewable fixture identities have their **exact intended D0 provider mappings**, not merely the correct D2 catalog digest. For each of nine permitted source fixture IDs it now validates three separately scoped D0 match expressions: `hash_fixture_raw_v1` identity-to-size dispatch, identity-to-raw-byte dispatch, and `fictional_json_preview_v1` identity-to-source dispatch. A GitHub-source inspection of the actual D0 code checked **27/27 mappings exactly once** in the correct function scopes. This closes a source-audit blind spot where catalog hashes could still be correct even though a future D0 refactor routed an ID to a different literal.

The check purposely extracts the three real D0 dispatch scopes rather than searching the entire file: those source strings legitimately also occur in other functions, making naive whole-file occurrence counts unreliable. A local Python syntax check and re-execution of the source-only adversarial suite after this hardening remained **8/8 PASS**. The **full-checkout source verifier has not been run against a materialized complete GitHub tree**; the independent full fixture audit above did run directly against actual GitHub file content.

## Three additional end-to-end Python negative controls

The full Python auditor was also tested against a temporary, deliberately **fictional** two-project source tree with all twelve entries and all nine preview/hash/raw-byte dispatches. The test verified the clean synthetic tree and then separately modified (1) a Bundle JSON byte while leaving the old SHA catalog intact and (2) the D0 byte dispatch of `observation-minimal` so it incorrectly returned the Patient bytes. The auditor refused both mutations with explicit mismatched-source reasons, and deleted the entire temporary tree.

The three source-tree tests were added to `tests/test_verify_d2_fixture_catalog_tree.py` and the existing eight adversarial cases retained. The complete local Python unit suite ran **11/11 PASS**, using `python -m unittest discover -s . -p 'test_verify_d2_fixture_catalog*.py' -v`. The existing nonpublishing source-only GitHub workflow now runs these eleven tests and the independent full-checkout catalog command on **future eligible events**; no hosted run at this private branch HEAD has been asserted.

## Hard NO-GO and execution limits

No actual `cargo test --offline --locked --all-targets`, `cargo fmt --all -- --check`, `cargo clippy -D warnings`, exact-HEAD Windows GUI UIA/keyboard, Linux real accessibility or macOS spoken VoiceOver test ran on the new integrated commit: the authorized PC remote execution connector remains blocked by a recorded monthly usage cap and the assistant's isolated environment has no Rust toolchain. The new Python repository-wide command is saved and can run in any full checkout, but its execution against an entire GitHub checkout was **not** claimed here.

Security/release conditions remain unresolved: #662 real D1 WebView2 egress, #673 Linux transitive AccessKit/zbus5 maintenance, #676 macOS spoken VoiceOver, #622 frozen optional research dependencies, #603 independent security review and #574 owner release approval. Native D2 is still a synthetic-only developer experiment, not a clinical app, EHR importer or FHIR R4 validator. No protected-main merge, publishing, signing, installer, release or patient data use.
