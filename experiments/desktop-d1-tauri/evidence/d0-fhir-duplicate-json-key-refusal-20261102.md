# D0 fictional FHIR duplicate-object-key refusal — 2026-11-02

Status: **AUTHOR-SIDE WINDOWS NATIVE GREEN; RELEASE NO-GO**. This is a nonpublishing, synthetic-only D0/D1 engineering experiment. No patient input, EHR, file import, network observer, package release, or clinical validation.

## Concrete defect and scope

The D0 fictional Bundle graph inspector previously parsed bytes directly into `serde_json::Value`. JSON objects with repeated keys are normalized to the last value before the local graph checks run. A modified fictional Bundle with both `"resourceType":"Patient"` and `"resourceType":"Bundle"` at the same object depth could therefore return `BUNDLE_GRAPH_OK` rather than refusing ambiguous source bytes. This is a **source parser ambiguity**, not proof of a real patient-data exploit: the preview accepts only twelve compile-time fictional fixture IDs.

The fix first deserializes a bounded JSON document with a recursive `serde::de::Visitor` that rejects repeated keys **at each object depth**, including Unicode-escaped equivalent key names, before the existing structural `Value` check. It covers both Bundle and Patient/Observation fictional envelope paths. Distinct objects may reuse the same field names. The existing `INVALID_UTF8` contract is preserved; duplicate keys return `INVALID_JSON`. The raw SHA-256 hash function is unchanged and still hashes original bytes without JSON normalization.

## Exact source and real native test-first sequence

- Immutable Draft #846 parent: `950fb1bfb2348e5fc6ad2a0eafea4635621fc237`.
- RED test commit: `8ba7bc1b4d5e8d9f0c3fd6c61e28d8ef6cbdcd67`. On authorized Windows Rust 1.97.1, the new test on pre-fix Bundle source returned `BUNDLE_GRAPH_OK` for duplicate `resourceType` while expecting `INVALID_JSON`; actual native test **FAILED**, exit 101. This is a demonstrated parser ambiguity, not an OS/network exploit.
- GREEN code commit: `a66b62eb6b478f3623028f7f10a3330cdcd6b770`. Actual Windows `cargo test --offline --locked --all-targets` D0: **7+2+2+3=14 PASS**, 0 failed, 0 ignored. `cargo clippy --offline --locked --all-targets -- -D warnings` PASS; `cargo fmt` and `git diff --check` PASS.
- During integration, a first GREEN run exposed an inherited `patient-invalid-utf8` status regression (`INVALID_JSON` instead of `INVALID_UTF8`); this was fixed before the final GREEN rerun. No tests were waived.
- Actual Windows D1 Tauri `cargo test --offline --locked --lib`: **6/6 PASS**, including after restoring an unrelated resolver-changed `cssparser-macros` `syn` entry. Only direct `serde` dependency edges were added to the two experiment Cargo.lock files; no crate versions changed.
- Source delta: D0 `Cargo.toml`, D0 `Cargo.lock`, D0 `src/lib.rs`, D0 `src/synthetic_bundle.rs`, D1 `src-tauri/Cargo.lock`; plus this evidence file. Frozen repository-root `pyproject.toml`, `uv.lock`, and MRL research evidence untouched.

## Proof boundaries and outstanding gates

The native tests exercise the **fictional local parser**, not full FHIR R4 validation, arbitrary JSON import, production WebView2 execution, packet-level egress denial, independent security review, or approved package metadata. Hosted exact-final-HEAD CI must be inspected separately after push. Issues #662, #622, #673, #676, #603 and #574 remain open/NO-GO. No protected-main merge, installer, tag, publication, policy changes, elevated capture, or patient data. Repository visibility is public; Draft PR does not make it private.
