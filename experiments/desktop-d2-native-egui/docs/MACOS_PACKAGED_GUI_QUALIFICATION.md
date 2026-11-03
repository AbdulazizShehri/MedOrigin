# macOS exact-archive D2 native GUI qualification — 2026-11-04

**Private synthetic developer preview only. Not an app release, accessibility certification, clinical FHIR validation or OS network isolation approval.**

## Source and tested artifact

- Parent source: private Draft PR #898, immutable commit `83bc536246ea7111c9308ffc24428ed53a37ade6` (stacked on #896). This qualification adds a separate source-controlled harness without changing the compiled Rust source. The parent package source was rebuilt on an authorized Apple Silicon Mac with Rust 1.97.1 and `--locked --offline`.
- Host: real arm64 Apple Silicon, macOS 26.6.2.
- Internal-only local archive: `MedOrigin-Synthetic-D2-macos-arm64-83bc5362.zip` — SHA-256 `4a5bb40a91f8119f275ed0b91f8e91f18018c77f04ad0ccf88d1279b5c8d4f6d`.
- Actual compiled native `medorigin-desktop-d2-native-egui` — SHA-256 `d796824aa596fd2bac37d319f5cad2aad6ab40f27322a1d284401d9d45f6b81b`.
- `scripts/verify_preview.py` first accepted the exact canonical 7-file ZIP layout/source content and reported `SYNTHETIC_ARCHIVE_SOURCE_CONTRACT_VERIFIED_NOT_RELEASED`.

## Reproducible authorized interactive Mac procedure

From `experiments/desktop-d2-native-egui` in the exact source checkout:

```sh
python3 -m unittest discover -s scripts -p 'test_*preview.py' -v
cargo +1.97.1 build --locked --offline
python3 scripts/package_preview.py --binary target/debug/medorigin-desktop-d2-native-egui --output /tmp/medorigin-d2-preview-local-only
python3 scripts/macos_archive_gui_preview.py --archive /tmp/medorigin-d2-preview-local-only/MedOrigin-Synthetic-D2-macos-arm64-<commit8>.zip
```

The live script requires an interactive authorized Apple Silicon Mac and Accessibility permission for its process. It verifies the source-commit ZIP member contract, extracts only the seven canonical files to a new mode-0700 temporary directory, verifies extracted bytes/modes against the source **again**, checks the embedded executable digest, launches exactly that local native executable, uses the original macOS AX four-fixture and FHIR AX eight-fixture testers, confirms the running executable SHA in the eight-fixture tester, rehashes the binary, terminates only the process it launched, and deletes its temporary bundle. Any missing AX permission, changed content, failed native launch or failed AX action is a refusal, not a skip/silent pass.

## Actual observed live outcomes

- **24/24** source-level Python tests **PASS** on the Apple Silicon Mac, including new negative cases for noncanonical ZIP, permission/world-readable destination, symlinked destination, changed Info.plist, changed license *after deliberately mocking an earlier admission*, existing bundle reuse, nonzero AX subprocess exit and wrong OS.
- Native app launched from the **verified extracted archive**, not an unqualified standalone development executable.
- macOS NSAccessibility original primary fictional Patient interactions **4/4 PASS** with exact visible source SHA-256 results.
- Additional Observation/Bundle fictional AX interactions **8/8 PASS** with distinct source SHA-256 and synthetic envelope-status checks.
- Final `MACOS_D2_EXACT_ARCHIVE_REAL_AX_PASS_SYNTHETIC_ONLY_NOT_RELEASE` emitted, process exit zero. Repeated once after extracted-byte recheck was added, with **all 12/12 GUI interactions passing again**.
- No release installer/notarization, external service or real patient record was used.

## What this does *not* prove

This is a **single-host** test of an **unsigned, nonproduction** developer-preview bundle launched by direct executable path. It does not establish Finder/LaunchServices distribution, notarization/Gatekeeper behavior, VoiceOver spoken output, independent accessibility approval, keyboard-only parity across the platform, absence of outbound DNS/TCP/UDP/child process traffic, independent binary/source attestation, or clinical FHIR R4 correctness. Source-controlled unit tests can run on other OSes; this real macOS AX test must never run in headless CI as a fake pass. Issue #676 remains open for spoken accessibility and #662 for separate D1 WebView2 networking. Other #673 Linux AccessKit transitive maintenance, #603 independent security assessment, #574 governance/release authorization and Core/Workspace parity remain NO-GO. Preserve protected main; no signing, publishing, production PHI or clinical use.
