# MedOrigin D0/D1 — synthetic Observation references and fail-closed UI
Date: 2026-11-02 (Asia/Riyadh). Exact branch: feat/medorigin-d1-synthetic-observation-20261102.
Status: nonpublishing, synthetic-only engineering; not FHIR R4 conformance, security release approval, or OS packet isolation.

## Feature and exact corpus

Building on Draft #835's original four fixed fictional Patient fixtures, add two in-memory fictional Observation JSON variants with explicit SHA-256 golden raw-byte references and sizes. Names:
- observation-minimal: 251 bytes, SHA-256 527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19; subject.reference points to the only locally recognized fictional Patient/synthetic. Bounded, strictly typed JSON envelope status FHIR_ENVELOPE_OK.
- observation-bad-subject: 253 bytes, SHA-256 d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838; subject.reference points to Patient/nonexistent and status must be INVALID_REFERENCE.

Checks also require synthetic-observation id, final status, a fictional offline code system, fictional coding, integer fictional measurement, and unit. This performs only local structural checks on exact fixed synthetic bytes, NOT terminology validation, profile adherence, reference resolution against real FHIR servers, clinical validation, or arbitrary JSON file import. Existing 32,768-byte boundary and max_input_bytes protections remain unchanged. D0 raw SHA-256 result contract remains unchanged; new names are explicitly allowlisted.

## UI integrity repair

React presents two new fictional samples, with exact static SHA references and expected envelope statuses. It verifies the native SHA response contract and byte length before allowing the second native command, then validates fixture identity, bytes, explicit nonclinical claim and exact expected structural status before setting a success result. A failing second command no longer leaves a prematurely displayed successful SHA result, which could obscure a bridge error. A real SHA mismatch is displayed as a failed match and no FHIR result. The preview continues to state nonclinical and no real WebView2 OS network isolation.

## Real test and CI scopes

Test-first RED on original D0 parent: the two new observation fixture tests FAILED as UnknownFixture, while the negative unknown/path case passed. GREEN actual Windows D0 cargo test --locked --all-targets: 9/9 tests PASS (4 legacy unit + 2 prior FHIR + 3 Observation). D1 Node source/AppContainer tests 9/9 PASS. Actual Windows npm ci and TypeScript/Vite 8.3.5 build PASS, 18 modules. Native D1 Rust compile and hosted Windows+Ubuntu exact SHA runs must be independently verified when completed. No application launch, external data, patient file, network capture, elevation, paid service, installer or publication.

## Unresolved release gates

#662 OS WebView2 packet/DNS egress remains BLOCKED G3, G4/G5 NOT_RUN, G7 BLOCKED; #622 optional original research dependency advisories; #673 Linux AccessKit/zbus v5 maintenance; #676 macOS VoiceOver spoken workflow verification; #603 independent human security review and #574 owner ADR/version/package/release authorization all remain NO-GO. No protected main merge. Never claim this closes them.
