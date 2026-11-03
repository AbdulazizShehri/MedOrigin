# D2 fictional FixtureSpec catalog — unparsed-source rejection (2026-11-03)

**Private Draft PR #865, source-only engineering. Release NO-GO.**

## Defect found and fixed

Before this revision, the Python verifier's `catalog(source)` used `pattern.finditer(FIXTURES_BODY)` and validated only the extracted 12 matching `FixtureSpec` rows. Text or a malformed 13th entry **outside** those matches could be silently skipped. This could falsely accept an unreviewed Rust source edit despite the twelve original SHA-256 digests still being correct.

`experiments/desktop-d2-native-egui/tests/verify_d2_fixture_catalog.py` now verifies that **every byte of the Rust `FIXTURES` array body** is consumed as one of exactly 12 recognized entries or an allowed separator (whitespace and at most one comma). Noncanonical text, comments, unrecognized extra FixtureSpec, or injected Rust-like statements cause `UNPARSED_FIXTURE_CATALOG_CONTENT` refusal. The previously established fixed-index selector order guard and source SHA/size/status checks remain unchanged.

## Adversarial coverage and actual execution

`experiments/desktop-d2-native-egui/tests/test_verify_d2_fixture_catalog.py` adds three source-only tests: an otherwise valid 12-row synthetic catalog; an unparsed 13th entry after the valid rows; and injected Rust-like tokens between two valid entries.

**One real test-source defect was discovered during execution:** the initial positive synthetic row constructor omitted the required Rust comma after `status`. The first local scoped test run therefore **failed** rather than proving the new guard. The synthetic test constructor was corrected in the committed source to emit `status: "...", },`. After that fix, an isolated Python 3.13.5 execution of the equivalent scoped parser and synthetic source cases completed **5/5 PASS**: valid canonical catalog, unparsed extra entry, injected text, trailing comment, and SHA-correct reorder. These locally executed controls reimplemented the small catalog function and do **not** constitute an execution of the entire exact current GitHub Python suite.

Separately, the **actual complete D2 Rust `src/app.rs` returned by the connected private GitHub source** was inspected with an independent delimiter-aware source checker: **12/12 recognized `FixtureSpec` entries**, all 13 pre/inter/post-entry gaps contained only allowed whitespace/comma separators, every SHA was 64 lowercase hex characters, and fixture names appeared in exactly the expected order. GitHub source blob `391b8d00e19a526d96607a9c0de93545f5d834b3` was the checked input.

The repository's authored Python unit suite now has **20 test methods** (11 in helper tests, 9 in temporary source-tree tests). The earlier byte-identical, twice-executed **17/17 PASS** applies to previous exact test blobs and is not silently carried forward. **The new 20-test full suite has not been executed on this exact HEAD**. The existing source-only GitHub workflow will discover it for a future eligible run, but no hosted CI PASS is claimed.

## Invariants not proved

The source audit cannot substitute for `cargo test --offline --locked --all-targets`, Rustfmt/Clippy, real Windows GUI/UIAutomation and exact installer tests, Linux AT-SPI, macOS spoken VoiceOver, app-scoped Windows WFP process-tree/TCP/UDP/DNS packet isolation, independent publisher/security assessment, medical FHIR R4 validation, real patient-record handling or release authorization.

The current local sandbox lacks `cargo` and `rustc`; Desktop Commander had earlier paused remote Windows calls at the monthly device usage cap. No protected main merge, release, tag, signing, installer, public publication, production or PHI was undertaken. Hard NO-GO blockers #662, #673, #676, #622, #603, and #574 remain open.
