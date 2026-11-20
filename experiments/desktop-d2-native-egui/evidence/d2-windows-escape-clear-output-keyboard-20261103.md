# MedOrigin D2 — Windows keyboard Escape / explicit clear-output acceptance (2026-11-03)

**Scope: local native synthetic-only Windows GUI; NOT a release, network-confinement proof, medical/PHI workflow, or full accessibility certification.** Private Draft PR #859, protected main untouched.

## Exact source and binary

- Source branch: `feat/medorigin-d2-fictional-compare-20261102-run11`.
- Native app and Rust test introduced at commit `0b4847f8233a05e01442b1d23257e5ff44588ea6`.
- Windows keyboard acceptance expanded to the new controls at `53601bc92dc78378e8ec093b51570ad3a8fe7def`, with a corrected deterministic reverse-focus test at `2cecc2b59e0b21c7822057623df0c572b7368dca`.
- Exact Windows local debug executable SHA-256: **`E0A3EEDD7235B8DDAE8B70B61C70A5044527D5F8379CF37E3F077E6D0E545C49`** (unsigned QA artifact only; no installer or publishing). Test harness pins the exact executable basename and caller-supplied digest before launching.
- Actual authorized Windows PC, existing source-locked Cargo registry, no new dependency installation, `cargo test --offline --locked --all-targets` **15/15 PASS**: nine native Rust synthetic UI/view-model tests and six browser-free/network-source boundary tests.
- `cargo fmt --all -- --check` **PASS**, `cargo clippy --offline --locked --all-targets -- -D warnings` **PASS**, `cargo build --offline --locked` **PASS**.
- All actual Rust test/build checks used exact application source from GitHub commit `53601bc9`; subsequent `2cecc2b5` changed only the PowerShell test, not Rust source or Cargo manifests.

## Actual changes

The D2 native Rust UI now provides `Clear fictional output (Escape)`, an explicitly Tab-reachable and Space-activatable button, and handles `egui::Key::Escape` as an alternative. Both call one narrow `clear_fictional_output` method which removes already displayed verification result, raw fictional JSON preview, notice, and side-by-side fictional comparison while keeping the same allowlisted selection indices. All values derive from compiled synthetic fixture sources only. This is **UI-state clearing, not guaranteed zeroization of allocated memory**; no new files, patient data, EHR, clipboard, sockets, model inference, packaging or privileges.

The new Rust unit test covers clearing comparison, a successfully rendered fictional JSON preview, and an unavailable-preview notice while preserving choices.

## Actual keyboard and regression evidence

- New source-controlled `tests/windows-native-fictional-compare-keyboard.ps1` uses real Tab, Shift+Tab, Space, and Esc key events through Windows SendKeys; Windows UIAutomation **reads only** currently focused control PID/name/role and synthetic text. No programmatic InvokePattern or mouse activation.
- First exact-source GUI attempt on the new UI was marked **FAIL**, correctly: the older keyboard test assumed reverse Shift+Tab always moved directly to `Compare: bundle-dangling`, but the newly focusable `Clear fictional output (Escape)` button affected focus order after an action.
- Updated test (commit `2cecc2b5`) bounds the reverse-key path to six events and accepts only the named intermediate controls `Clear fictional output (Escape)` and `Compare verified fictional JSON (read-only)`; any unrelated/foreign PID focus or failed destination remains a hard failure. In the real pass, reverse focus progressed through Clear -> Compare -> bundle-dangling. This **does not prove reliable one-keystroke reverse navigation**, and wider screen reader accessibility remains open.
- Real native UI run on the exact binary then returned **6/6 PASS**, exit 0:
  1. Tab/Space creates pair comparison and displays exact expected synthetic Patient and Observation SHA-256 text.
  2. Shift+Tab reaches the previous fictional selection via a bounded verified focus path.
  3. Esc immediately clears the displayed pair SHA text.
  4. Same-source comparison fails closed, removing the stale second-source SHA.
  5. A new verify action clears the displayed comparison.
  6. Tab/Space activates the new Clear button, removing the displayed comparison again.
- The old independent source-controlled `windows-native-fictional-compare-uia.ps1` was rerun against the same exact binary: **3/3 PASS**, exit 0 (two sources, same-source refusal, stale clear). No user-files or patient data were used in either test.
- No hosted GitHub Actions CI success was observed/claimed for this `[skip ci]` branch head. The scratch executable is not a qualified distribution artifact.

## Unresolved blockers / NO-GO

The D2 Windows direct-egui GUI is still a developer experiment, not the complete MedOrigin application. Existing D1 WebView2 external egress #662, Linux AccessKit zbus5 maintenance #673, macOS spoken VoiceOver #676, optional Core extras #622, independent security review #603, and owner release/signing/packaging #574 remain open. Actual OS-enforced Windows packet/DNS egress confinement, OS-broker descendant tracking, independent accessibility assessments and supported non-WSL Linux host acceptance are not qualified. **No protected main merge, tag, release, PHI, clinical deployment or public publication.**
