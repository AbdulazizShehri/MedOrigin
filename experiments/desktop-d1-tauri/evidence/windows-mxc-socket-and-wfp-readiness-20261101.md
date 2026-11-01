# MedOrigin D1 — Windows socket observer and WFP evidence readiness (2026-11-01)

**NONPUBLISHING / SYNTHETIC-ONLY / NO PHI / NO RELEASE.** This record
belongs to stacked Draft PR #797, on PR #787. Neither a socket snapshot
nor the tests below constitute operating-system enforced zero-egress proof.

## Finding and reproducible regression

The earlier observer excluded every `Listen`/`Bound` TCP record before
checking its local binding. Consequently, a child process listening on
`0.0.0.0` or `::` could pass the observer even though that binding
could expose an inbound listener. This is an **inbound surface**, not proof
that traffic actually crossed the host boundary.

On the authorized Windows device, the test-first commit
`b71e345e301a16d71f198e614b553c04835e30ab` produced
`D1 endpoint guard erroneously accepted IPv4 wildcard listener` (RED).
The fix at `3e6078f2fc6f5e616b11d8a0c8a3151aa7f17bb2`
rejects nonloopback/wildcard/unknown passive TCP local bindings and
unrecognized TCP states, while preserving explicitly loopback-bound
passive TCP. It retains rejection of active nonloopback/unknown TCP and
all sampled owned UDP endpoints.

- Local Windows PowerShell 5.1: the synthetic negative regression passed.
- Local Windows PowerShell 7: the same regression passed, exit 0.
- Hosted Windows 2025 Actions [run 41293816083](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41293816083):
  job `windows-source` completed SUCCESS, with all test, checkout and
  evidence-boundary steps successful; the log enumerates all new negative
  cases, including IPv4/IPv6 wildcard listeners and unknown TCP state.
- The observer's initial and twelve windowed socket snapshots call the
  new fail-closed guard. **No real native WebView2/MXC run was performed
  for this patch**. An endpoint binding is not evidence of transmission,
  and absent endpoints in sampled windows cannot prove absence of packets,
  DNS, short-lived traffic, cross-process handoff, or Windows service
  activity. This patch neither establishes containment nor resolves #662.

## Read-only WFP telemetry access check (authorized Windows device)

Read-only commands were attempted without elevation or OS policy changes:

- `auditpol.exe /get /subcategory:"Filtering Platform Connection"`:
  **0x00000522**, a required privilege is not held by the client.
- `auditpol.exe /get /subcategory:"Filtering Platform Packet Drop"`:
  same **0x00000522**.
- `Get-WinEvent -ListLog Security`: no readable metadata returned.
- Query for Security event IDs 5152/5157 (last hour): not accessible.
- Windows principal `IsInRole(Administrator)`: **False**.

Therefore this host/session cannot currently furnish **qualified WFP audit
evidence through these commands**. This says nothing about whether other
supported OS-enforced audit mechanisms could work in a separately authorized
isolated test environment. No security-event records, remote addresses,
packet payloads or personal data were copied into the repository.

## Remaining acceptance blockers — NO-GO

1. An authorized **disposable** Windows test environment must supply
   independently reviewable process-identity-bound, OS-enforced outbound
   denial evidence for TCP, UDP, DNS, IPv4 and IPv6, across cold launch,
   UI interaction, shutdown, restart and upgrade. Snapshot polling alone
   is insufficient.
2. Verify the specific Tauri IPC and local UI functions still operate;
   keep unrelated system services and global WebView2/Edge updates intact.
3. Establish that owner attribution cannot be bypassed by brief child
   processes, PID reuse, or broker/service egress; record any unavoidable
   exemptions and independently review them.
4. Maintain #662, #603, #574 and #622 release/security blockers as open
   until their independent acceptance criteria are met.

No global firewall/audit setting, installer, tag, protected-main merge,
public release, clinical data or monetized service was changed.
