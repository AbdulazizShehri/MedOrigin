# MedOrigin D2 — actual Linux Cargo dependency-maintenance gate (2026-11-03)

**Decision: NO_GO_TRANSITIVE_UNMAINTAINED. No release or clinical authorization.**

## Actual sources and context

- Repository: AbdulazizShehri/MedOrigin, stacked nonpublishing Draft PR #858, pinned D2 Cargo.toml eframe **0.36.0**, AccessKit enabled for accessibility. No disabled AccessKit or edited frozen research-root dependency metadata.
- Source-controlled diagnostic: `experiments/desktop-d2-native-egui/tests/verify_linux_accesskit_maintenance.py`. Tests: `tests/test_verify_linux_accesskit_maintenance.py`. The script calls **real** `cargo metadata --offline --locked --format-version 1 --filter-platform x86_64-unknown-linux-gnu`, reads exact resolved package IDs and traverses reachable dependencies from the actual native D2 root. No internet and no executable application launch.
- Real host: authorized Ubuntu 26.04 WSL2 via Windows device `Abdulaziz`; Rust/Cargo **1.97.1**. Only offline cached Cargo registry was used; full metadata for **247 reachable Linux packages** resolved.
- This maintenance diagnostic has no ability to declare a release PASS. It returns nonzero for known risk, source/tool failure, missing accessibility backend and even a future apparently updated graph that still needs independent review. It always sets `release_authorized=false` and `maintenance_debt_resolved=false`. It does **not** claim refreshed RustSec database or prove any exploit.

## Exact source-to-risk paths proven in local locked Linux dependency resolution

- `medorigin-desktop-d2-native-egui@0.0.0 -> eframe@0.36.0 -> egui-winit@0.36.2 -> accesskit_winit@0.32.2 -> accesskit_unix@0.21.1 -> zbus@5.19.0`.
- `medorigin-desktop-d2-native-egui@0.0.0 -> eframe@0.36.0 -> egui-winit@0.36.2 -> accesskit_winit@0.32.2 -> accesskit_unix@0.21.1 -> accesskit_atspi_common@0.18.1 -> zvariant@5.15.1`.
- `medorigin-desktop-d2-native-egui@0.0.0 -> eframe@0.36.0 -> egui-winit@0.36.2 -> accesskit_winit@0.32.2 -> accesskit_unix@0.21.1 -> zbus@5.19.0 -> zbus_names@4.3.5`.
- `medorigin-desktop-d2-native-egui@0.0.0 -> eframe@0.36.0 -> egui-winit@0.36.2 -> accesskit_winit@0.32.2 -> accesskit_unix@0.21.1 -> accesskit_atspi_common@0.18.1 -> zvariant@5.15.1 -> zvariant_derive@5.15.1`.

These align with informative unmaintained advisories `RUSTSEC-2026-0370`, `RUSTSEC-2026-0371`, `RUSTSEC-2026-0372`. They are **maintenance advisories, NOT proof of currently exploitable vulnerabilities**. Upstream accesskit_unix latest documented `0.24.0` (2026-09-25) still lists `zbus ^5.19`; therefore simply changing its version, or adding a direct zbus 6 dependency, does not fix the transitive path. See https://docs.rs/crate/accesskit_unix/latest and https://rustsec.org/advisories/RUSTSEC-2026-0370.html.

The actual CLI produced `decision=NO_GO_TRANSITIVE_UNMAINTAINED`, `maintenance_debt_resolved=false`, `release_authorized=false`, exit **3**, while a separate test wrapper confirmed the precise three unmaintained package identities.

## Regression suite

Eight meaningful test methods, all with self-contained synthetic metadata IDs and graph links; validated on **real Windows Python 3.14 (8/8 PASS)** and **real Ubuntu Python (8/8 PASS)**:
1. zbus 5 path and all three maintenance advisories => NO_GO.
2. Synthetic zbus 6 graph => still REVIEW_REQUIRED, never a release PASS.
3. Accessibility backend removed => NO_GO, not a recommended workaround.
4. Unreachable orphan maintenance package => not falsely counted as reachable.
5. Broken dependency link => NO_GO_INVALID_CARGO_METADATA.
6. Missing reachable resolution node => NO_GO_INVALID_CARGO_METADATA; repaired discovered fail-closed edge case.
7. Wrong root project identity => NO_GO.
8. Malformed root/metadata => NO_GO.

The nonpublishing GitHub Actions source-only test workflow now includes this suite and watches the two new files. **Latest exact-head hosted CI not asserted successful**: commits deliberately include `[skip ci]` under zero-cost policy.

## Release disposition

Issue #673 remains open until upstream resolves the compatible AccessKit/AT-SPI graph through zbus 6, or a source-bound, platform-limited maintenance-risk disposition is independently approved, with real UI accessibility test, fresh RustSec database, OS containment, license review, and all normal three-OS acceptance. Do not force a zbus 6 direct dependency or remove Linux accessibility to mask this maintenance debt. Separate D1 WebView2 #662, optional extras #622, macOS spoken VoiceOver #676, independent review #603 and owner authorization #574 remain unresolved.

No real patient data, installer, tag, merge, release or frozen research-root modification performed.
