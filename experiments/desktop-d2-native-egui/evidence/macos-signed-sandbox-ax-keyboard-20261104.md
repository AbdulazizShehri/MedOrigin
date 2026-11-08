# MedOrigin D2 macOS signed sandbox native keyboard and AX regression qualification

**2026-11-04 · synthetic-only developer experiment · one authorized interactive Apple Silicon Mac, macOS 26.6.2 · NO PHI and NO release**

## Baseline and actual discovered defects

At exact parent `security/medorigin-d2-private-release-gate-20261104`, commit `43256e03d1324e9f9facc45bdbb44cb2af72cdc4`, built the native D2 Rust/egui preview using `cargo +1.97.1 build --locked --offline`. The local debug Mach-O SHA-256 was `bb25244d79528384f4512d84d4a2f7b07edc7a2cbe9929a1ef7bf7f9a2fb78bd` (not a trusted-source independent attestation).

The existing source-controlled local App Sandbox test:
- `bash tests/macos-native-sandbox-network-negative.sh` qualified the sandbox entitlement **mechanism** on a separate ad-hoc signed disposable loopback probe, observed unconfined connection positive control then OS denial `MACOS_APP_SANDBOX_LOOPBACK_DENY_PASS_NOT_PRODUCT_EGRESS_AUTHORITY`. No external destination used.
- `bash tests/macos-d2-app-sandbox-interactive.sh <exact locally built D2 binary>` created a separate disposable **ad-hoc signed** native GUI .app with sandbox entitlements `app-sandbox=true` and no network client/server authorization. On baseline test, the actual D2 app's **4/4 AX fixtures passed**, but the keyboard script initially failed after the first fixture: `MACOS_KEYBOARD_NO_GO: Tab cannot reach selector patient-invalid-utf8`. It had a stale `<7 Tabs` assumption despite extra in-app controls, navigation loops and repaint. This is a **GUI QA regression** in the keyboard harness, not independent evidence that the native app itself was inaccessible.
- The next cold-start re-run also exposed an independent **AX startup race**: `MACOS_AX_NO_GO: expected exactly one accessible preview window`; PID appeared before AccessKit/LaunchServices returned a window. Neither failure was silently waived.

## Source fix and real acceptance

Changed only the **source-controlled macOS test harness**, not the product GUI, privacy policy, entitlement file or Core:
1. Genuine keyboard Tab search increased to **at most 28** events around the larger focus cycle, still requiring the exact named fixture/Verify button, forward and reverse keyboard focus and exact visible SHA; it collects only the last 8 synthetic control names if the bound is exceeded. Still uses CGEvent Tab/Shift+Tab/Space and no AXPress, mouse or direct Rust hash substitute. A missing/unreachable control remains exit 1.
2. In both native AX and keyboard acceptance scripts, wait up to **40 * 0.2 seconds** for **exactly one** AX window from the intended process, refusing zero or ambiguous windows after the bound. The tests still require live Accessibility trust and actual AX-visible labels and native controls.
3. New source-only Python tests pin fail-closed bounded navigation, AX window uniqueness and real keyboard input; do not misrepresent them as live GUI tests.

**Actual observed on authorized Mac:**
- Real signed local sandbox GUI AX **4/4** primary synthetic patient hash fixtures PASS.
- Real signed sandbox GUI actual keyboard **4/4** Space-activated synthetic patient hash fixtures PASS, including forward Tab and reverse Shift+Tab focus checks.
- This full signed GUI+AX+keyboard acceptance passed twice after the fix, in independent disposable .app launches. `swiftc -typecheck` succeeded for both adjusted Swift sources.
- Real separate loopback OS-denial test **PASS**, as recorded above.

## Boundaries and unsatisfied release gates

This is **not** a fully OS-enforced network confinement attestation for the D2 app and all its process descendants: the packet-block negative probe is a separate signed program; GUI testing observes accessibility with the same sandbox entitlement, not actual descendant DNS/TCP/UDP packet provenance under independent controls. It is **not** notarized/certified App Store signing, VoiceOver spoken announcements, cross-device independent keyboard approval, production Core bridge or clinical FHIR validation. Do not close issue #676 from this result; #662 D1 WebView2 egress, #673 Linux transitive dependency, #603 independent security assessment and #574 owner signing/publication approval also remain open. Never place real patient data into this D2 preview, release it, publish it or merge into protected main based on this test.

Source-only CI must validate harness syntax/markers; **actual macOS AX and CGEvent** require a separately authorized interactive Mac with Accessibility permission and are not run as if proven by GitHub hosted Linux/Windows runners.
