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

The audit checks approved executable name/digest, actual window presence,
three TCP/UDP process-tree snapshots, and writes `qualification.json` with
`network_isolation_qualified=false`, `clinical_qualified=false` and
`release_qualified=false` **even if every snapshot is clean**. A successful
*observation* exits nonzero (2); enumeration/identity failure exits 1. Full
endpoint logs remain local. The tool does not change firewall, WebView2,
installers, network or patient data. The Windows CI source-only test checks
three negative cases without launching any GUI.

First local D2 result (2026-10-29): an actual top-level Windows window
was observed and three samples reported only two process-tree entries,
**0 established external TCP, 0 all-state external TCP and 0 UDP**. This
is an encouraging *snapshot observation*, not a packet-level guarantee.

**All releases, merging into protected main, distribution, PHI and clinical
usage remain NO-GO** until separate acceptance, security, provenance,
dependency/licensing, accessibility, native UI, and offline-network gates.

Upstream copy-first attribution: [UPSTREAM-NOTICE.md](UPSTREAM-NOTICE.md).
