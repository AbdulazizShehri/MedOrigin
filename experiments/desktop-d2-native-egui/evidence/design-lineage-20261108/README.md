# Claude Design implementation: Lineage identity and 28-screen navigation (2026-11-08)

- **Design source:** the Claude Design canvas "MedOrigin Desktop", board "Desktop — Encounter review (all 28 screens in nav)" and the "Lineage — identity" board. The repository copy is PR #1011 (`ab6b4b8`), merged into this branch: `docs/design/desktop-v1/`.
- **Build:** `cargo build --release`, Windows 11 x64, rustc 1.97.1. The EXE SHA-256 of the local QA binary is recorded in the commit message. The build is not reproducible across hosts.

## What was implemented in the native app
- **Tokens:** every light and dark colour in `tokens.json`, plus the board's pink, blue and mint tag colours. Type sizes 11/12/13/16/22 and layout widths 244/52/320. A test (`theme::palettes_match_the_committed_design_contract`) reads `tokens.json` and fails on any drift. A second test checks WCAG AA contrast for every text/surface and tag pair.
- **Lineage mark and app icon:** the committed SVGs (`lineage-mark.svg`, `lineage-mark-on-dark.svg`, `lineage-app-icon-dark.svg`) were rendered unchanged with resvg 0.45 to raw RGBA in `assets/lineage/`. The logo is not redrawn in code. `theme::lineage_rasters_come_from_the_committed_svgs` re-hashes the SVGs and the rasters against `assets/lineage/MANIFEST.txt`. The window icon is the dark app icon.
- **Navigation:** all 28 `FEATURE_COVERAGE.md` screens in the board's eight groups (`src/screens.rs`). A test pins the count against `FEATURE_COVERAGE.md` and pins the board's tags: Audio & transcript, Orders & tasks and Model catalog & runtime are Gated; Coding suggestions is Deferred; FHIR fixture inspector is Exp.
- **Gates:** Gated and Deferred screens are disabled buttons. Screen readers hear the tag in the name ("Audio & transcript Gated"), and hovering shows the reason. `open_screen` refuses them (tested). The board's header actions "Export to quarantine" and "Send for clinician review" are shown disabled, with reasons.
- **Routes:**
  - **Working screens:** Home; Synthetic patients, Encounters and FHIR workspace (the records view, each applying its type filter); FHIR fixture inspector (the existing developer view); Settings; About & diagnostics; Help & safety.
  - **Not-connected screens:** each says "Not connected yet", quotes its design-contract status and backing modules, and offers only a real action (Open FHIR workspace) where one exists. Nothing is simulated.
- **Inspector** (records screens, window width ≥ 1100): source, flagged notices, and a provenance chain that marks only what really happened. FHIR R4 profile validation shows "Not performed" and clinician sign-off shows "Not available".
- **Keyboard:** Ctrl+K searches screens (Enter opens the first enabled match). Ctrl+1/2/3 open Home / FHIR workspace / FHIR fixture inspector. F1 opens Help & safety. Esc clears.

## Captures (real app, driven through Windows UI Automation)
`home-light.png`, `encounters-light.png` (built-in sample open, Encounter filter applied), `status-not-connected-light.png` (Patient graph), `fhir-workspace-dark.png`, `about-dark.png` (bottom strip cropped to remove an unrelated desktop notification).

## Verification on this tree
- `cargo fmt --check` and `cargo clippy --all-targets -D warnings` are clean.
- `cargo test`: 130 + 15 + 7 tests pass.
- `tests/windows-native-uia-smoke.ps1`: `D2_NATIVE_UIA_4_OF_4_PASS`. It now opens "FHIR fixture inspector" by prefix, because navigation names include their tag.

## Known gaps against the board
- **Fonts:** Inter and Instrument Sans are not bundled, so egui's default font is used. Bundling them needs a font-file and licence review.
- **Icons:** the board's per-item stroke icons are not drawn yet.
- **Note-draft content:** the board's encounter note draft (Subjective/Objective/…, citations, contradiction card) is illustrative. No draft generation exists in the desktop app, so that content is not reproduced as if it worked.
- **Records view:** the bundle view was restyled afterwards (see `evidence/records-restyle-20261108/`). The Core batch, audit and focused-workspace views still use the older developer layout.
- **Not run:** the Linux AT-SPI script was updated (new label, wider Tab bound) but is verified only in CI.
- **Scope:** fictional data only. This is not evidence of clinical, PHI or network-isolation readiness.
