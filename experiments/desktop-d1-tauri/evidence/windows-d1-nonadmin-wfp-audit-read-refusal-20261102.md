# Windows D1 T1: actual nonadmin WFP audit settings read — privilege denied

**2026-11-02 Asia/Riyadh • source-bound author-side Windows run •
read-only, synthetic development only • security/release NO-GO.**

## Why this matters

[Draft #826](https://github.com/AbdulazizShehri/MedOrigin/pull/826)
proved that WFP/TCPIP/DNS/KernelNetwork ETW providers are **registered**
and WFP Operational channel metadata is **enabled** on the authorized
Windows 10.0.26300 non-admin PC, but this never established that OS
audit subcategories are enabled, accessible or capturing blocked traffic.

Microsoft's WFP auditing guidance documents the GUIDs
`{0CCE9226-69AE-11D9-BED3-505054503030}` for **Filtering Platform
Connection** (including event 5157) and
`{0CCE9225-69AE-11D9-BED3-505054503030}` for
**Filtering Platform Packet Drop** (including event 5152).
These audit events are in the Windows **Security** log, not inferred
from an enabled WFP Operational channel. No audit-policy mutation
is authorized in this work.

## Exact work / test-first evidence

- Stacked on **Draft #826 exact parent HEAD**
  `602809dfad3d96b6c5f1ee9a65e946c84f8418b3`.
  New test-only source code and read-only host query script.
- Actual authorized Windows non-admin test-first RED source
  `2a473a4e8f632212f35ba86ca521647c3e5a1a6d`
  lacked the new `.mjs` implementation:
  `ERR_MODULE_NOT_FOUND`, expected missing-module RED rather
  than proof of an active exploit.
- Initial implemented local source SHA
  `0f4ac4e125e1f74fece209a8362568f1677be047`:
  **45/45 Node tests PASS**, script exit 0, but report gave
  `OTHER_ERROR` because under PowerShell 5.1 the script's
  `ErrorActionPreference='Stop'` and native all-stream
  redirection masked the native `auditpol.exe` exit code.
  It was **not** misclassified as PASS.
- Independent direct, **read-only** `auditpol.exe /get
  /subcategory:{GUID} /r` on the same non-admin PC returned
  native **exit 1314** for each exact WFP GUID
  (`ERROR_PRIVILEGE_NOT_HELD`). A separate metadata-only
  `Get-WinEvent -ListLog Security` returned **inaccessible**.
  No native audit text, event messages or endpoint data saved.
- Corrected PowerShell script suppresses localized native
  output while preserving the exit code; distinguishes
  `PRIVILEGE_DENIED`, `READABLE_UNVERIFIED` and
  `OTHER_ERROR` explicitly, and **never** treats even
  readable audit settings as active packet evidence.
- Actual final tested source SHA
  `d5a80079f88358b8c5987e5f16e00c82138ccbe3`:
  **45/45 local Node tests PASS, 0 fail, 0 skip**, native
  read-only PowerShell/Node collector **exit 0**, clean
  exact Git SHA before and after, Windows 10.0.26300,
  non-admin. Exact sanitized result:

```json
{
  "schema":"D1_WFP_AUDIT_READ_VISIBILITY_V1",
  "sourceSha":"d5a80079f88358b8c5987e5f16e00c82138ccbe3",
  "status":"READ_ONLY_AUDIT_VISIBILITY",
  "osBuild":"10.0.26300",
  "elevated":false,
  "connectionAuditState":"PRIVILEGE_DENIED",
  "packetDropAuditState":"PRIVILEGE_DENIED",
  "securityLogMetadata":"ACCESS_DENIED",
  "wfpAuditPolicyAttested":false,
  "eventRecordsRead":false,
  "policyChanged":false,
  "osPacketDenyProven":false,
  "reason":"WFP_AUDIT_POLICY_NOT_INDEPENDENTLY_READABLE"
}
```

- [Hosted exact-code-head Windows source-only run
  #41364473343](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41364473343):
  **COMPLETED SUCCESS**, job raw logs inspected,
  **45 PASS, 0 FAIL, 0 SKIP**. The hosted tests use
  mocked native output. They are **not** packet or real
  host-observer proof.
- All actual local operations used an owned clean detached
  D: worktree. Permanent original Windows repo/source is
  preserved separately. No external IP, hostname, process
  name, Security event message, packet payload or PHI is
  in the sanitized receipt.

## Exact security limits / next authorized dependency

An installed ETW provider, enabled WFP Operational metadata,
and unavailable security audit-policy read together establish
**nonadmin visibility constraints**, not proof WFP denied any
TCP/UDP/DNS packet or attributed a WebView2 descendant/broker.
The error 1314 is about this specific process's **permission**
to read audit settings, not proof the system has auditing
disabled and not authorization to change audit policy.

The required next engineering work is an **owner-approved**
disposable Windows guest / independently operated OS
observer with narrowly scoped audit policy/elevation decision
and source-bound positive/negative packet evidence, covering
DNS, IPv4/IPv6 TCP/UDP, cold start, UIA and shutdown,
WebView2 descendant PID lifecycle and shared-service brokers.
Independent human security review is mandatory.

Historical WebView2 external TCP, native MXC
`captureDenials E_NOTIMPL` and UDP `send_to=SENT23`
remain unresolved in
[open issue #662](https://github.com/AbdulazizShehri/MedOrigin/issues/662).
**G3 BLOCKED; G4/G5 NOT RUN; G7 BLOCKED.**
Owner version/release #574, human security review #603,
unsafe canonical optional research extras #622,
Linux D2 zbus5 maintenance #673 and macOS spoken
VoiceOver #676 remain separate blockers.

No privileged action, auditpol setting modification,
Security event enumeration, ETW/pktmon session, firewall
rule change, installer, clinical use, PHI, protected-main
merge or publication. `publication_authorized=false`.
