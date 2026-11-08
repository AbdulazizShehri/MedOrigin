# D2 directional fictional JSON difference ? 2026-11-03

Scope: D2 native Rust eframe developer-only interface, source-compiled fictional fixtures, no user-provided JSON, file/EHR/PHI ingestion, clipboard, telemetry, network or release.

## Change
The verified JSON Pointer difference now includes bounded left/right scalar hints for differing values, explicit JSON type labels, the side on which an object field is missing, and both array lengths. Strings are escaped and capped at 48 Unicode scalar values. Objects and arrays are summarized by counts, not serialized. Root differences are labeled (root) rather than pretending slash is the RFC 6901 root pointer. The existing deterministic shared-key-first traversal, depth bound, fixture SHA/size/status checks, and stale-result clearing are preserved.

## Verification
Native authorized Windows Rust 1.97.1, task-owned isolated sparse worktree based on Draft PR #863 9d444df8f2ee12381b1d8c1a209faf60abb1ce36.
- cargo test --locked --lib: 12/12 expected including directional missing fields, both array-length directions, JSON types, escaped pointers, bounded long scalar, and root.
- cargo test --locked --test browser_free_boundary: 6/6 expected.
- cargo fmt --all -- --check and cargo clippy --locked --all-targets -- -D warnings required before push.
- GitHub-hosted CI, macOS spoken VoiceOver, Linux AT-SPI and native Windows UIA not claimed for this change.

## Release boundary
NO-GO unchanged: #574, #603, #622, #662, #673, #676. This is not full FHIR R4 validation, an independent packet-containment result, or release authorization. No frozen research files, main branch, tags, packages or installers changed.
