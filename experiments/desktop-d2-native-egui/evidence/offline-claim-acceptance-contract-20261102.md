# MedOrigin D2 — offline claim acceptance contract (nonpublishing)

**Status:** BLOCKED / NO-GO. **Date:** 2026-11-02. **Source baseline:** D2 Draft #857 at `4af4fb057c8dbdb231efd4f82f16fe299284feb3`. This is a test specification, not evidence that isolation is implemented or successful.

## Motivation / observed failure

Issue #662 recorded established **non-loopback TCP/443** sockets from Windows WebView2 child processes even when Tauri capabilities and CSP limited application fetches. `--disable-background-networking` did not consistently prevent sockets. Application-level denial or a brief empty TCP snapshot is therefore **insufficient** to claim fully offline operation. A native eframe D2 process avoids WebView2 but must separately prove its own per-process and child-process boundary; absence of a browser dependency alone proves nothing about DNS, UDP, updates, or future dependencies.

## Test boundary

- **Artifact:** exact-source, SHA-256-pinned D2 native executable and all attributable descendants; repeat separately for D1 Tauri/WebView2 if D1 is still a supported shipping path. Never substitute D2 results to close D1's #662.
- **Network scope:** outbound/inbound non-loopback IPv4/IPv6 TCP, UDP, DNS and proxy-mediated attempts, including refused connections (not just ESTABLISHED), over cold launch, stable idle, all twelve synthetic selections, JSON inspection success/refusal, shutdown, restart, and upgrade simulation when packaging exists.
- **Isolation policy:** a documented application-scoped OS-enforced deny boundary with explicit and reviewable enforcement scope, applying before launch and surviving child creation. Do not disable machine-wide WebView2/Edge updates or blanket-block a shared executable. Protect other users and applications.
- **Inputs:** embedded fictional fixtures only. Do not capture PHI, EHR data, browsing sessions, credentials or raw packet payloads. Use a disposable test machine/account and test-only packet metadata where possible.
- **Environments:** actual supported Windows build and Linux/macOS where claimed. A hosted CI Linux check is not proof of Windows containment. If a platform cannot enforce/observe the boundary, its offline claim remains blocked.

## Acceptance matrix (all mandatory; fail closed)

| ID | Test | Required proof | Failure condition |
| --- | --- | --- | --- |
| NET-01 | Pin executable and complete process tree | Signed-off source ref, SHA-256, tree/PID timeline, OS/build info, tool versions | Binary mismatch, descendant enumeration gaps |
| NET-02 | Deny before process launch | Auditable policy tied to the application execution boundary; child inheritance and policy failure behavior | Policy attaches after launch or can silently fail open |
| NET-03 | Cold start and idle | OS packet/event capture covering both IP families, DNS and TCP/UDP attempt events, with synchronized clock | Any unexplained outbound attempt attributable to the app boundary |
| NET-04 | Exercise all fictional cases | Timestamped synthetic UI interaction trace for 12 fixtures, positive/negative JSON preview, and capture coverage | Any fixture skipped, ambiguous PID ownership, packet gap |
| NET-05 | Shutdown/restart/crash | Captures continue until all attributable descendants exit; repeat with recovery and simulated abrupt termination | Orphans escape policy or capture stops too early |
| NET-06 | Negative-control injection | A safe test-only child intentionally attempts DNS, TCP and UDP egress; telemetry **must** detect attempt and enforced deny must block it | Attempt goes undetected or exits boundary |
| NET-07 | Internal function preserved | Source-controlled fictional SHA / envelope UI remains usable under isolation | UI silently breaks or requires external access |
| NET-08 | No global disruption | Independent benign WebView2/Edge application and normal host updates unaffected | Machine-wide rules, globally disabled updates |
| NET-09 | Independent review | Separate reviewer reproduces, evaluates all raw **non-PHI** evidence and signs exact platform/artifact scope | Reviewer absent, unexplained exemptions, incomplete evidence |

## Evidence packet

For each platform and binary SHA, retain: source revision; command transcript and harness SHA; OS image/build; enforced policy definition and its lifecycle; capture tool version/configuration; time-synchronized DNS/TCP/UDP metadata; parent/child process ownership timeline; negative-control results; failed-policy tests; bounded synthetic interaction log; reproducibility commands; an explicit exemption ledger with rationale, approver, expiry and independent reviewer identity. Store evidence without patient data or secrets. Distinguish *blocked attempted egress* from *no attempt observed*, and *no packet escaped* from merely *no established sockets seen*.

## Decision rule

**No offline, zero-egress, local-private clinical or release claim** until all mandatory NET checks pass for each shipping platform and binary with independent review. Any missing capture window, ambiguous process, failed enforcement, unsupported OS, missing negative control, or unexplained egress keeps **NO-GO**. D1 #662 remains independently open regardless of D2 status. Other blockers #673 (Linux unmaintained zbus), #676 (spoken macOS VoiceOver), #603 (security), #622 (dependency advisories) and #574 (owner release/signing) are separate and cannot be waived by this packet.

## Next engineering slice

Implement a **fail-closed, disposable, synthetic-only test harness** that (1) verifies a pinned binary and policy before launch, (2) associates all descendants with telemetry, (3) runs a bounded negative DNS/TCP/UDP control plus fictional UI interactions, (4) writes machine-readable PASS/FAIL/UNKNOWN for each NET gate, and (5) exits nonzero for UNKNOWN as well as FAIL. Get independent security review before claiming any platform passes. This document deliberately does not request elevation or mutate host firewall rules.
