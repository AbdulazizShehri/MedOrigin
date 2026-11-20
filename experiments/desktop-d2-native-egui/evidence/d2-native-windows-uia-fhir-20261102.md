# D2 native Windows UIAutomation real FHIR fixture qualification — 2026-11-02

**Nonpublishing, nonclinical, one authorized Windows 11 host.** Source candidate stacked on D2 Draft #852 exact parent `1482a28e6b39ecf32478d2545da0ad0def9a96dc`, after separate native FHIR D2 Draft #851. This experiment only uses twelve compiled-in, fictional Patient/Observation/Bundle fixtures and no arbitrary files, PHI, FHIR server, model, EHR API or cloud account.

## Genuine detected accessibility regression

The D2 preview introduced by #851 rendered a combined multi-line Rust result (`Synthetic raw SHA-256 verified: ...\nFictional FHIR envelope: ...`) through a **single** `egui::Ui::monospace` element. The existing Windows UIAutomation test expects the SHA-256 digest as its own exact `ControlType.Text` node. Source-level tests did not detect this GUI/accessibility contract regression.

This patch renders each verified result line as its own `egui::monospace` text node while preserving the in-process Rust result and fail-closed digest+structural checks. The original four visible selector labels and `Verify synthetic SHA-256` button remain in their original order, and eight advanced fictional cases remain initially collapsed. The status is a distinct accessible node stating `NOT full FHIR R4 validation`. No network/browser entrypoints, native background workers or clinical features added.

## REAL Windows native UIA results

- Built the exact checked-out code with `cargo build --locked` on the user's authorized **interactive Windows PC** using pinned Rust 1.97.1 and fixed Cargo.lock. Verified binary with `Get-FileHash -Algorithm SHA256` before launching. Native exe SHA-256 **7776E912C99EED4B71A92DA4254D7E10D84BA106912F5A892BE51B9F0F84749F**.
- Re-ran the source-controlled original `tests/windows-native-uia-smoke.ps1` on an actual fresh native application process. **4/4 PASS**: selects each original case with the Win32 UI Automation pattern, invokes the actual Verify button and finds the exact standalone SHA-256 text node; exit 0.
- New source-controlled `tests/windows-native-fhir-uia-qualification.ps1` launches the real local native D2 executable with an externally supplied expected exact SHA-256, locates the visible window by PID, expands the eight-case section through **real Windows UIA Invoke/Toggle**, chooses each fixture, invokes Verify, and requires exactly one SHA-256 text node AND exactly one expected fictional envelope-status text node for each result. **8/8 PASS**, exit 0. The eight cases include Observation valid and broken reference, Bundle valid, broken reference, duplicate fullUrl, unsupported type, valid local URN, and dangling URN.
- Repeated that **new 8/8 UIA test on a separate fresh app launch**; again exit 0.
- Deliberately supplied an incorrect all-zero binary SHA-256: the same source test failed closed **before app launch**, `D2_NATIVE_FHIR_UIA_NO_GO: binary identity mismatch`, exit 1. PowerShell parser on the test script returned zero syntax errors.
- Real Windows native Rust `cargo test --locked --all-targets` PASS (4 app model tests + 6 browser/network source tripwires), `cargo build --locked` PASS; no actual server/browser launch or test PHI. Existing D0 12-case Rust source tests from parent remain source-bound as noted in PR #852. Cargo audit/OS packet egress remains separate.
- Hosted GitHub Windows and Linux check for this **PR exact head must be confirmed separately**; any hosted PowerShell AST parsing is **source-only**, and does not claim a hosted interactive GUI/packet test.

## Residual NO-GO

This validates native visual control interaction / UIA accessibility on **one authorized Windows host**, not macOS AX/VoiceOver spoken announcements, usability on a second machine or independent review. #676 remains OPEN. A local **bounded GUI test** is not an OS WFP/ETW/pktmon DNS/TCP/UDP process descendant packet-denial proof: #662 G3 BLOCKED, G4/G5 NOT_RUN, G7 BLOCKED. #673 Linux transitive AccessKit/zbus5 unmaintained RustSec, #622 frozen research optional advisories, #603 independent security review, #574 owner ADR/version/signing/publication still OPEN and unapproved. No protected-main merge, release, PHI, EHR system or paid cloud inference.

The original native Windows UIA test was genuinely re-run, not inferred from a preserved source string. The independent Mac AX/keyboard test for the **new** expanded interface was **not** re-run and its earlier four-fixture results cannot be automatically extended to this commit.
