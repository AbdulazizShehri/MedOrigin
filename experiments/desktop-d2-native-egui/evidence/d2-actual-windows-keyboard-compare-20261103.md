# D2 actual Windows keyboard-only fictional comparison qualification — 2026-11-03

**Status: 4/4 narrowly scoped Windows keyboard-control behaviors PASS twice; release, clinical functionality, screen-reader usability and native OS network containment remain NO-GO.**

## Exact tested source and executable

- Private, unmerged Draft PR #859; native D2 comparison source inherited from exact baseline `f22cd3f94a30ac4a0057a839d619fa1fb2e63439`. The only new committed code is a source-controlled **test**, not production API, user data import or dependency change.
- On authorized Windows development PC, compiled from source using `cargo build --offline --locked` (PASS, no dependency download). Local, unsigned native D2 GUI exact SHA-256: `65A4AF60A85E28C08010FDBC756C8A3AA65B28EADC57657A0887DFCFF4D75073`. This hash applies only to this locally built executable, **not a signed/published artifact**.
- Source-controlled test: `experiments/desktop-d2-native-egui/tests/windows-native-fictional-compare-keyboard.ps1`. Requires exact executable basename and caller-supplied SHA-256 *before* launching the native app. Detects the actual native application window by its PID and title, focuses **the window** (not individual controls via UIA), uses genuine `System.Windows.Forms.SendKeys` Tab, Shift+Tab and Space key events. Reads only UIAutomation *focused element, role/name and synthetic text*. No UIAutomation InvokePattern, TogglePattern, mouse click, EHR, PHI, file import or network request.

## Actual GUI results

Two independent cold-start runs against that exact binary reported **4/4 PASS, exit 0**:
1. Tab navigation from native window through the original four Patient selectors, Verify, additional fixtures header, JSON read-only preview and second-fixture header; press Space to expand; Tab to Observation; Space to select; Tab to Compare; Space to compare. Windows UIAutomation showed the **exact Patient and Observation SHA-256** as two accessible text nodes. `KEYBOARD_REAL_COMPARE_TWO_SHA_PASS`.
2. Reverse **Shift+Tab** navigation from the focused Compare button to the prior named `Compare: bundle-dangling` control. The first Shift+Tab event after repaint left the focused element unchanged; a second Shift+Tab moved to the previous control in both runs. The source-controlled test checks this behavior, does **not** claim reliable single-keystroke reverse navigation, and records `KEYBOARD_REAL_REVERSE_SHIFT_TAB_PASS`.
3. Tab to comparison source Patient; Space to select; Tab to Compare; Space to submit same-source comparison. Exact `FAIL CLOSED: choose two distinct fictional fixtures` text appeared, and previous Observation SHA text was absent. `KEYBOARD_REAL_SAME_FIXTURE_REFUSAL_PASS`.
4. Tab back to Observation; Space select, Tab and Space compare; verify SHA is present; Tab to `Verify synthetic SHA-256`, Space activate; previous comparison SHA text disappears. `KEYBOARD_REAL_STALE_CLEAR_PASS`.

Final marker **`D2_COMPARE_WINDOWS_KEYBOARD_4_OF_4_PASS_NONPUBLISHING`**, process exited 0. The test terminates only its own spawned MedOrigin process. Earlier exploration independently recorded the 9 tab stops per loop and confirmed all focus elements belonged to the spawned MedOrigin PID.

## Not qualified and remaining issues

This demonstrates **keyboard activation and readback of synthetic comparison on one real Windows interactive session**, not full keyboard-only accessibility on all supported OSs. The repeated-key Shift+Tab observation remains a targeted usability limitation; actual VoiceOver announcements on macOS #676 remain pending. No packet-level Windows egress isolation #662, Linux AccessKit/zbus maintenance #673, optional extras #622, independent security review #603, or owner release/signing approval #574. The comparator is synthetic-only and never authorized to process PHI or clinical records. No protected main merge, tag, installer, publication, paid inference or hosted exact-HEAD CI success is claimed.
