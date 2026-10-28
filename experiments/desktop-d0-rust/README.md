# MedOrigin desktop D0 — isolated Rust SHA-256 experiment

**Status:** Experimental source only, **not accepted for product integration**, not a distribution, not a medical device, and not a Python replacement. This folder exists on a separate **Draft-only** PR branch and must not be merged into protected `main` or shipped without an accepted architecture/toolchain entry decision.

## Purpose and trust boundary

The user-directed future direction is a Rust-first local desktop, with Python remaining canonical for research and Health AI. This tiny crate experiments with only the first pure-data Rust capability: `hash_fixture_raw_v1(fixture_id, max_input_bytes)`. It uses a closed set of four *fictional* in-memory byte fixtures from [D0 issue #657](https://github.com/AbdulazizShehri/MedOrigin/issues/657) and [Draft PR #658](https://github.com/AbdulazizShehri/MedOrigin/pull/658).

The implementation does **not** parse FHIR, open filesystem paths, execute OS commands, start a service, collect telemetry, load a model, or process real patient records. It returns the SHA-256 of **raw bytes**, which must not be mistaken for FHIR canonical JSON or a signed/authenticated receipt. It enforces an upper bound before allocation, has no `unsafe` code, and rejects all fixture IDs not on its explicit allowlist. Unknown Windows paths, Unix paths, traversal and embedded-NUL strings are negative tests, not accepted file paths.

## Dependencies and reproducibility limitations

- Rust 2024 edition, toolchain at least Rust 1.88.
- SHA-256 implementation from RustCrypto `sha2 = "=0.11.1"` (dual MIT OR Apache-2.0 license); no custom cryptographic algorithm.
- **Do not call this crate supply-chain qualified until a machine-generated and reviewed `Cargo.lock` is committed**, dependency/license/advisory evidence is recorded, and Windows, macOS and Linux independently pass using that lock and a pinned toolchain. This first step is exploratory and remains unpublished.
- License of MedOrigin-owned prototype source: Apache-2.0. All third-party notices and upstream code licenses must be preserved; the RustCrypto implementation is an external dependency, not copied into this repository.

## Proposed qualification

From the experiment folder, once an approved toolchain and lock are available:

```bash
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --locked
```

Compare all four expected SHA-256 hex values *byte-for-byte* against the **source-bound** Python test corpus in [PR #658](https://github.com/AbdulazizShehri/MedOrigin/pull/658). Initial failures must block qualification. The independent benchmark in [PR #659](https://github.com/AbdulazizShehri/MedOrigin/pull/659) measures Python only, not Rust performance.

The first eventual desktop command must undergo a separate IPC, path traversal/symlink/TOCTOU, size-budget, no-network/no-telemetry, privacy and native installer threat review. The source-only in-memory prototype is **not** that command.

**Release authorization:** `false`. **Rust production parity qualified:** `false`. **Clinical/PHI authorization:** `false`.
