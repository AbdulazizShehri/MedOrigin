# Windows WebView2 egress blocker — release NO-GO (2026-11-03)

**Applies to:** MedOrigin Desktop Slice 1–3, synthetic-only Tauri 2 / WebView2 branch. This is a decision record and **not** proof of isolation or permission to publish.

## Observed blocking evidence

The Slice 1 exact-tree Windows process-tree check saw `msedgewebview2.exe` descendants establish outbound IPv6 TCP/443 connections twice, at approximately 8 and 33 seconds. Recorded as `V1_NETWORK_ISOLATION_NO_GO` in `QA_RECORD.md`. Slice 2 and Slice 3 do not lift this NO-GO. Browser route restrictions, CSP, and disabled application HTTP plugins are **not** OS egress guarantees.

## External design evidence checked Nov 3, 2026

- Microsoft WebView2 official security/enterprise documentation identifies **network processes** among runtime children; renderer sandboxing is a separate issue from outbound traffic and must not be equated with network denial: https://learn.microsoft.com/en-us/deployedge/webview2-security-tools
- Microsoft official security guidance recommends ordinary, non-elevated WebView2 hosts and isolation of any necessary elevated operations. It cautions against loosening runtime permissions or relying on runtime internals for a trust boundary: https://github.com/MicrosoftDocs/edge-developer/blob/main/microsoft-edge/webview2/concepts/security.md
- Public feature request to disable WebView2 outgoing traffic exists and has no shipped mitigation established by this review; do not assume a magic browser flag: https://github.com/MicrosoftEdge/WebView2Feedback/issues/5224
- WebView2 networking uses its own `msedgewebview2.exe` processes, and firewall rules targeting the shared runtime executable affect *other* applications, so global runtime firewall denial cannot be used as a silent product-level fix: https://github.com/MicrosoftEdge/WebView2Feedback/issues/369

## Fail-closed choice pending independent engineering qualification

**Preferred safety route for a PHI-capable future:** browserless Rust/egui host (existing D2 prototype) with platform-specific process confinement, audited dependencies, matching Accessibility/UIA/AX/AT-SPI evidence and complete feature parity. D2 passing synthetic UI tests does *not* establish PHI readiness; it removes one known WebView2 runtime source of egress but every plugin, Python/model service and OS API must still be constrained.

**Alternative research track only:** test app-scoped Windows Filtering Platform (WFP) policy with disposable process identity and all verified WebView descendants, fail-closed denial of TCP+UDP IPv4/IPv6, lifecycle/restart/escape tests, offline packet capture and native UIA/UX checks. Never change machine-wide or shared `msedgewebview2.exe` firewall rules, kill runtime children, or alter global OS/antivirus settings during proof-of-concept. If app-level enforcement cannot be proven across all descendants and restarts, reject this option.

## Acceptance before this blocker can close

1. Threat model signed off independently for the exact host and WebView descendants; isolate all network-capable children and dynamic identities, including restart.
2. Repeatable Windows physical-host **process and packet evidence** with known-negative attempts, IPv4+IPv6/TCP+UDP, cold/warm startup, 8s/33s snapshots and extended idle.
3. Native UX/UIA still works; no global machine-wide security weakening or impact on unrelated WebView apps.
4. No automatic downgrade to clinical, PHI, offline or release claims. Build/release governor remains **NO-GO** until all other clinical, security, license, signature and owner approval gates pass.

**State:** Research decision only. No WFP rules or system policies modified. This branch remains a synthetic developer preview.

## 2026-11-04 — exact executable evidence and build policy (Slice 6)

New **read-only, SHA-256-bound** Windows process-tree witness:
`tests/windows-egress-exact-binary-witness.ps1`. It uses process creation time plus parent PID rather than trusting PID alone, and observes live socket *snapshots* without changing OS policy.

- Slice 5 executable `DA9F657E967BF880EA4F355801A9A1EE168C2089106B1E6FB68C65E665D9CE7D`: 21 samples, 38 observed nonloopback IPv6 TCP:443 connections belonging to WebView2 descendants; `OBSERVED_EXTERNAL_TCP_NO_GO`.
- New exact Slice 6 debug executable `BF09565876079937E35473AF5D74E9326D5A575C99B0CD00BEC42A6702A4B364`: 20 samples, 36 observed nonloopback IPv6 TCP:443 connections belonging to WebView2 descendants; `OBSERVED_EXTERNAL_TCP_NO_GO`. Native Windows UIAutomation of that exact executable **PASS**.
- Explicit Rust `build.rs` gate now refuses optimized Release or unknown/custom Cargo build profiles, allowing only debug/test; standalone policy tests **2/2 PASS**. This **does not eliminate network traffic or prove OS containment**.
- No private IP addresses, usernames, command lines or raw endpoint data included in the checked-in evidence JSON. Reports record only destination port, family, owner name and TCP state. No PHI used.
- Both observed results leave issue #662 and offline/PHI/release qualification **NO-GO**. Process snapshots miss short-lived events, DNS, UDP sends and QUIC; packet capture and enforceable OS network denial remain mandatory.
- Alternative browserless D2 egui is an existing, independently tested track (recent #867 Windows/Linux native-offline checks passed), but it remains **Draft** and not a clinical-ready replacement with full feature parity. Keep Tauri/React synthetic-only while D2 is qualified separately.

For reproducibility, limits, fail-closed wrong-hash tests and exact QA receipts see `SLICE6_SECURITY_QA.md`. No global firewall, antivirus, WFP or user preferences were modified.
