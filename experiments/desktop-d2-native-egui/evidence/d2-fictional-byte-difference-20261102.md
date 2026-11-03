# D2 exact fictional byte-difference qualification — 2026-11-02

## Scope and source lineage

- Repository: `AbdulazizShehri/MedOrigin` (verified PRIVATE before writing).
- Branch: `feat/medorigin-d2-fictional-byte-diff-20261102`, stacked on unmerged Draft #859, source parent `5aaf289d698054a73db9de64efd5e7939f6c3d8d`.
- Tested native D2 source commit: `0a1e713e49ac288b6576db64403244a34d4f30f7` (after rustfmt, with the source-controlled Windows UIA assertion). Subsequent documentation-only commits do not alter the tested Rust source.
- All comparisons use only two independently reverified, source-compiled fictional JSON strings, each bounded to 2,048 bytes. No file input, clipboard, persistence, network or real patient data.

## Functional behavior

The read-only comparison now displays a byte-exact, zero-based first differing offset, common unchanged suffix length and both original byte lengths. It uses UTF-8 **byte** positions, not character offsets, and never normalizes or interprets JSON. Identical strings are explicitly reported. An invalid/duplicate selection, a new Verify, or a fixture change removes the old comparison and its summary before any new success can appear. No FHIR R4 clinical or semantic difference claim is made.

## Actual authorized Windows evidence

The user-authorized Windows device ran local Rust 1.97.1 offline/locked with the isolated worktree `D:\\MedOrigin-D2-ByteDiff-20261102`:

- `cargo test --offline --locked --all-targets` on the D2 manifest: **9/9 app tests PASS**, **6/6 browser/network source boundary tests PASS**, no failures. The new test covers identical, inserted, Unicode multibyte, and prefix-only byte differences.
- `cargo fmt --all` applied, and the resulting Rust source was committed; `cargo clippy --offline --locked --all-targets -- -D warnings`: **PASS**.
- `cargo build --offline --locked`: **PASS**. Native executable SHA-256: `04F37A232C05CED19F4BF50AE086F6A5F33E07D996CA615269C68F0ED13EE02B`.
- Real native Windows UI Automation via `tests/windows-native-fictional-compare-uia.ps1`: **3/3 PASS**. It verified both exact fictional JSON texts, SHA labels and exact new summary `first differing byte offset 17 (zero-based); common suffix 1 bytes; left 57 bytes, right 251 bytes`; then proved that a same-fixture refusal and a subsequent Verify remove stale source text and the byte summary. The test independently validates the executable SHA against the supplied expected digest, but this is **not** third-party binary signing or human attestation.

## Deliberate limits / remaining NO-GO

- No hosted GitHub Actions were deliberately launched for this private-repository change because free-minute billing availability was not verified. **No hosted CI PASS claim** for this head.
- New byte-summary UI not independently replayed on Linux AT-SPI or macOS VoiceOver; prior native accessibility evidence applies only to earlier source heads. Real spoken VoiceOver and second-device independent acceptance remain missing.
- This is source-only synthetic developer functionality. It does **not** prove Windows D1 WebView2 broker/descendant packet containment, Linux zbus5 maintenance remediation, full FHIR R4 validation, clinical suitability, human security review, signing or release readiness.
- All six existing release gates remain open: #574, #603, #622, #662, #673, #676. No protected-main merge, tag, installer, publication, PHI, root research lock mutation or host security-policy change.
