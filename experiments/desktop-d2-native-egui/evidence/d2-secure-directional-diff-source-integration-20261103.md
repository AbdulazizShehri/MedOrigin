# MedOrigin D2 — source-level integration of PR #859 and PR #864 (2026-11-03)

**Private integration branch; pending native tests and independent review. STRICT RELEASE NO-GO.**

## Scope and exact frozen inputs

- Security, native fictional comparison, keyboard Escape, synthetic-output clearing: Draft [PR #859](https://github.com/AbdulazizShehri/MedOrigin/pull/859), HEAD `aa8916f15952d61a6dc6eec9e8a5808b4523e8d0`.
- Directional, bounded, developer-only JSON byte/HEX/JSON Pointer differences: Draft [PR #864](https://github.com/AbdulazizShehri/MedOrigin/pull/864), HEAD `72ca7c3ff6913663d54b54aef168fd7ce4a47de3`.
- Common source base for `src/app.rs`: commit `5aaf289d698054a73db9de64efd5e7939f6c3d8d`.
- Integration branch `integration/medorigin-d2-fictional-diff-secure-20261103` was started **from PR #859 HEAD**, not `main`. PR #864 is *not an ancestor of the integration branch*: its changes were transplanted as verified source/file content. This is a **source/content integration, not a merge commit with two parent SHAs**.

## Exact content and source-retention verification

The original D2 app source from the shared ancestor contains 548 newline-split lines. PR #859's variant adds 49 lines and PR #864's adds 315 lines without deleting or modifying any of those ancestral lines; the insertions occupy **disjoint anchoring positions**. A deterministic merge interleaved their additions at original anchors into a single `src/app.rs` and preserved both feature sets. Both original 859 and 864 `app.rs` files were independently verified to be ordered **line subsequences** of the integrated source; the file now also includes a new Rust test `directional_semantic_and_hex_details_are_cleared_before_recomparing`. That test exercises end-to-end view-model creation of JSON Pointer, byte difference and HEX context from two allowlisted synthetic fixtures, clearing all rendered state, and recomputing a different pair. **Rust compile/test outcome is not verified.**

For every other touched PR #864 path, GitHub blob IDs were independently compared and confirmed **identical** after port:
`Cargo.toml`, `Cargo.lock`, `README.md`, `tests/browser_free_boundary.rs`, `tests/windows-native-fictional-compare-uia.ps1`, `tests/windows-native-fictional-json-pointer-uia.ps1`, and five source-backed evidence Markdown records for byte, HEX, semantic pointer, directional and original Windows UIA receipts (**11 of 11 matched**).

Five independently checked 859 security and keyboard paths were also **blob-identical** in integration: `tests/windows-native-fictional-compare-keyboard.ps1`, `tests/verify_linux_accesskit_maintenance.py`, `tests/linux-private-netns-smoke.py`, `tests/linux-wsl-interop-refusal-integration.sh`, `evidence/d2-wsl-interop-escape-and-fail-closed-20261103.md`, and GitHub workflow `.github/workflows/medorigin-d2-offline-evidence-validator.yml` (**6 of 6 matched including the workflow**). Other #859 files were inherited unmodified from the starting branch. No base/branch rewrite of #859 or #864.

The integration diff against PR #859's exact HEAD shows only PR #864's 12 changed paths plus the explicitly integrated app additions; no protected source/security files were deleted. Comparison against #864 remains genealogically diverged because the integration commits are not a Git merge of #864's existing history.

## Acceptance and outstanding work

**Verified now:** connector-backed source/sha identity, disjoint merged source lines, source-only presence of cross-feature regression. **Not verified now:** a native Rust compiler run, Cargo.lock real build/test, Clippy, Linux AT-SPI, Windows actual UIA key flow, the independent #864 semantic JSON pointer UIA path, macOS VoiceOver, or source-bound hosted CI on the integration head. Never describe pre-merge PR test reports as proof for this new combined head. Desktop Commander remains unavailable due to a documented monthly usage cap, even if paired/online.

Before any merge into the stacked development branch, require the exact-head native Rust Windows + Ubuntu + macOS checks, Cargo formatting/Clippy, original Windows keyboard/clear comparison tests, new Windows pointer UIA test, Linux accessibility, independent review and source-grounded provenance. **Do not merge to protected main, tag, package, sign, publish, process real patient data, install network filters on the live PC, or claim full FHIR/clinical readiness.**

Existing hard NO-GO release blockers: Windows D1 WebView2 egress #662, AccessKit/zbus maintenance #673, spoken VoiceOver #676, optional dependencies #622, independent security signoff #603 and owner release authorization #574. WSL WindowsInterop escape cannot be equated with full network confinement. This branch solves *source divergence only*, not these release blockers.
