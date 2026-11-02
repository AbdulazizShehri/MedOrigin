# MedOrigin synthetic Bundle URN graph reconciliation

Date 2026-11-02 Asia/Riyadh. Source branch: feat/medorigin-d1-bundle-urn-resolution-20261102 stacked on nonpublishing Draft #839 (which is stacked on Draft #837). No release or clinical authorization.

## Why this additional slice

Draft #838 was independently opened on the same #837 base as #839. #838 tested two fictional Bundles with Observation.subject.reference equal to Bundle.entry.fullUrl (URN UUID), whereas #839 checked the local relative Patient/synthetic reference, duplicate entries, and unsupported Bundle type. Neither was an exact superset of the other, and they must not be merged blindly.

This update extends #839's one graph checker to accept EITHER the fixed fictional relative reference Patient/synthetic OR an exact URN UUID that equals the present fictional Patient entry's fullUrl, with no HTTP/file resolution. The local check captures the actual observed Patient entry URL rather than accepting arbitrary URNs. A reference to an absent fictional Patient URN is rejected with INVALID_REFERENCE. All other prior fail-closed graph, duplicate entry, collection-only and deterministic byte checks remain.

## New compiled synthetic fixtures

- bundle-linked: 559 bytes, SHA-256 1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88, expected BUNDLE_GRAPH_OK; subject references the exact present Patient entry URN.
- bundle-dangling: 559 bytes, SHA-256 1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229, expected INVALID_REFERENCE; subject points to a valid-shaped but absent fixed fictional UUID.

They are compiled into the D0 Rust binary, regenerated reproducibly with the source-controlled deterministic generator, and verified read-only by --check. The public Tauri command interface remains unchanged, with 12 exact allowlisted fictional fixtures total. React and the test-only Edge mocked-IPC bridge cover both URN outcomes; no user-supplied real JSON paths or EHR data.

## Local evidence and limits

Test-first initial Rust compilation failed on one missing match comma (syntax RED) and was corrected. On exact candidate source, authorized Windows D0 cargo test --offline --locked --all-targets 12/12 PASS, D0 Clippy -D warnings PASS, source/AppContainer Node 9/9 PASS, npm ci + TypeScript/Vite PASS. Real Edge headless browser with mocked Tauri IPC 4/4 tests completed successfully (exit 0). Native Windows Tauri Rust cargo test --locked --lib 5/5 PASS (exit 0), Rustfmt for both crates PASS, Node source/AppContainer 9/9 PASS. Hosted GitHub Windows/Linux/Edge exact SHA jobs must independently complete before treating this candidate fully qualified.

This is NOT full FHIR R4 Bundle reference resolution or terminology/profile validation; it is a fixed fictional graph safety check. It does not close #662 WebView2 background DNS/packet egress G3 BLOCKED G4/G5 NOT_RUN G7 BLOCKED, #622 frozen research advisories, #673 Linux AccessKit/zbus, #676 spoken VoiceOver, #603 independent human security review, or #574 owner ADR/version/publishing decisions. No public release, tag, installer, PHI, paid inference, main merge or elevated OS capture.
