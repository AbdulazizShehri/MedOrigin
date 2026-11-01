# MedOrigin D1: hostLoopback AppContainer capability bypass — RED/GREEN

**2026-11-01 · Synthetic-only, nonpublishing, zero-cost. RELEASE NO-GO.**
This note records a real Windows native security regression and its
narrowly scoped correction. No patient/clinical payloads, packet transmission,
firewall/audit edits, installer, tag, release, or protected-main merge.

## Found: AppContainer + three network SID checks could allow host loopback

Previously the D1 pre-Tauri Rust guard required `TokenIsAppContainer` and
denied `internetClient`, `internetClientServer`, and
`privateNetworkClientServer` SIDs from the process primary token.
Authentic MXC ProcessContainer allowed these independent policy axes:

| Native MXC policy | Old gate result | Intended admission |
| --- | --- | --- |
| egress deny, ingress deny, hostLoopback deny | exit 0 / admit | admit |
| egress allow, ingress deny, hostLoopback deny | exit 76 / refuse | refuse |
| egress deny, ingress allow, hostLoopback deny | exit 76 / refuse | refuse |
| egress allow, ingress allow, hostLoopback deny | exit 76 / refuse | refuse |
| **egress deny, ingress deny, hostLoopback allow** | **exit 0 / admit — SECURITY RED** | **refuse** |

The fifth case was an actual native ProcessContainer execution with the
**same compiled, SHA-256 pinned original Rust runtime helper**:
`ccc905a68f6bb4ed071718fa2302086485e4458da6a59c6b1dedf9c05d7062e9`.
The temporary five-case test correctly reported exit 1 because the
hostLoopback-allow container unexpectedly passed the token gate.
No socket or DNS request was sent by this token probe.

The read-only Windows `TokenCapabilities=30` control compared the same
native SID-reporting executable in both configurations:

| Token observation | hostLoopback deny | hostLoopback allow |
| --- | --- | --- |
| AppContainer | 1 | 1 |
| capability count | 1 | **2** |
| three-known-network-SID mask | 0 | **0** |

The additional SID in the hostLoopback-allow primary token was
`S-1-15-3-1024-820624432-2503302554-1536879699-4049119443-112573677-3799174643-950279649-4267032225`.
The eight generated RID values match SHA-256 of the **uppercased UTF-16LE**
name `NETWORKLOOPBACK`, according to the documented Windows derivation
for hash-based application capability SIDs. The ordinary deny-all MXC
contained a different unchanged non-network capability; requiring **zero
total capabilities** would therefore incorrectly reject the approved
GUI sandbox. This extra SID comparison is specific to this tested MXC
backend/policy; it is not independent signing or network attestation.

## Correction

- Extended `windows-token-gate/src/lib.rs` to compare each token
  capability via Windows `EqualSid` against the additional
  `networkLoopback` SID, using a fixed, C-layout, ten-subauthority
  SID representation. This blocks the host-loopback-only bypass **before
  Tauri/WebView2 startup**, with no environment-variable override or new
  third-party Rust dependencies.
- Existing `reject_network_capability_bits` now receives bit 3 for
  `networkLoopback`, in addition to bits 0–2 for Internet/private SIDs.
  Its Rust unit test rejects **all nonzero combinations 1–15**, while
  the normal zero mask remains admissible.
- `windows-d1-appcontainer-startup-source.test.mjs` asserts the
  named SID, its hashed RID values, `EqualSid` comparison and failure.
- `windows-mxc-d1-native-token-policy-differential.mjs` now
  checks **five** native network-policy cases with the exact same
  SHA-pinned security-helper executable. A separately covered direct,
  ordinary uncontained Windows process must also fail with exit 76.
- The private original baseline source/compiled files were kept only
  temporarily for the diagnostic. No global network policy was changed.

## Actual GREEN after source correction

Compiled `tests/windows-mxc-d1-native-token-policy-probe.rs` using
`rustc --edition 2024 -Dwarnings`; its imported helper is the
**same source** used by the D1 application. New probe SHA-256 before
the final rustfmt-only normalization:

`1e8a3f4e0eeff5dbb08d07e4e6dba52fcad412a0d164a9b0f55df8673a6ca88f`

Same executable, supported Windows Node v24.22.1, locally cached
MXC SDK1.0.1, and actual ProcessContainer:

| Admission control | New gate |
| --- | --- |
| Direct ordinary Windows host | refuse / 76 |
| Egress deny, ingress deny, hostLoopback deny | **admit / 0** |
| Egress allow, ingress deny | refuse / 76 |
| Egress deny, ingress allow | refuse / 76 |
| Egress allow, ingress allow | refuse / 76 |
| Egress deny, ingress deny, **hostLoopback allow** | **refuse / 76** |

Full real native five-policy differential returned exit **0** and
`D1_EXACT_RUNTIME_TOKEN_GATE_FIVE_POLICY_MATRIX_PASS_NO_WFP_ATTESTATION`.
No MXC enforcement warnings, no network traffic or DNS requests.
Two Node source-contract tests PASSED on Windows, two Rust token-gate
unit tests PASSED, five startup source contracts PASSED, and
`rustfmt --check` subsequently passed on the exact formatted helper.
[Windows 2025 source CI #41309415377](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41309415377)
completed **SUCCESS** with all steps checked; hosted CI does **not**
exercise native MXC or record packet denials.

A full official Tauri build and source-built GUI/UIAutomation qualification
are tracked as separate subsequent evidence; no such claim follows merely
from the helper differential.

## Explicit remaining release-security blockers

The token check protects **these named capability SID classes** on
the tested process. It does not cryptographically authenticate an MXC
backend or its exact policy, prove that a maliciously launched
AppContainer with custom or brokered network access is prevented,
establish OS/WFP packet-level TCP/UDP/IPv4/IPv6/DNS denial, or cover
Edge/WebView2 service/broker access or full install/upgrade/restart
lifecycle. Prior external WebView2 egress observations and #662
remain unresolved. The small Win32 FFI helper still requires
independent review; the host is non-admin and cannot provide WFP
Security event auditing without separately authorized elevation.

Keep #662 and #603 open, Draft PR #797 unmerged, and **NO-GO**
for publishing, PHI, real patient data, installer and clinical use.
