# D2 secure directional JSON diff — cross-feature source contract review (2026-11-03)

**Current decision: unqualified Draft integration; RELEASE NO-GO.** This report documents review and source-only correction, **not** a new native Windows/macOS/Linux test run.

## Defect found when bringing #864 into #859

The standalone Windows JSON Pointer UIAutomation script introduced on the earlier PR #862 test baseline expected a shortened accessible text node:

`Fictional JSON path difference: /id (value differs). Structural developer hint only; original source bytes unchanged.`

The current PR #864 Rust function `fictional_json_path_diff` computes a **detailed** scalar hint with both fictional string values. Thus carrying that older UIA expectation forward as a source-verified acceptance criterion into the newer integration would incorrectly mark a correct detailed result as failed. The earlier 3/3 source-bound UIA report identifies **an older native executable and earlier source parent** and cannot be extended to the current combined head. No prior result is dismissed as false without its exact tested code.

## Exact independently checked source contracts

From `experiments/desktop-d0-rust/src/lib.rs` fixed source bytes, independently parsed using standard-library JSON and SHA-256:

| Fixed fictional source | Exact bytes | SHA-256 |
| --- | ---: | --- |
| Patient | 57 | `747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0` |
| Observation | 251 | `527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19` |

The first differing source-byte offset is **17** (zero-based); common trailing bytes **1**. Both contain `id`, which is the first alphabetically sorted common field that differs. Exact expected current Rust semantic summary:

```text
Fictional JSON path difference: /id (value differs: left="synthetic", right="synthetic-observation"). Structural developer hint only; original source bytes unchanged.
```

The source-controlled `tests/windows-native-fictional-json-pointer-uia.ps1` now independently parses these two fictional IDs from D0's fixed Rust literal source (asserting their expected allowlisted values) and constructs the detailed exact expected text, instead of its obsolete placeholder. This is strictly a developer test of built-in fictional bytes; there is no patient data, arbitrary import, filesystem read by the app, clipboard, EHR or network side effect.

## New cross-feature regression admission

- `src/app.rs` integration test `directional_semantic_and_hex_details_are_cleared_before_recomparing` now asserts **three actual changes** — JSON Pointer text, byte difference summary and HEX context — after a UI state clear and re-comparison of a *different fixed fictional pair*, rather than merely asserting those texts exist.
- A new Rust unit test `pinned_fictional_patient_observation_pointer_matches_windows_uia_contract` asserts the exact expected detailed source string from two separately re-verified D0 fixtures, preventing silent future drift between the Rust formatter and Windows UIAutomation acceptance.
- The Windows JSON Pointer UIA script now includes a **fourth** expected scenario: accessible Clear button activation must clear JSON Pointer, byte difference, HEX context, and raw comparison text. **This is source-authored, not a 4/4 executed PASS.**
- `tests/windows-offline-powershell-ast-gate.ps1` adds the integrated comparison, genuine keyboard, and JSON Pointer UIA scripts to its static parser input (7 total instead of the previous 4). **The 7-file parser run is pending** because the owner's Windows Desktop Commander monthly usage is exhausted even though paired/online.

## Evidence and release restrictions

Verified here: GitHub file/commit identity, exact fixture contents and hashes independently computed, source-specific inconsistency and correction, and inclusion of new test assertions. **Not verified at this combined head**: `cargo test --offline --locked`, Rustfmt, Clippy, actual Windows 4-case UIA, actual Windows keyboard flow, macOS VoiceOver, independent Linux AT-SPI, signed build, or Windows WFP/DNS/TCP/UDP packet containment. GitHub-hosted exact-head CI runs **0** at the source review checkpoint; commits retain `[skip ci]`.

The parent PRs #859 and #864 remain separate, private, open, and unmerged. Integration PR #865 remains private Draft, with no protected main merge, release, patient data, installer, signing or publication. Hard NO-GO blockers #662, #673, #676, #622, #603 and #574 remain open.

**Resume exact-head native acceptance only from the current GitHub PR #865 SHA** when an authorized zero-cost Windows runner is available; never reuse prior debug executable hashes or pre-integration UIA receipts.
