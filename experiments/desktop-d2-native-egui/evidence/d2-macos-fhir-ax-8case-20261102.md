# MedOrigin D2 — real Apple Silicon NSAccessibility for eight fictional FHIR examples

Date: 2026-11-02 Asia/Riyadh. Experimental, synthetic-only and nonpublishing. Parent is Draft #853 at exact SHA `71416ed53efe17992d99ba1951b0f90cc492f21e`. Mac device is a user-authorized Apple Silicon arm64 desktop running Darwin 25.6.0, native macOS UI session. The working copy was a separate **sparse Git worktree** with only D0/D2 and workflows; initial source size 1.3 MB, about 25 GB available before compilation. No unrelated Mac projects or system privacy settings were altered.

## What ran on the REAL Mac

Compiled the **exact Draft #853 native eframe/Rust source** with `cargo +1.97.1 build --locked`, and ran `cargo +1.97.1 test --locked --all-targets` successfully. The built debug native executable SHA-256 was `dffb0094a5b55162f4fb555a1cda741d12787452b8b34ab9a73ff852d703b806`, printed from `shasum -a 256`.

1. Executed the EXISTING source-controlled `macos-native-ax-qualification.swift` against the fresh running native application. It waited for AccessKit's asynchronous accessible tree, used real `AXUIElementPerformAction` on the original four checkboxes + Verify button, and matched all four approved synthetic SHA values in the native AX tree: **4/4 PASS**, exit 0.
2. Executed the EXISTING `macos-native-keyboard-qualification.swift` on the same live native application. It sent actual forward Tab, reverse Shift+Tab and Space keyboard events and read OS-focused AX controls, with all four original fixture results: **MACOS_KEYBOARD_4_OF_4_PASS_NONPUBLISHING**, exit 0.
3. Added NEW source-controlled `macos-native-fhir-ax-qualification.swift`. It finds exactly one visible native window for the caller's PID, expands `Additional fictional FHIR/Bundle cases (8)` through the real native NSAccessibility Press action, selects each fictional Observation or Bundle case, invokes the original Verify button and requires **two distinct AXStaticText elements**: one EXACT `Synthetic raw SHA-256 verified: <fixed SHA>` and one EXACT `Fictional FHIR envelope: <expected synthetic status> (NOT full FHIR R4 validation)`. Tested 8/8 SUCCESS (exit 0) on TWO separate cold-start native application processes:
   - `observation-minimal` => `FHIR_ENVELOPE_OK`
   - `observation-bad-subject` => `INVALID_REFERENCE`
   - `bundle-valid` => `BUNDLE_GRAPH_OK`
   - `bundle-bad-reference` => `INVALID_REFERENCE`
   - `bundle-duplicate` => `DUPLICATE_ENTRY`
   - `bundle-wrong-type` => `INVALID_BUNDLE_TYPE`
   - `bundle-linked` => `BUNDLE_GRAPH_OK`
   - `bundle-dangling` => `INVALID_REFERENCE`.
4. Added **in-script binary identity enforcement** using `NSRunningApplication(processIdentifier:)`, exact executable basename and `CryptoKit.SHA256.hash` over the executable on disk. Calling with an all-zero wrong SHA-256 rejects with exit 1 before accessing the app's AX tree; correct externally supplied binary SHA yields 8/8 PASS, exit 0. Invalid non-existent PID `999999` likewise fails closed (exit 1).
5. `swift format lint --strict` and `swiftc -typecheck` passed on the checked-in Swift test after formatting.

The new GitHub macOS source-only CI only **typechecks/lints Swift**, checks the presence of eight exact fictional cases and read-only AX calls; it does not run a hosted GUI, activate VoiceOver, listen to spoken output, or claim independently signed build binaries. The existing GitHub Windows/Ubuntu Rust matrix from parent #853 covered the actual D0/D2 native source on those systems. This new test produces narrower **one-machine NSAccessibility acceptance**, not an independent release signature or multiple-device reproducibility.

## Explicit remaining NO-GO

- **#676 remains OPEN:** this does not test VoiceOver speech/audio announcements, screen-reader workflow quality, cross-machine independent reproducibility or independent accessibility review. Real AX controls/labels and keyboard tests are not a spoken VoiceOver evaluation.
- **#662 remains BLOCKED:** there was no Mac kernel/network packet observer, Windows WFP attribution, background broker DNS/TCP/UDP containment or Windows isolated-disposable guest qualification; only fictional in-process Rust was run.
- **#673 remains OPEN:** Linux AccessKit transitive `zbus 5` unmaintained advisories are unchanged.
- **#622/#603/#574 remain OPEN:** root frozen optional dependency alerts, independently reviewed source/signed release artifact, founder ADR identity/version/signing and public release approval. No clinical FHIR R4 conformance, PHI, EHR, tag, installer or protected-main merge.

Do not convert this evidence into a clinical acceptance or publication authorization. Keep Draft status and preserve original source-bound receipts.
