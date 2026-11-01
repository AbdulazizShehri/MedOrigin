# Windows D1 passive WFP/DNS observer availability: actual host metadata, NO packet proof

**2026-11-02 Asia/Riyadh • authorized Windows PC • NONADMIN •
synthetic-only source engineering • APP-NETWORK SECURITY STILL NO-GO.**

## Scope / source provenance

- Exact parent [Draft PR #812](https://github.com/AbdulazizShehri/MedOrigin/pull/812)
  SHA `02283e2e25aa9d4c83f1ce3ef6638692ba403c4d`
  provided existing T1 clean Git provenance and T2 source-only checks.
- Newly executed code/CI before this documentation commit:
  **`4c2ea3192a7309e4f7ac084110a8e03574c46d19`**.
  Full clean detached authorized Windows git worktree on `D:\`
  and separate original repo unchanged on its own branch.
- The new `windows-d1-passive-os-observer-inventory.ps1` reads
  **Windows operating-system VERSION**, current process
  **non-admin status**, registered ETW *provider metadata* via
  `Get-WinEvent -ListProvider`, WFP/DNS log ENABLED/DISABLED
  metadata via `Get-WinEvent -ListLog`, and existence of
  `pktmon.exe` and `Get-NetEventSession` command names.
- This script **does not run `Get-WinEvent` against event records,
  invoke `Get-NetEventSession`, create/start/stop event/packet
  capture, change WFP/ETW/firewall/logging policy, request elevation,
  make network connections, collect event messages, addresses,
  process paths/names, host identifiers or patient data**.
- The JavaScript verifier requires a **single bounded canonical
  JSON line with exact keys and booleans** and obtains the
  **clean identical Git SHA before and after** the metadata
  query. Source drift, dirty/untracked paths, elevated process,
  malformed or duplicate JSON, invented packet status,
  unsupported OS, extra fields, warnings and failed subprocess
  cause **fail-closed NO-GO**. Every output object expressly
  contains `packetCaptureStarted=false`,
  `osPacketDenyProven=false`,
  `reason=NO_ACTIVE_INDEPENDENT_PACKET_OBSERVER`.

## Actual RED and GREEN

- **RED** at exact test-only branch source
  `e8ff70840186cb6698e97d186901a2712ed87ace`:
  authorized Windows Node v24.19.0
  `node --test windows-d1-passive-os-observer-inventory.test.mjs`
  returned **exit 1** with `ERR_MODULE_NOT_FOUND`,
  as no implementation existed. This is a missing-module
  test-first baseline, **not a proven WFP escape vulnerability**.
- After implementing source-only metadata code and tests,
  **exact code source SHA
  `4c2ea3192a7309e4f7ac084110a8e03574c46d19`**:
  actual authorized non-elevated Windows OS `10.0.26300`,
  real local **35/35 combined T1+T2/new Node regression PASS,
  0 fail, 0 skip**, and actual native metadata CLI **exit 0**
  with source git clean before+after.
- [Exact SHA hosted Windows source-only CI #41362427522](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41362427522)
  **COMPLETED SUCCESS**, raw logs inspected:
  **35/35 PASS, 0 fail, 0 skip**. Hosted source-only
  tests use mocked metadata; not claimed as independent
  physical-host packet monitoring.

## Sanitized actual native receipt

```json
{
  "schema": "D1_PASSIVE_OBSERVER_FEASIBILITY_V1",
  "sourceSha": "4c2ea3192a7309e4f7ac084110a8e03574c46d19",
  "status": "READ_ONLY_METADATA_ONLY",
  "osBuild": "10.0.26300",
  "elevated": false,
  "wfpProvider": "REGISTERED",
  "tcpipProvider": "REGISTERED",
  "dnsProvider": "REGISTERED",
  "kernelNetworkProvider": "REGISTERED",
  "wfpChannel": "ENABLED",
  "dnsChannel": "DISABLED",
  "pktmonExecutable": true,
  "netEventReadCmdlet": true,
  "packetCaptureStarted": false,
  "osPacketDenyProven": false,
  "reason": "NO_ACTIVE_INDEPENDENT_PACKET_OBSERVER"
}
```

**Crucial interpretation:** WFP/Kernel-Network/TCPIP/DNS
providers being *registered* and WFP Operational *enabled*
is not evidence that any app-scoped packet was captured,
blocked or attributed. DNS Operational is *disabled*, not a
DNS-denial measurement. An installed `pktmon.exe` and
`Get-NetEventSession` is only tooling presence, not
authorization to start a privileged session. The previous
T1 `sdkVersion=UNAVAILABLE` represented missing package-lock
metadata only and must not be inferred to mean ETW providers
are absent or that an OS observer is ready.

## Next real G3–G7 acceptance requirements, held

1. Get **owner-approved** app-scoped contained-source/policy
   architecture and an approved independent disposable
   Windows guest/observer, with documented non-admin vs
   privileged boundaries and review permissions. This
   metadata feasibility test does not authorize capture.
2. Independently observe positive control traffic **and**
   blocked negative attempts across cold start, UIA IPC
   journeys, shutdown/restart, Windows browser/broker
   descendants, DNS, IPv4/IPv6 TCP/UDP and shared services.
   Attribute to actual process/policy/host packet events
   and prove replay identity before claiming any zero-egress.
3. Keep previously observed WebView2 external TCP, MXC
   `captureDenials E_NOTIMPL`, and UDP
   `send_to=SENT23` ambiguity visible in
   [open security issue #662](https://github.com/AbdulazizShehri/MedOrigin/issues/662).
   No source, UIA or localhost positive result clears them.
4. Independent human security review #603, owner release/
   ADR/version approval #574, optional research dependency
   concerns #622 and Linux/macOS qualification remain.

**Decision: D1 passive OS metadata T1 feasibility PASS only.
G3 BLOCKED; G4/G5 NOT RUN; G7 BLOCKED; network-isolation,
clinical use, protected-main integration and release NO-GO.
`publication_authorized=false`.**

No global firewall change, WFP trace/capture start,
installer, registry upload, PHI, clinical claim, tag,
public package or merge was performed.
