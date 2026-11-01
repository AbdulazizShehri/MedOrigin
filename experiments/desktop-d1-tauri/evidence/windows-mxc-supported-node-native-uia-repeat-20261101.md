# MedOrigin D1 native MXC/WebView2 qualification — repeat 1/2, 2026-11-01

**NONPUBLISHING / synthetic fixtures only / no PHI / NOT release-qualified.**
This is a real, authorized interactive Windows GUI run, not hosted source CI.
The result is scoped to an older, separately pinned *unpublished* D1 preview
binary; it is **not a rebuild from PR #797** and does not qualify a release.

## Exact inputs (source and binary verified before launching)

- D1 test source: exact branch commit
  `7d1a443e89b703c5fd45ec10b186a785d9f086ad` of stacked Draft PR #797.
  Six runner/guard sources were downloaded from the immutable GitHub commit
  and checked against their Git blob SHA-1, all six matched.
- `windows-mxc-d1-real-app-qualification.mjs` blob
  `d3cadc83e2bb329d69006e27025b2f81a9279735`.
- `windows-mxc-d1-real-uia-qualification.ps1` blob
  `a257a0c8778c2bc3c5e1a1a8e66646ed7b51d6c3`.
- `windows-mxc-d1-network-endpoint-guard.ps1` blob
  `5e5225f880919a2052668744484a87e7c748ac85`.
  The companion Node admission and root/descendant continuity scripts were
  also independently blob-SHA-verified before the run.
- Older *unpublished* synthetic-only D1 preview executable, copied to a
  temporary QA folder, 13,215,232 bytes, SHA-256
  `7eceea367a05ce60576d633ff48f593d8dbff9ed2a56ff227d37c2280759b74a`.
- Node.js `v24.22.1` from an already installed local application runtime,
  SHA-256 `6932215721e085e83c43a61c0ae06c5182be8909a7abab3a45d4148d81af709d`;
  **not** a global Node install or independently signed Node download.
- `@microsoft/mxc-sdk@1.0.1` installed into the ephemeral QA folder
  from an existing local npm cache with `--offline`; package version
  independently returned by `npm ls`. Its `getPlatformSupport()` returned
  `isSupported=true` and included `processcontainer`. SDK integrity is
  limited to the npm-cache/install validation (no detached signature claim).
- Authorized interactive Windows session, non-admin, with process-contained
  GUI and SDK request declaring egress/ingress default deny and
  `hostLoopback` deny. No host-wide firewall, audit or Edge/WebView2
  update setting changes.
- No genuine patient, EHR or clinical data. No installer, release or network
  upload of application data.

## Two separate real ProcessContainer interactive runs

| Observation | Run 1 | Run 2 (clean subsequent launch) |
|---|---|---|
| Minimal Patient UIAutomation / SHA | PASS | PASS |
| Invalid UTF-8 UIAutomation / SHA | PASS | PASS |
| Oversize Payload UIAutomation / SHA | PASS | PASS |
| Exact-Limit Payload UIAutomation / SHA | PASS | PASS |
| Root process-tree count | 8 | 8 |
| Real WebView2 child process count | 6 | 6 |
| Initial owned TCP / nonloopback TCP / UDP endpoints | 0 / 0 / 0 | 0 / 0 / 0 |
| 12 identity-bracketed socket samples: max owned TCP / UDP endpoints | 0 / 0 | 0 / 0 |
| MXC runtime `warnings` | [] | [] |
| MXC bounded interactive timeout | `timedOut=true`, `exitCode=-1` | same |
| Node qualification launcher exit | 0 | 0 |
| Exact-path root process remaining after run | 0 | 0 |
| Owned MXC temporary dirs remaining after run | 0 | 0 |

Both runs printed
`D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO`.
Timeout of the GUI container is an **expected controlled observation boundary**,
not a claim that the product naturally shut down. The second run was performed
after checking that the prior run's exact executable path had zero remaining
root processes and no MXC temporary test directories.

## What was NOT proven — #662 remains OPEN / NO-GO

- No WFP/kernel-level packet denial, firewall enforcement or trusted
  inbound/outbound packet counters were collected in this non-admin session.
- Snapshot polling can miss short-lived TCP/UDP/DNS/IPv4/IPv6 flows, proxy
  or broker/service egress, traffic between samples, or exits between identity
  censuses. A zero count in twelve snapshots is not zero-egress attestation.
- No sustained WFP deny-telemetry test, cold-boot OS lifecycle, WebView2
  auto-update/restart lifecycle, OS update tests, packet-level IPv6/DNS test
  or independent security reviewer sign-off. This was only two app launches.
- No modern D1 executable was built from the latest proposed product source,
  and the tested executable remains unpublished/synthetic-only.
- This source guard is an *observer* and is not the application's production
  network-isolation mechanism.

**Decision: continue NO-GO** for release, PHI, clinical use, public artifacts
and protected-main integration. Keep release/security issues #662, #603,
#574 and #622 open. The temporary QA installation is to be cleaned after
storing this evidence in GitHub.
