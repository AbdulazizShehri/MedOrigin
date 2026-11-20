# Records view restyle to the Claude Design board (2026-11-08)

- **Source:** the commit that adds this file on `integration/medorigin-product-20261108`. Its parent is `1759ace`.
- **Build:** release build on Windows 11 x64 with rustc 1.97.1. EXE SHA-256: `26dc2a2fe2e11ee677886cf36f951b2c28d25777c5cc14d76fe0e73e867f725e`. This identifies the local QA binary only; the build is not reproducible.

## What changed
- **Layout:** the fictional FHIR bundle view follows the board.
  - A title ("Fictional FHIR bundle") with a "Not reviewed" tag and a one-line summary.
  - A filter card: patient segments with Previous/Next, type segments, and search with Ctrl+F.
  - A **Records** list with type badges (Patient, Encounter, Observation) and an "opened" marker. The selected row is highlighted.
  - A **Record** detail card: verified fictional URN, outgoing and incoming references, Back with a step count, and the no-clinical-content note.
  - Close bundle and the collapsed source evidence sit at the end.
- **Same behaviour:** the actions, guards, bounds and fail-closed checks are unchanged. Only the drawing code changed.
- **Accessibility contract:** each control keeps its reviewed accessible name (for example "Bundle: Open Observation/fictional-observation-001" or "Bundle: 4 of 8 fictional resources visible") through an explicit `widget_info` label, while its visible copy follows the board. Segments and records also expose their selected state.
- **Header and sidebar:** the Synthetic tag's accessible name is "Synthetic data: fictional demo, not for clinical use". The sidebar shows "Source: …" (accessible "Core status: …"). The header button reads "Clear local session".
- **Navigation:** closing records while on a records screen now returns Home, where records are opened. This is unit-tested.

## QA scripts updated for the new shell
- `windows-synthetic-multipatient-bundle-uia.ps1`:
  - Expects Home ("Welcome to MedOrigin") at start and after clearing.
  - Press falls back to the Toggle pattern for selectable controls.
  - Search48 ignores the sidebar's "Search screens" field.
- `windows-native-typed-fictional-path-uia.ps1`: path-field lookups ignore the sidebar search.
- `linux-native-fhir-atspi-qualification.py`: identifies the window by Home plus the "FHIR fixture inspector" navigation item. Before this fix, the script failed from `1759ace`, which made Home the start screen. Verified in CI only.
- `macos-synthetic-multipatient-bundle-ax.swift`: the post-clear expectation becomes "Welcome to MedOrigin". **Not run** (no macOS host).

## Verification on this build
- `cargo fmt --check` and `cargo clippy --all-targets -D warnings` are clean. `cargo test`: 130 + 15 + 7 pass.
- Windows UIA, all passing on the EXE above:
  - bundle default, embedded demo, 48-record stress, and 48-record search;
  - typed path;
  - smoke 4/4.
- The typed-path script failed once in three runs earlier (the file was refused once). Typing and admission were then checked separately and passed. Two consecutive script runs passed.
- Stdin-fed bundle modes need `[Console]::InputEncoding=[Text.Encoding]::ASCII` on this host. Otherwise .NET prefixes the piped bytes with a UTF-8 BOM, which the app correctly refuses. This is a property of this host, not of the app.
- Not run: OLE drag-drop (it moves the real mouse), macOS AX, and Linux AT-SPI (CI only).
