# D2 actual-preview byte integrity hardening — 2026-11-03

**Private Draft PR #865 only; release, clinical workflows and PHI remain strictly NO-GO. No exact-HEAD compiled Rust/UIA/CI green result is claimed.**

## Source-backed defect and actual code change

D2 previously verified raw digest metadata from D0's source-compiled fixture catalog and the preview provider's reported SHA-256, and verified returned JSON's byte **length**, but did **not** hash the **actual `raw_json` returned for UI display/comparison**. Although D0 currently returns a shared fixed fictional source, an accidental future mismatch between provider metadata and returned display text could cross this provenance boundary unnoticed. This change adds a second exact byte-level digest check, before exposing any raw fictional JSON in the GUI.

File: `experiments/desktop-d2-native-egui/src/app.rs`.

- New `verified_fictional_preview_bytes(FixtureSpec, &str) -> bool` returns false unless exact `raw.len() == fixture.bytes` and `raw.len() <= 2048`; it computes SHA-256 from **`raw.as_bytes()`**, renders lowercase 64-digit hex and compares it against the original fixed catalog SHA. It does not parse/normalize user content, load files, open sockets, invoke subprocesses or claim memory zeroization.
- `preview_selected` (in-app read-only inspection) and `verified_json_for` (both sides of read-only comparison) **both** now require that independent byte hash, in addition to their existing D0 raw SHA, metadata/contract, limited synthetic FHIR envelope and no-release conditions. Their previously established refusal handling clears stale prior preview/comparison state.
- A dedicated Rust regression `fictional_preview_hash_checks_returned_bytes_not_only_provider_metadata` now covers original source, a **same-byte-length** mutation with unchanged metadata, a substituted catalog SHA, a 2049-byte raw input, and all available fixed fictional JSON preview vectors. These are authored tests **awaiting actual Rust compilation/execution**.
- `Cargo.toml` adds direct `sha2 = { version = "=0.11.1", default-features = false }`. The crate, its transitive dependencies and its exact registry checksum were **already present** in the locked D2 `Cargo.lock` because D0 already depends on exactly `sha2 0.11.1`. Only the existing D2 package dependency list in `Cargo.lock` was updated to include `"sha2"`. No new version, network client, browser, or OS policy introduced.
- Source inspection confirms this hasher mirrors D0's own SHA-256 implementation and that the call is present at **both** raw-preview exposure boundaries. D2's browser-free boundary source policy was left unchanged.

## Verified locally without a Rust runner

An independent local Python stdlib SHA-256 check using the exact fixed D0 fictional Patient JSON:

- `{"resourceType":"Patient","id":"synthetic","active":true}` — **57 UTF-8 bytes**, SHA-256 `747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0`, matching D0 catalog.
- Same-length mutation replacing `synthetic` with `synthetix` — **57 UTF-8 bytes**, SHA-256 `eb90a0d64dd27ecda3a2740cd9ece68d496e4524ad3c1c980c21283282f41961`, correctly distinct from the compiled SHA. This is an **independent test-vector check**, not proof that the unrun Rust test passes.
- Current GitHub source confirmation: Rust helper is present; two call sites in `preview_selected` and `verified_json_for`; `Cargo.toml` exact pinned version and corresponding locked package dependency; source-authored Rust tests present. No rustc/cargo toolchain was available in the assistant's isolated sandbox, and owner PC Desktop Commander remains capped at monthly usage, so **no exact-integrated-HEAD `cargo test --offline --locked`, formatting, Clippy, real Windows UIA, Linux AT-SPI, or macOS native acceptance was executed**.

## Important source test blocker corrected before native compilation

After adding the direct `sha2` dependency, a fresh review of the existing `tests/browser_free_boundary.rs` discovered a concrete failing assertion in `direct_dependencies_remain_limited_to_native_ui_and_existing_d0`: it previously expected exactly **three** manifest direct dependencies, `eframe`, D0 and `serde_json`. The new fourth dependency would fail the safety test even though `sha2 0.11.1` was already resolved and locked transitively.

The source-guard assertion was **updated to admit precisely one reviewed fourth dependency, `sha2`**, while continuing to reject unreviewed additions, browsers, HTTP clients, socket/process APIs, unexpected source modules, and changes to native eframe/AccessKit features. It also now checks the exact `sha2 = { version = "=0.11.1", default-features = false }` manifest line, the `sha2 0.11.1` locked package and the D2 root package's explicit `"sha2"` lock dependency. That preserves the existing fail-closed policy rather than weakening it to accept arbitrary crates.

Independent GitHub-source checks against the *current* integration branch confirmed **7/7 static invariants**: four expected direct dependency names, the Rust test's expected allowlist, exact manifest pin, root lock wiring, existing locked package, continued browser/client refusal, and independent hashing at both raw preview exposure sites. The earlier **13/13 static source/lock assertions** from the initial SHA change also passed before this guard fix. These are independently executed **static source checks, not Cargo tests**.

No actual `cargo test` or `cargo fmt --check` result is yet available at this branch head, since the authorized Windows device connector still has a monthly execution quota block. The code and tests remain unmerged in Draft #865; the change is not a release authorization.

## Follow-up acceptance and hard gates

Before merging even into a development base, run on the **exact new #865 HEAD**: `cargo test --offline --locked --all-targets`, `cargo fmt --all -- --check`, `cargo clippy --offline --locked --all-targets -- -D warnings`, exact-hash Windows UIA four-case JSON Pointer and keyboard/clear flows, and Linux/macOS accessibility. Independent security review and OS-level packet isolation are still required before release. No hosted CI success is inferred from previous PRs or a successful file SHA comparison.

Out of scope: real patient data import, EHR interoperability, full FHIR R4 clinical validation, protected main, signed binaries, installers, public distributions and publication. Existing #662 WebView2 TCP/DNS egress, #673 Linux AccessKit transitives, #676 spoken VoiceOver, #622 optional frozen research advisories, #603 independent security review and #574 founder release authorization remain OPEN/NO-GO. No duplicate automation or changes to host firewall, WFP, ETW or global Edge/WebView2 policy.
