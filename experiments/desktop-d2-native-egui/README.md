# MedOrigin D2 — native Rust UI (experimental, strictly nonpublishing)

This is an **isolated browser-engine-free native UI feasibility spike** derived
from the permissively licensed eframe template, not a replacement for the Tauri
D1 source candidate, the Python Research Core or the Workspace.

## Strict test scope
- Only four exact **fictional in-memory** fixture IDs from the already qualified
  D0 Rust crate, with byte-for-byte SHA-256 checks. Not a FHIR validator.
- No WebView2, JavaScript, TCP server, telemetry, EHR API, file picker,
  patient data, model, download, updater, installer or automatic cloud service
  intentionally present in this source. Dependency auditing is still required.
- Native application compilation is distinct from proving zero network egress:
  an OS-scoped packet-level observation is still required on each platform.
- The UI does not persist state or read from an arbitrary path.
- `eframe`'s `accesskit` feature is enabled explicitly (default features are
  disabled). Before enabling it, Windows UI Automation exposed **0** descendants
  of the native window; after enabling it, Windows exposed **10** accessible
  controls/text nodes, including the four synthetic fixture selectors and
  the verification button. This added Rust/Windows accessibility dependencies
  to the locked dependency graph; their licenses and advisories require review.

## Build and qualification
Use Rust 1.97.1 and checked-in Cargo.lock, from this folder:

```sh
cargo +1.97.1 fmt --all -- --check
cargo +1.97.1 test --locked
cargo +1.97.1 clippy --locked --all-targets -- -D warnings
```

Only execute `cargo +1.97.1 run --locked` on an approved graphical development
machine with sufficient disk capacity and fictional data. Windows, Linux and
macOS CI can verify compilation and pure-data unit tests; headless CI cannot
prove a window was displayed or that outbound packets never occurred.

## Native Windows runtime observation (manual and nonpublishing)

On the authorized interactive Windows machine, after building the native D2
binary and independently checking its SHA-256, run the source-controlled
fail-closed host smoke on a **fresh fixed-drive directory**:

```powershell
$exe = 'D:\MedOrigin-D1-target\debug\medorigin-desktop-d2-native-egui.exe'
$sha = '<caller-verified-build-SHA256>'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/windows-native-host-qualification.ps1 `
  -ExePath $exe -ExpectedSha256 $sha `
  -AuditDirectory 'D:\MedOrigin-D2-new-audit-dir'
```

The single host runner now verifies the caller-pinned SHA-256, copies the
approved native executable to a **new fixed-drive staging folder** under the
fresh audit directory, and verifies the copied bytes a second time. It runs
the real Windows UI Automation smoke **4/4** on that copy, verifies the same
staged digest after UIA, then relaunches that **same staged copy** for three
TCP/UDP process-tree snapshots. It refuses an absent window or mismatched
fixture result. The audit receipt `qualification.json` records
`staged_executable_sha256`, `executing_verified_copy=true`,
`interactive_uia_4_of_4_pass=true` and always
`network_isolation_qualified=false`, `clinical_qualified=false` and
`release_qualified=false` **even when all socket snapshots are clean**.

A successful *observation* exits nonzero (2); enumeration or identity failure
exits 1. Full endpoint logs remain local. The tool does not change firewall,
WebView2, installers, network or patient data. Windows CI runs five *source-only*
negative cases (wrong digest/name, relative output, UNC source and pre-existing
audit folder preservation) without launching any fixture executable.
This is a better **test-consistency boundary**, not a complete solution to
symlinks/races in a hostile filesystem or a guarantee of OS-enforced offline
runtime.

After enabling AccessKit (2026-10-29), the native window displayed a
Windows UI Automation tree with **10 descendants**. The independent
`tests/windows-native-uia-smoke.ps1` exercised the four actual selector
buttons and verification button, then matched the rendered digest for every
fictional fixture: **4/4 PASS on Windows**. The Windows CI parses this script
but does not run an interactive graphical session. On the rebuilt AccessKit
executable (author-local SHA-256
`45D19A06E5E21667A23A858BA50B6D4077C68C27F6CF6133141C61281221DF4E`),
the host probe again observed a native window and **three samples with 0
external established/all-state TCP and 0 UDP**. The RustSec audit returned
**0 known advisories** for the newly regenerated lock at test time. These
are encouraging limited observations, **not packet-level zero-egress proof**.

**All releases, merging into protected main, distribution, PHI and clinical
usage remain NO-GO** until separate acceptance, security, provenance,
dependency/licensing, accessibility, native UI, and offline-network gates.

Upstream copy-first attribution: [UPSTREAM-NOTICE.md](UPSTREAM-NOTICE.md).
