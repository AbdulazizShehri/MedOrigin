# MedOrigin D0/D1 — synthetic FHIR Bundle graph (nonclinical, nonpublishing)

Date: 2026-11-02 Asia/Riyadh. Source: feat/medorigin-d1-synthetic-bundle-20261102, stacked on unpublished Draft #837. This is a narrowly bounded offline Developer Preview, **not** FHIR R4 profile/terminology/clinical validation.

## Real new feature

The Rust D0 library now compiles four additional *fixed, fictional* JSON Bundle collections from tracked source fixtures using include_bytes! and does not read any runtime filesystem path. A deterministic generator, tools/generate_fictional_bundles.py, creates the exact fixture bytes, or with --check verifies byte equality without writing. The fixed fullUrl URNs use synthetic, syntactically valid UUID strings (00000000-0000-4000-8000-000000000001 and ...0002), not dereferenceable URLs.

The Bundle inspector uses real serde_json parsing and enforces exactly one fictional Patient and one fictional Observation, a specific collection Bundle type, distinct expected fullUrls, unique entries, fixed fictional Patient/Observation identity and code/value, and an Observation subject.reference resolving strictly to Patient/synthetic. It returns BUNDLE_GRAPH_OK (valid fictional internal graph), INVALID_REFERENCE (subject does not exist), DUPLICATE_ENTRY (fullUrl conflict), or INVALID_BUNDLE_TYPE (unsupported transaction). It denies any arbitrary user path, URL, real patient data, external FHIR lookup, file input or unbounded graph size. No real FHIR transactions, network API, EHR, terminology or PHI.

Four raw compiled fixtures:
- bundle-valid: 531 bytes, SHA-256 3a530a66c0f2b71908b1282985432e405f0f2f412c7ccc0143aa1972d9447983
- bundle-bad-reference: 528 bytes, SHA-256 4aabcfa54309c83052d62b4fdcf1c6635a6cd3d937551e2ab947899345f9f082
- bundle-duplicate: 531 bytes, SHA-256 813f8a3b8fee59ba74abdb293c6cac5cca103b390153730e6e3bc4656540f15b
- bundle-wrong-type: 532 bytes, SHA-256 293c10c8abf055e8c1f84bae4913c7246bf9be5bf53dee0fb3c918e32a8346a7

The Tauri D1 command remains the same typed, allowlisted synthetic-only FHIR envelope bridge. The React UI now offers ten fictional examples total; new Bundle outcomes are matched to exact expected fixture status, raw SHA-256 and size and never imply full FHIR R4 validity or release authority.

## Local real evidence (must confirm exact final SHA before final approval)

- Windows D0 native cargo test --offline --locked --all-targets: 12/12 PASS, including mutable graph negative cases, all Bundle fixture SHA-256 goldens and rejection behavior.
- Windows D1 Node source/AppContainer contract: 9/9 PASS.
- Windows npm run build (TypeScript + Vite) PASS.
- Real Edge headless Playwright rendering + mocked synthetic Tauri IPC: 4/4 PASS, including Bundle graph acceptance and three explicit failure states, plus prior forged native bridge and hash mismatch cases. **The Tauri IPC is mocked**; no real Tauri WebView2 network proof follows.
- Deterministic fixed fixture script --check: PASS without writes.
- Native Windows D1 cargo test --locked --lib and exact hosted GitHub Windows/Ubuntu/Edge CI must be checked separately on final SHA.

## Security and release constraints

Fictional Bundle graph structural tests are not a specification-level FHIR validator, terminology validation, profile conformance, production parity, trusted real-world patient reference resolution or clinician usability. This does not close #662 WebView2 OS packet/DNS egress G3 BLOCKED, G4/G5 NOT_RUN or G7 BLOCKED, #622 frozen original optional research advisories, #673 Linux AccessKit/zbus maintenance, #676 actual macOS spoken VoiceOver evidence, #603 independent human security review, or #574 owner ADR45/version/packaging/release authorization. No protected-main merge, PHI, installer, user file access, elevated WFP/ETW capture, outbound network, paid inference, distribution or public release.
