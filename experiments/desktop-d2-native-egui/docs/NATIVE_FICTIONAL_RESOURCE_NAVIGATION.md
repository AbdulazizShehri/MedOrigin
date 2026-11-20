# D2 native fictional FHIR resource navigation — functional UI slice

Private, source-only, nonclinical Desktop development. No release authorization, PHI or real FHIR validation.

## User-facing behavior

MedOrigin D2 now supports **two independent, fixed-selection worklist facets** in its real Rust/egui GUI: expected developer status (positive/negative) and fictional FHIR resource type (All/Patient/Observation/Bundle). The visible count is calculated from six SHA-verified, build-time fictional cases: **1 Patient, 2 Observations, 3 Bundles**. Their source IDs and expected statuses are fixed; no free-text query field accepts user/patient input. Changing a facet clears previously rendered details and navigation.

The user can open a fictional Observation or Bundle, see its verified source relationship pointers and click **Follow fictional reference** to navigate directly to a source-approved Patient/Observation case. The link action independently re-verifies the source's exact SHA/envelope and the full source-compiled relationship projection before resolving only these hard-coded identifiers:

- `Patient/synthetic` or `urn:uuid:00000000-0000-4000-8000-000000000001` → fixed Patient case
- `urn:uuid:00000000-0000-4000-8000-000000000002` → fixed Observation case

Generic references, unexpected edge indices, negative/dangling resource graphs, hidden target types, and cases not in the selected developer-status facet are refused, clearing stale details. One-step **Back to previous fictional case** restores the prior SHA-verified case once only. Escape, closing the fictional workspace, changing a facet, or opening another case drops the previous navigation state. An unchanged strict synthetic-intent gate remains closed by default.

This is actual GUI behavior, not a claim that the user can yet browse an authenticated/encrypted clinical database. No patient storage, user import/export, EHR access, network, process launch, consent, cryptographic key custody, production permissions, full HL7 FHIR R4 validation or clinical decision support is enabled by these controls.

## Real Mac native UI / exact source evidence

Built with pinned offline Rust 1.97.1, cargo `test --locked --offline --all-targets`, fmt, Clippy `-D warnings` and existing browser/network/process source guards PASS. Four new Rust tests cover faceted counts and intersections, SHA-verified Observation→Patient and Bundle→Observation/Patient navigation plus one-step back, hidden targets and out-of-range indices, and navigation state cleanup on filter, clear and close.

On an authorized Apple Silicon Mac, an ephemeral ad-hoc signed **App Sandbox native D2 .app** ran in the actual GUI. The source-controlled Swift/macOS Accessibility test `macos-fictional-resource-navigation-ax-qualification.swift` clicked type facets, checked worklist counts, verified hidden target refusal (without leaking prior details), followed an Observation's exact subject to the fixed Patient, returned, then navigated Bundle → Observation and back. Exact case names, SHA-256 digest, expected envelope status, original relation pointer and explicit not-clinical warning are verified from the real window. Marker:

`MACOS_FICTIONAL_WORKSPACE_NATIVE_FACET_LINK_AND_BACK_AX_PASS_NOT_CLINICAL` (exit 0)

Original Mac signed-sandbox tests **4/4 SHA native AX, 4/4 real keyboard, 2/2 Core provenance, 4/4 fictional Workspace cases** also PASS after compacting the facet layout to keep detail text accessible within the existing native viewport. Initial over-tall uncompressed UI caused an actual macOS AX regression in late Workspace detail visibility, so the layout was corrected and full GUI retested; no failure was waived.

The source-controlled Windows UIAutomation test for existing fictional workspace was extended to click the same resource facets, verify counts, fail-close on hidden Patient, follow accepted references and use Back. Hosted Windows CI only **parses this UIA script** and runs Rust tests; a genuine on-device Windows UIA execution is a separately reported gate.

## Remaining product gates

The display still uses six compiled fictional D0 resources, *not* arbitrary clinical FHIR data and not the encrypted Core readback APIs. A production workspace needs an independently attested installed Core and secure isolated worker, authenticated anti-replay IPC, production OS keystore/user identity/RBAC/consent/audit, safe encrypted persistence and readback, packet/descendant confinement on Windows/macOS/Linux, complete FHIR R4 schema+profile+terminology checks, accessibility/medical/security independent signoff and release approval. Private Draft, no merge to protected main or distribution.
