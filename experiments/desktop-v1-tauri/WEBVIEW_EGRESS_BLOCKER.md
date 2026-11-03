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
