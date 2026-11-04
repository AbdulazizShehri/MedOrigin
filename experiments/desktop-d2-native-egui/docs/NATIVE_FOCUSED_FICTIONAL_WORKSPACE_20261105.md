# D2 focused native Workspace — user-facing screen, separate from developer evidence

**2026-11-05. PRIVATE Draft stacked on #953. Fixed fictional records only; not clinical use.**

## Product-facing function

The existing native egui GUI placed source-reviewed fictional Core encrypted Workspace results among large scrolling engineering evidence and developer fixture controls. This adds an explicit **Open focused fictional Workspace** action. It shows a separate simple native screen with a verified source summary, three source-derived resource actions, current Patient/Encounter/Observation identity and graph links, Back, a small in-memory visit walkthrough, and an accessible return to developer evidence. The original full developer view and its tests remain available. Source presentation distinguishes an actual persistent DPAPI test vault from a removed ephemeral AES-GCM test vault.

Actions are **Focus: Open Patient, Focus: Open Encounter, Focus: Open Observation, Focus: Back to patient, Focus: Next unvisited, Focus: Mark visited (demo only), Focus: Reset visits, Focus: Return to developer evidence** and **Focus: Clear fictional session**. Direct linked-member opening first reopens the verified fictional Patient, then follows the exact source-projected relationship to the intended member; it does not fabricate an encounter chronology. The three visit booleans remain in memory, never in the Core SQLite store, audit or a clinical workflow. The source approval and Core runtime behavior are unchanged.

Entering the screen requires the existing strict reviewed source projection and independently reconcilable Patient/Encounter/Observation graph. A changed, missing or duplicated source relationship refuses and clears both the source and mode. A clear/Escape resets the focus mode. There is no arbitrary FHIR input, patient information, clipboard, network, OS process launch, local filesystem read/write or new crate within Rust.

## Actually observed qualification

- Windows 11: 62 native Rust library + 11 main + 7 no-network/browser boundary tests = **80 PASS**; offline locked cargo test, Clippy -D warnings and Rustfmt PASS. Two new adversarial tests cover both pinned ephemeral and persistent fictional Core projections, source retention after entering/leaving focused view, Patient→Encounter→Back, missing source, mutated link and full reset.
- The actual Windows compiled native Rust GUI SHA256 is a2b2e6e30e4e23cf91f53947738fbf3ab8949b7bf11c7907ada11a0969ddfe11. Real Windows UIAutomation clicks the new focused view, Patient/Encounter/Observation, Back, visit mark/reset and developer return, then independently completes the historical source graph/filter/history/clear tests. EXIT0 WINDOWS_REAL_ENCRYPTED_CORE_READBACK_THREE_RESOURCES_LINK_AND_BACK_UIA_PASS_NOT_CLINICAL.
- A separate actual source-pinned Windows Python3.14 Core AES-256-GCM import/reopen/audit readback under a true suspended-before-execution kill-on-close Job Object was loaded into that exact binary; the expanded full GUI UIAutomation exited 0 with WINDOWS_LIVE_ENCRYPTED_CORE_READBACK_TO_NATIVE_D2_GUI_PASS_NOT_CLINICAL.
- The macOS Apple Accessibility script is extended to drive the focused screen. The exact PR-head Mac build and GUI outcome must be checked and reported separately, as must the hosted GitHub Windows/Ubuntu checks. Do not mistake source parsing for actual native GUI acceptance.

## Outstanding NO-GO gates

Still limited to **three imaginary, exact source-reviewed FHIR-shaped identities**. No signed production installer, real patient workspace, production protected key resolver, verified RBAC/consent, full FHIR R4 conformance, authenticated production IPC, OS network egress isolation, clinical security/accessibility review or dependency remediation. No protected main merge, real PHI, publication, distribution, production release or notarization. The Windows Job Object controls worker lifetime, not network. Source/tests/docs only; no SQLite, DPAPI blobs, Wheels or executables committed.
