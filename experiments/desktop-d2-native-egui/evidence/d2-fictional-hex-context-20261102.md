# D2 bounded fictional first-difference HEX ? 2026-11-02

## Source and scope

- Private repository: AbdulazizShehri/MedOrigin.
- Parent: unmerged Draft #860, exact source SHA e7e7fc04a4127f16cad446ce0707e0f78a97d0b9.
- Task branch: feat/medorigin-d2-hex-context-20261102-run11.
- Developer-only native Rust eframe D2: show at most 8 original UTF-8 source bytes before and after the first difference in uppercase hexadecimal for each separately verified, source-compiled fictional JSON. This is NOT a semantic JSON or FHIR comparison, not clinical validation, and not an external file import.
- Invalid selection, same-fixture refusal, fresh Verify, and selection changes retain fail-closed clearing behavior for the entire comparison, including the new HEX line.
- No PHI/EHR, network, clipboard, persistence, installers, signing, tags, releases, or protected main merge.

## Native Windows qualification (authorized PC)

- Actual cargo test --offline --locked --all-targets in D2: 10/10 app tests PASS, 6/6 no-browser/network source-boundary tests PASS; no failures.
- New Rust test verifies identical data, Unicode UTF-8 byte offsets (explicit U+00E9 escape to avoid Windows console codepage ambiguity), insertion, and bounded 8-byte windows.
- Actual cargo clippy --offline --locked --all-targets -- -D warnings: PASS.
- cargo fmt --all: PASS.
- Actual cargo build --offline --locked: PASS.
- Native executable SHA-256: 228FB11A87696AFE3662733DBC96EB22C4F007AEF5583BEAA0BCB8350D610107.
- Source-controlled real Windows UIAutomation windows-native-fictional-compare-uia.ps1 with exact binary SHA: 3/3 PASS (Patient-vs-Observation exact raw HEX derived independently from D0 fixtures; same-selection refusal clears stale context; fresh Verify clears stale context).
- First RED test revealed Windows codepage corruption of a literal Unicode test string; corrected source test to use an ASCII-only Rust Unicode escape, then GREEN tests and Clippy passed.

## Explicit limitations

- No hosted GitHub Actions intentionally requested for this task because private-repository free quota could not be confirmed; [skip ci] used on source commit. Do not claim hosted Linux/macOS qualification for this new HEX UI.
- Existing hard release blockers #574, #603, #622, #662, #673 and #676 remain OPEN / NO-GO. New native D2 feature is not WebView2 OS packet-containment evidence and does not address zbus5 maintenance or spoken VoiceOver.
