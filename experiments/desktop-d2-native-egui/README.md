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

**All releases, merging into protected main, distribution, PHI and clinical
usage remain NO-GO** until separate acceptance, security, provenance,
dependency/licensing, accessibility, native UI, and offline-network gates.

Upstream copy-first attribution: [UPSTREAM-NOTICE.md](UPSTREAM-NOTICE.md).
