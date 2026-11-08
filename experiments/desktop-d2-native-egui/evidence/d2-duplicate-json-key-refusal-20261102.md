# D2 fictional Bundle JSON duplicate-key refusal — 2026-11-02

## Scope and provenance

- Parent: Draft #851 exact head `cc9ec502d9f21521d30ac322d71616cb5a09c0fd`; independent stacked branch, no modification of #851 or protected main.
- Source lineage: D2 copied D0 fictional Bundle graph parser from #840 before the separate D1-stack duplicate-key repair in Draft #847 (`439122c4b6311367dd94f0e879ab07652e85ec8d`). This patch ports only the relevant parser safety behavior; it does not merge #847 or reconcile the full D1/D2 lineages.
- Only twelve compiled fictional sample identifiers are accepted. No runtime patient files, external URLs, network, PHI, clinical validation, or release authority.

## RED — actual authorized Windows native test

- Test-only commit `1fadef01efdedbc1e6cc7798306c79acaa45dcf1`, command: `cargo test --manifest-path experiments/desktop-d0-rust/Cargo.toml --offline --locked rejects_duplicate_json_keys_in_d2_copied_bundle_parser -- --nocapture`.
- **Exit 1**: `left: "BUNDLE_GRAPH_OK"`, `right: "INVALID_JSON"`. This is a source-level ambiguous JSON interpretation, **not** proof of an exploitable external patient-file pathway.
- Three cases: duplicate top-level `resourceType`, duplicate nested Patient `resourceType`, and escaped Unicode alias `\\u0072esourceType`.

## GREEN — narrow remediation

- Recursive serde visitor rejects duplicate decoded JSON object keys at every depth before `serde_json::Value` can silently retain the last key.
- Applies to Bundle and Patient/Observation envelope paths; invalid UTF-8 is still explicitly rejected. SHA-256 continues hashing original bytes.
- D0 and D2 experimental Cargo locks updated for direct serde dependency only. No canonical Python `pyproject.toml`/`uv.lock` or research evidence mutation.
- **Actual authorized Windows Rust 1.97.1**: D0 `cargo test --offline --locked --all-targets` **13/13 PASS**; D2 `cargo test --offline --locked --all-targets` **10/10 PASS** (4 app and 6 source-boundary tests), zero skipped. D0 and D2 `cargo clippy --offline --locked --all-targets -- -D warnings` both PASS. D0 `cargo fmt --all -- --check` and `git diff --check` PASS.
- Hosted CI is source-only and must be verified at the final SHA separately; it cannot prove real OS packet denial or independent security approval.

## Remaining NO-GO

#574 owner release authority, #603 human security review, #622 frozen Python optional advisories, #662 WebView2 independent OS packet evidence, #673 D2 Linux AccessKit/zbus5 maintenance, #676 spoken VoiceOver/independent second device. No protected-main merge, release, tag, installer, artifact upload, elevation, WFP/ETW/firewall changes, or FHIR R4/clinical conformance claim.
