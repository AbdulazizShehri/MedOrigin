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


## 2026-11-01 continuation: stable process-identity bracketing

A source-level attribution gap remained: `Get-CimInstance Win32_Process`
listed descendants **before** the TCP/UDP lookup, but the harness did not
revalidate the tree **after** the socket read. A departing or arriving child,
or PID substitution, could produce an incomplete or misattributed observation.

At test-first head `4c726ded4a3dc72402fc628bd99470387e287944`,
the synthetic regression failed RED because
`Assert-MxcD1StableSocketWindow` was absent. The new helper and live UIA
source integration subsequently added fail-closed checks bracketing both
initial and each of 12 sampled socket windows. A second native process census
is compared against the first by PID, start ticks, parent, process name and
preserved executable path; changed membership or unexpected socket ownership
is rejected.

At exact source head `3c57f4f6c5e4bf78a1f9294563e0a213d75f8ec1`:
- PowerShell 5.1 and 7 on the authorized Windows machine: synthetic negative
  cases PASS, including new child, departed child, PID reuse, changed parent,
  unattributed TCP/UDP owner and empty pre-snapshot.
- `[System.Management.Automation.Language.Parser]::ParseFile` on the
  guard, test and real UIA script: **0 parser errors** on PowerShell 5.1.
- [Windows 2025 Actions run 41294438061](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41294438061)
  completed SUCCESS; reviewed job 124812213745 and its negative-case log.
- Added workflow syntax-parsing gate in subsequent commit
  `c0f964e82964428a09e322003eecaf3b71a54058`.
  Its own exact-head hosted result must be separately verified.

**Limits:** This is a fail-closed observer for two inventories that
surround each socket snapshot. A process that starts and exits between
both inventories, a broker/system-service flow, a very brief TCP/UDP
exchange, DNS, or packets not represented as endpoint snapshots
could still escape observation. Nothing here is kernel packet-denial
or system policy evidence. The previously documented D1 binary and
portable supported MXC Node runtime are no longer present in the
original recorded locations on this Windows machine, so this continuation
did **not** rerun native MXC/WebView2 GUI. Full #662 remains NO-GO.
