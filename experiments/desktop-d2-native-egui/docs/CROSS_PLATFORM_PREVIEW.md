# MedOrigin D2 — native cross-platform synthetic preview (NOT RELEASE)

## Actual deliverables

The same native Rust/egui D2 source builds for Windows x86-64, macOS Apple Silicon, and Linux x86-64. It intentionally does **not** use Tauri/WebView2. Each private developer-preview archive contains one native executable (inside an unsigned `.app` for macOS), `LICENSE`, `UPSTREAM-NOTICE.md`, `README-SYNTHETIC.txt`, and `MANIFEST.json` with the exact Git commit and binary SHA-256.

This is *not* the finished MedOrigin desktop healthcare product. It supports only the committed fictional D0 fixture browser, SHA checks, limited JSON inspection/comparison and pinned synthetic reference inspection. It is **not connected** to the actual Python Research Core or Clinical Workspace; no real patient data, EHR writes, clinical models, production install or claims of offline security.

| Host | Tested native architecture | Portable developer-preview archive | Current deployment limitations |
| --- | --- | --- | --- |
| Windows | x86_64 | `MedOrigin-Synthetic-D2-windows-x86_64-<commit>.zip` | Unsigned .exe, Windows SmartScreen may warn; not MSI/MSIX |
| macOS | arm64 Apple Silicon | `MedOrigin-Synthetic-D2-macos-arm64-<commit>.zip` containing unsigned `.app` | No Developer ID signature/notarization, Gatekeeper may block; Intel Mac not qualified here |
| Linux | x86_64 glibc | `MedOrigin-Synthetic-D2-linux-x86_64-<commit>.tar.gz` | Requires compatible system GL/X11/Wayland runtime libraries; not AppImage/Flatpak/deb/rpm |

## Exact local build and packaging

**Run this only with a pinned, reviewed commit and Rust 1.97.1.** The scripts use Python standard library only, no network access and no extra packaging dependencies.

From `experiments/desktop-d2-native-egui`:

```bash
cargo +1.97.1 fmt --all -- --check
cargo +1.97.1 test --locked --all-targets
cargo +1.97.1 clippy --locked --all-targets -- -D warnings
cargo +1.97.1 build --locked
python3 -m unittest discover -s scripts -p 'test_*preview.py' -v
python3 scripts/package_preview.py \
  --binary target/debug/medorigin-desktop-d2-native-egui \
  --output ./private-preview
python3 scripts/verify_preview.py --archive ./private-preview/MedOrigin-Synthetic-D2-*.tar.gz
```

On Windows PowerShell use `python`, `target\debug\medorigin-desktop-d2-native-egui.exe`, and verify the actual `.zip` instead of `.tar.gz`. The scripts refuse mismatched binary formats/CPU architecture, wrong executable names, symlinked binary inputs, missing safety labels, malformed manifests and attempts to overwrite an existing archive.

On macOS, a local archive holds `MedOrigin Synthetic Preview.app` with `Contents/Info.plist` and the host-native arm64 executable. A signed/notarized distributable is *separate future work*. Do not disable Gatekeeper or security controls to use this preview in a healthcare environment.

On Linux, this is a **native glibc executable**, not a self-contained AppImage. For Ubuntu/Debian X11 runtimes, a confirmed missing dependency was resolved with `sudo apt-get install libxkbcommon-x11-0` (and its `libxcb-xkb1` dependency). GL/X11/Wayland runtime libraries must also be available. The CI job uses Xvfb with software Mesa and asserts a real native window title, but that does **not** qualify every distro, Linux AT-SPI accessibility or OS network isolation.

## GitHub Actions

`.github/workflows/medorigin-d2-crossplatform-portable.yml` compiles/tests the exact PR SHA on Windows 2025, Ubuntu 24.04 and macOS 15. Jobs upload archives as **short-lived private Actions artifacts** (retention 3 days) with `MedOrigin-D2-SYNTHETIC-ONLY-` names; there are no publishing, signing, app-store or release steps. A GitHub artifact is not a production installer, and private-repository runner minutes may count against account quotas.

## Strict archive verification (synthetic-only)

The verifier checks the exact source-commit-derived archive filename, the canonical set of five (Windows/Linux) or seven (macOS) regular files, byte-for-byte safety labels, source-tree LICENSE/UPSTREAM notice, macOS bundle metadata, permissions, binary header and SHA-256 recorded in the canonical manifest. It rejects duplicate member names, aliases, symlinks/special files, unsafe metadata, substituted contents, and bounded-size violations **before extracting anything to disk**. Run the packaging and adversarial verifier tests via `python3 -m unittest discover -s scripts -p 'test_*preview.py' -v`.

**Critical limit:** this is a local self-consistency check, **not** a code-signing, independent provenance, or reproducible-build proof. An adversary able to replace both an executable and its self-attested manifest can still make the archive self-consistent; the verifier does not prove that binary was compiled from the reviewed source. Never trust an untrusted ZIP/TAR simply because this check passes, nor treat this as PHI/network isolation clearance.

## Mandatory release blockers

A build or archive verification pass cannot grant these missing qualifications:

1. OS-enforced, independent network isolation proof on **each OS** (not mere clean socket snapshots), sandbox/lifecycle verification, and a documented policy against PHI exfiltration.
2. Feature-complete, supervised local bridge to the real MedOrigin Python Core/Clinical Workspace, with storage encryption, access control, consent, FHIR semantics, auditability, import/export and recovery.
3. OS-specific real GUI and accessibility tests: Windows UIA, macOS AX, Linux AT-SPI with actual distribution binaries, plus supported rendering paths.
4. Updated Rust/Python dependency advisory remediation and licenses, independent security assessment and clinical-risk testing, app store/device signing and notarization where required.
5. Product design and owner release approvals. The Tauri/WebView2 external egress [issue #662](https://github.com/AbdulazizShehri/MedOrigin/issues/662) remains open independently.

**No merge to main, no public release, and no real patient files or clinical workflows until all gates are satisfied.**
