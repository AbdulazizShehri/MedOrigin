# D1 native fictional batch metadata fingerprint (NO RELEASE)

Date: 2026-11-02 Asia/Riyadh. Parent Draft #844: `5527795600b85398cb43b3cdee49ceaf6f9889b1`.
All data are the twelve fixed fictional fixtures. No PHI, external URLs, filesystem inputs, package publication, network policy changes, or production activation.

## Problem and bounded implementation

The existing native `verify_all_fixtures` returned twelve individually pinned row digests but no compact deterministic identifier for the *ordered aggregate result*. A user could not compare the complete result with a single reproducible digest. This adds a domain-separated SHA-256 fingerprint of **row metadata only** (fixture ID, decimal byte count, raw fixture SHA-256, fictional envelope status), with ASCII TAB fields and LF row endings in exact allowlist order. Prefix: `medorigin-d1-native-batch-v1\n`.

The pinned independently computed Python SHA-256 for all twelve source golden rows is:
`af062a37ed639a6df5c769bb0e9cb2e0e792b3f68760853ff8ea8e97e2ab5088`.

The D0 Rust helper hashes only caller-owned in-memory metadata; D1 computes it only **after all twelve native hash and fictional envelope checks succeed**. React validates the exact extra response field against its pinned golden and displays the digest only on complete success. Browser tests reject a forged fingerprint, with no partial rows. Node independently reconstructs the canonical byte stream from the Rust golden table using built-in crypto and verifies the pinned value and tamper sensitivity.

## Actual authorized Windows checks

- Test-first RED before implementation: Node source suite 4 PASS / 1 FAIL; new test rejected the missing batch digest contract. This is a missing feature, not an OS-network exploit.
- GREEN: Node source 5/5 PASS; Rust D0 6/6 PASS including order/content sensitivity; Rust D1 6/6 PASS including the exact 64-character aggregate golden; locked npm TypeScript/Vite build PASS; real installed Microsoft Edge browser 12/12 PASS using **test-only mocked Tauri IPC** and loopback-only local HTTP.
- Rust 1.97.1 Windows native toolchain; `cargo +1.97.1 fmt` wrapper was unavailable on this host, so the installed default `cargo fmt` with `rustc 1.97.1` was used. Final Clippy and exact hosted CI results must be separately checked.
- The scratch checkout is detached from immutable parent #844; no changes to frozen Python research `pyproject.toml`, `uv.lock`, MRL evidence, Rust Cargo lock, publisher, or protected main.

## Non-claims and unresolved release gates

This SHA-256 is **not a digital signature, independent attestation, source-to-artifact audit, or proof of OS-level network confinement**. The Edge browser suite uses simulated IPC, not a real WebView2/Tauri launch. The narrow fictional checks are not full FHIR R4, clinical, or patient-data validation. The release remains **NO-GO** pending #574 owner authority, #603 independent human security review, #622 frozen optional extras, #662 real WebView2 OS packet/DNS denial, #673 Linux zbus5 RustSec, and #676 spoken VoiceOver/independent accessibility.
