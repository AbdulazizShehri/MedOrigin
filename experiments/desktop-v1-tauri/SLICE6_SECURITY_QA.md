# MedOrigin Desktop Slice 6 — Windows egress witness and nonpublishing build gate

**Date:** 2026-11-04, Asia/Riyadh. Parent: Slice 5 draft PR #890, exact commit `cd19906b7afa39711a2c2c1af3dd2606ece419b6`. All changes are in a separate clean Git worktree/stacked private draft; Ink, Core, Workspace, D1/D2, `main` and OS firewall/antivirus/system configuration remain untouched.

## Security finding — definitely not closed

The last Tauri Synthetic Desktop v1 binary that passed native Windows UIA was confirmed by SHA-256 before re-launching it, and the new source-controlled process tree witness sampled all live Win32_Process descendants and owner-bound TCP endpoints. Its **observed** result is:

| Item | Baseline observation |
| --- | --- |
| Exact binary SHA-256 | `DA9F657E967BF880EA4F355801A9A1EE168C2089106B1E6FB68C65E665D9CE7D` (Slice 5 debug) |
| Verdict | **OBSERVED_EXTERNAL_TCP_NO_GO** — script exit code **2** by design |
| Samples over requested 45-second run | **21**; OS/WMI cmdlet collection takes time, no 1-second effective sampling guarantee |
| Live process tree at steady state | **8** processes, **6** `msedgewebview2.exe` descendants |
| Non-loopback TCP observations | **38** (2 connections in 19 of 21 samples) |
| Connection class | All **IPv6 / TCP port 443 / Established**, owned by `msedgewebview2.exe` |
| UDP local endpoints | **0 observed**, not proof of zero outbound UDP |
| Native app permissions changed | **None** |

See `evidence/windows-exact-binary-egress-20261104.json` (raw IP addresses deliberately omitted; only process family, destination port, state and counts stored). This reproduces the existing #662 blocker on an exact file from a real Windows run. **It is not evidence of PHI exfiltration or an application-origin HTTP call.** The user had only synthetic data.

### What the new harness does (and cannot claim)

`tests/windows-egress-exact-binary-witness.ps1` validates SHA-256 **before process launch**, enumerates descendants by exact parent/creation-time identity to mitigate recycled PID attribution, samples all TCP connection states and local UDP endpoints, refuses host process identity changes, records redacted JSON, and terminates only the process it started.

- Hash mismatch refuses to launch. Verified with an all-zero wrong hash: **nonzero exit, no report and no launched target**.
- Synthetic selftest covers nested process ancestry, recycled parent/root IDs, IPv4 and IPv6, IPv4-mapped loopback and refusal of a supposed "clean" snapshot as a security PASS.
- **Every real-probe outcome is NO-GO**: observed TCP = exit 2, inconclusive zero-observed-TCP = exit 3, incomplete/error/reused PID = exit 4. There is deliberately **no success exit code 0** for a live egress scan. Only `-SelfTest` returns success for the local test suite.
- This is **observational socket enumeration, not Windows Filtering Platform enforcement, ETW, packet capture, DNS capture or full TCP/UDP/QUIC proof**. A zero observation would not qualify the host. No global firewall rule, network block, WebView2 override or system policy was added.

Microsoft source semantics:
- Get-NetTCPConnection exposes live owner, remote endpoint, state: https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-nettcpconnection
- Get-NetUDPEndpoint exposes bound **local** UDP sockets, not complete remote UDP send history: https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-netudpendpoint
- Win32_Process ParentProcessId can be recycled and CreationDate is needed to detect mistaken ancestry: https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process

### Fail-closed unauthorized release build guard

`src-tauri/build.rs` now invokes `build_gate.rs`, which accepts Cargo `PROFILE=debug` / `test` only. `release`, custom, unknown or missing profiles **panic at the Rust build-script boundary** until source is independently reviewed/updated. No environment variable or command-line bypass has been provided. This addresses the risk of accidentally building a publishable optimized binary **without pretending to fix WebView2 egress**. It does not prevent someone from distributing an unsafe debug executable manually, and it is not an OS sandbox.

The standalone Rust build-gate tests run via `rustc --edition=2024 --test build_gate.rs`, and Cargo tests validate that debug builds still work. Only source control review can lift the build guard after explicit evidence; the app's runtime `release_authorized=false` and `webview_egress_qualified=false` remain unchanged.

## D1/Tauri vs D2/native security direction

D2 (native Rust/egui) is a **real existing browser-engine-free** experiment with source-bound checks, accessible Windows native UI, and separate Windows/Linux/macOS qualification workflows. Recent D2 stack PR #867 has recorded Windows and Linux `native-offline` CI passes and a structure check, but it remains a **draft**. D2's no-browser source contract does **not** imply all transitive behavior/clinical functionality or a ready production host; its own documented release, OS sandbox and dependency maintenance gates remain.

**Decision:** do not weaken, patch, or impersonate WebView2 OS confinement via Chrome flags or a globally targeted firewall rule. Preserve Tauri/React as the current polished **synthetic-only demo**, and treat native D2 as the **stronger host candidate for genuinely sensitive offline data**, subject to complete feature parity, independent packet/network-denial qualification and design/accessibility review. This is a scoped engineering recommendation, not a unilateral release or UI rewrite.

## Exact-source qualification table

| Check | Status |
| --- | --- |
| Witness pure synthetic/PID/loopback selftest | **PASS** |
| Wrong SHA fail-closed no launch | **PASS** |
| Exact Slice 5 Windows real-process network witness | **NO-GO confirmed** (21 samples, 38 external IPv6 TCP:443 observations) |
| Standalone Rust build-gate unit tests | **2/2 PASS**; exact new Debug Tauri build also passed. A full Release build was deliberately **not attempted**; denial comes from the tested build-script guard logic |
| Rust `cargo test --locked` on Slice 6 | **26/26 PASS** (all inherited strict fictional-only Rust gates preserved) |
| Rust fmt/clippy on Slice 6 | **PASS**: `cargo fmt --all -- --check` and `cargo clippy --all-targets -- -D warnings` |
| Exact Slice 6 Tauri debug build & new binary egress witness | **Build PASS, egress still OBSERVED_EXTERNAL_TCP_NO_GO (exit 2)**: SHA-256 `BF09565876079937E35473AF5D74E9326D5A575C99B0CD00BEC42A6702A4B364`; **20 samples**, **36 IPv6 TCP/443 established observations** (2 in 18 samples), steady tree 8/6 WebView2; redacted evidence in `evidence/windows-exact-binary-egress-slice6-20261104.json` |
| Exact Slice 6 native UI Automation | **PASS** on the identical hash-bound executable: exact fictional hashes, JSON source, nested-key structure, provenance links, second timeline route, filters and re-verification, with native Dark/Light screenshots at 125% DPI (temporary local captures, not committed again) |
| Windows Filtering Platform confined packet-level denial | **NOT RUN, still NO-GO** |
| D2 browserless clinical-grade full capability parity | **NOT QUALIFIED** |

## Remaining release blockers

- <https://github.com/AbdulazizShehri/MedOrigin/issues/662> WebView2 external egress is **still unresolved**. The observational harness does not close it.
- No PHI/patient-data ingestion, EHR, clinical authorization, model execution, full Core/Workspace bridging, installers or public releases.
- Default-branch Dependabot vulnerabilities, independent reviews, native macOS/Linux parity and other clinical/release gates remain open.
- Existing stacked desktop PRs are nonpublishing drafts; **no merge or release** occurred.

**Important:** an empty TCP snapshot must NEVER become a pass. A lack of malicious intent or a passing local unit test does not establish safe handling of sensitive health information.
