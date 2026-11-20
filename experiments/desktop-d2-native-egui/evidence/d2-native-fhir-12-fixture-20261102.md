# D2 native FHIR-shaped fixed-fictional extension — 2026-11-02

Scope: source-only, no release, no patient data, no WebView, no model, no network operation or file importer. Windows developer PC used; D2 native eframe source pulled from independent Draft #830 exact parent `6b7551adbe77b3fe49677c0871ab7d309482810a`. D0 fixed test corpus copied from separate D1 Draft #840 exact source SHA `0997e713941f90cb2ede7366521d20b3ac153224`, **not merged** as a Git branch or publication decision. The separate integration requires human source-level review before combining Drafts.

## Actual new behavior

Native D2 now offers 12 bounded, compiled-in, fictional D0 Rust samples: the same four original Patient SHA vectors plus two fictional Observations and six fictional Bundles with valid local references, missing references, duplicate fullUrls, a disallowed transaction type, and a correctly matching or dangling URN. It validates `sha256`, byte count, hash-contract/fixture ID, FHIR envelope contract/status and fixed negative flags using only in-process Rust. For deliberately malformed samples, a successful verification means **this negative test was correctly detected**, not that a real FHIR resource is valid.

The original four visible fixture selectors and `Verify synthetic SHA-256` button remain in their prior sequence so previously established Windows UIA and Mac AX/keyboard test actions are not silently reordered. The other eight fixtures are under an initially collapsed `egui` section after the original Verify button. Results explicitly state `NOT full FHIR R4 validation`, `NO-GO` release, no patient data and no network isolation qualification. An invalid programmatic selector fails closed without panicking.

No Tauri/WebView2, `std::net`, remote FHIR calls, EHR integration, PHI, model, telemetry, persistence or arbitrary input is added. `AccessKit` remains enabled; the Linux zbus 5 unmaintained advisory chain (#673) has **not been fixed**.

## Qualification evidence

Local authorized Windows Rust 1.97.1: D0 `cargo test --offline --locked --all-targets` PASS (5 library + 2 bundle + 2 envelope + 3 Observation = 12 tests). D2 `cargo test --locked --all-targets` PASS (4 app behavior tests and 6 browser/network source tripwire tests, 10 total); D2 `cargo clippy --locked --all-targets -- -D warnings` PASS and D0/D2 `cargo fmt --check` PASS. `Cargo.lock` is refreshed only within isolated D2 for explicit new D0 `serde_json` dependency. No cargo-deny RustSec remediation claimed. Hosted exact-head Windows/Linux native tests should be checked on the pushed commit before claiming hosted qualification.

**Known limits:** No actual macOS AX/VoiceOver testing of changed UI was performed; the previous Mac 4/4 technical AX/keyboard evidence was for the old four-selector version and cannot be transferred blindly. Source guard tests are not OS packet confinement. #662 G3 BLOCKED, G4/G5 NOT_RUN, G7 BLOCKED; #673 Linux maintenance, #676 spoken VoiceOver, #603 independent security, #622 optional research advisories and #574 owner release approval all remain OPEN/NO-GO. No merge to protected main, tag, installer, registry push or signed release.
