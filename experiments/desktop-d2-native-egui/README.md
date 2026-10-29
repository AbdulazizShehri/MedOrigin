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

## Browser/network dependency regression guard

`tests/browser_free_boundary.rs` runs automatically with `cargo test
--locked --all-targets` in the existing Windows/Linux/macOS matrix. It checks
that D2's direct dependencies remain the native `eframe` UI plus the existing
D0 Rust contract, AccessKit remains enabled without eframe default features,
the committed lock contains no known WebView2/browser engines or selected HTTP
client/server stacks, and authored `src/*.rs` files do not introduce common
direct socket, browser, or external process-launch entry points. Four regression
tests include deliberately forbidden synthetic examples to verify the guard.

This is a **narrow code-review tripwire**, not a complete static analysis,
supply-chain guarantee, operating-system sandbox or packet-capture proof.
Platform-specific dependencies such as `tokio` and `web-sys` may appear in the
multi-platform lockfile without showing that D2 sent any network traffic. Any
intentional feature or dependency expansion needs separate review and a new
audited baseline; never relax this gate silently to enable clinical data.

## Source-bound Rust supply-chain gate (strictly nonpublishing)

`deny.toml` is the explicit `cargo-deny 0.20.2` policy for the native D2
dependency graph across Windows x86_64, Linux x86_64, and Apple Silicon. It
**denies known vulnerability advisories**, disallowed/unlicensed SPDX
expressions and unknown package registries. The license allowlist includes
font-specific `OFL-1.1` and `Ubuntu-font-1.0`, but this is NOT a waiver
of font notice/distribution obligations. No advisory IDs are silently ignored.

This source graph currently contains three **transitive Linux accessibility
maintenance notices**: `RUSTSEC-2026-0370` (`zvariant`),
`RUSTSEC-2026-0371` (`zbus_names`), and `RUSTSEC-2026-0372`
(`zvariant_derive`). See [maintenance issue #673](https://github.com/AbdulazizShehri/MedOrigin/issues/673).
The documented `advisories.unmaintained = "workspace"` policy continues to
**fail on unmaintained direct dependencies** while these transitive notices
remain explicit unresolved review risks. A fully strict `unmaintained = "all"`
scan still FAILS on three records as of 2026-10-29; no release is authorized.
This policy does not downgrade known security vulnerabilities. Re-evaluate
and migrate to the maintained zbus/AccessKit chain before any release.

The independent GitHub source-only security job compiles a **version-pinned,
locked, free `cargo-deny` CLI** and checks advisories, licenses and package
sources with a refreshed remote advisory database. It never runs patient
data, exports packages or publishes releases. Offline reproducibility of
the local policy can be checked using:

```sh
cargo deny --offline --locked check advisories licenses sources
```

An offline pass is dependent on the local advisory database age and is **not**
a substitute for an online refreshed RustSec scan. This D2 policy does not
remediate Python optional extras or historical research pins (issue #622).

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
