# D2 native browserless source-provenance Slice 7 — 2026-11-04

**Base:** [draft PR #867](https://github.com/AbdulazizShehri/MedOrigin/pull/867) exact head `e9c02592a1eb4395859bf4d0a11b739859485d80`, deployed into a new independent Windows Git worktree. Not applied to protected `main`, D0 canonical research files, Ink's Tauri draft, Python Core or Workspace.

## Purpose and scope

The D2 `eframe 0.36` native Rust host already includes an in-process SHA-bound viewer for 12 fixed fictional D0 cases and read-only comparison. This change adds a distinct, **explicit user-requested, source-verified bounded relationship viewer**, a first step toward native provenance features without inheriting D1/Tauri's observed WebView2 egress.

The existing D0 corpus has **no event dates**. The implementation therefore explicitly states `No recorded event dates in these source files; chronology unavailable.` and refuses any newly introduced, unreviewed date fields. It **does not copy** Tauri's two date values from a different fixture set, invent a timeline, or claim clinical FHIR validation.

The new `Inspect verified fictional relationships (read-only)` action independently re-verifies the exact in-memory source via D0 SHA-256 and envelope contract before projecting **only three reviewed source fixture IDs**:
- `observation-minimal`: one `/subject/reference` → `Patient/synthetic` relationship
- `bundle-valid`: `/entry/0/resource` Patient membership, `/entry/1/resource` Observation membership, `/entry/1/resource/subject/reference` → `Patient/synthetic`
- `bundle-linked`: same two member pointers and a Bundle-URN subject reference to the fixed Patient `fullUrl`

The projection checks actual embedded JSON fields, exact resource types/IDs, Bundle type, both fixed fullUrls, exactly two entries, and expected reference targets before showing each result. Source fixture ID, exact bytes and SHA-256 appear beside pointer-based developer evidence. No free-form JSON, paths, EHR URLs, browser, IPC, network connector, model, uploader, user files, clipboard or PHI.

Changing either fixture selector, verifying again, clearing with Escape, attempting an unapproved fixture or failing a source/hash contract removes existing relationship evidence. Prior four accessible primary fixture selectors and Verify button keep the same order to preserve previous accessibility qualification.

## Qualification on exact tree

| Gate | Status |
| --- | --- |
| D0/D2 12-source fixture catalog audit | **PASS**: 12/12 verified and 9/9 permitted raw-preview hashes |
| Python source-only catalog mutation unit tests | **17/17 PASS** |
| Native Rust `cargo fmt --all -- --check` | **PASS** (Rust 1.97.1) |
| Native Rust `cargo test --locked` | **PASS**: **19/19 native app unit tests**, including three new relationship/mutation/reset tests; **6/6 browser-free/source-layout guard tests**; **0** doctest failures |
| Native Rust `cargo clippy --locked --all-targets -- -D warnings` | **PASS** on exact Windows worktree |
| Existing no-browser / source-layout guard | **6/6 PASS**, unchanged dependency graph and exactly three authored D2 `src/*.rs` files, no network API or browser stack introduced |
| Real Windows D2 executable and exact SHA-256 | **PASS** `cargo build --locked`, exact compiled unsigned native debug binary SHA-256 `5E8BF9F71721126A338A4E7FE7B567ED2C1E4DBC307858855B34654352E8A53B` (on D:\\ for isolated Rust targets; not packaged or installed) |
| New Windows source-bound UIAutomation (Observation, Bundle, stale state, negative fixture) | **4/4 PASS** on same SHA-bound executable; accessible button interaction through real Windows UIA, checks exact source SHA, JSON pointers, no-dates notice, clear on reverify, and negative case |
| Pre-existing native Windows UIA regression on same executable | **PASS**: original Patient 4/4, additional FHIR 8/8, fictional JSON source preview 3/3, comparison 3/3. Existing compare script now boundedly waits for the asynchronously re-rendered button after a selection; no product change or relaxed assertion. |
| Native Windows D2 process-tree socket snapshot | **6 snapshots, 0 observed nonloopback TCP or bound UDP endpoints, exit 3 = NO-GO**; not OS packet/firewall/DNS/QUIC proof and not zero-egress qualification |
| Native macOS AX, Linux AT-SPI regression on this exact new head | **NOT RUN** |
| Actual OS network packet-level denial, real patient/clinical release | **NOT QUALIFIED / NO-GO** |

## Release security limitations

D2's existing browser-free source contract and testable native accessibility are promising, but **do not by themselves establish OS-level absence of all network traffic** or end-to-end medical safety. D2 still needs network policy enforcement or qualified host confinement, independent assessment, transitive dependency maintenance (#673), full patient/workspace feature parity, real consent and clinical approvals, voice/accessibility signoff and release governance. The Tauri WebView2 external egress blocker [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662) remains independently open. No release, signing, PHI, production installation or main merge is authorized.

No new Rust dependencies, `Cargo.lock` change, network policy or global OS modifications in this slice.
