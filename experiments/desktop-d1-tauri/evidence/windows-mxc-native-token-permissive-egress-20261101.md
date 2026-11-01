# MedOrigin D1 — native MXC permissive-network policy rejection differential

**Date:** 2026-11-01. **NONPUBLISHING / SYNTHETIC ONLY / NO PHI / NO RELEASE.**

## Purpose

The previous exact-source native Windows D1 preview build refused ordinary
unsandboxed startup and accepted a genuine MXC ProcessContainer with
default-deny network ingress/egress. The isolated Rust primary-token helper
also rejected all combinations of the three well-known Windows network
capability SIDs in **unit tests**. That alone did not demonstrate that the
same helper could distinguish **two real, otherwise valid AppContainer
processes configured with different MXC network permissions**.

This qualification closes that narrower negative-test gap. It does **not**
establish OS/WFP packet-level isolation, clinical or release readiness.

## Source and execution controls

- Added `tests/windows-mxc-d1-native-token-policy-probe.rs`, which
  **imports the exact original production helper** from
  `../windows-token-gate/src/lib.rs`. The probe does not reimplement
  `GetTokenInformation`, SID matching, or gate logic. It accepts no
  user content and creates **zero sockets, DNS queries or external requests**.
  It returns 0 only if
  `require_windows_appcontainer_primary_token()` succeeds, and exits
  76 on rejection with the helper's reason.
- `tests/windows-mxc-d1-native-token-policy-differential.mjs` refuses to
  run on an unsupported Windows/Node environment, requires a user-supplied
  exact SHA-256 match for the compiled probe, requires native MXC
  ProcessContainer support without isolation warnings, and runs the
  **same pinned probe** under three different process identities.
  All contained processes have finite 14-second timeout, read-only
  executable and isolated writable scratch.
- The test differentiates `network.egress.default='deny'` from
  `network.egress.default='allow'`. Both use
  `network.ingress.default='deny'` and
  `hostLoopback='deny'`. It **does not send packets** under either.
- The intentionally permissive case must exit **76** with
  `primary_token_has_network_capability`. Successful execution or
  absence of that rejection is a test **NO-GO**. The deny-all case must
  exit **0** with the original helper's success marker. Both require
  empty SDK warnings and no timeout.
- `tests/windows-mxc-d1-native-token-policy-source.test.mjs`
  preserves the exact-runtime source import, denies accidental
  duplicated/ad-hoc token logic, verifies host and permissive-container
  negative conditions, SHA pinning, and no network calls.
  The Windows source CI additionally performs a metadata compilation of
  the native Rust probe and source-only JavaScript tests; it does **not**
  exercise native MXC.

## Actual authorized Windows results

- Existing supported local Node `v24.22.1`,
  `@microsoft/mxc-sdk@1.0.1` installed using the existing offline npm
  cache in a dedicated disposable D: QA folder.
- `rustc --edition 2024 -Dwarnings` compiled the same production-helper
  linked probe without external crates. Native EXE SHA-256:
  `109729dc33d22d2488f26d8ebb074d9b51f9722bc7cb9159c133a2ed8744de28`.
- Ordinary Windows direct launch: **REJECTED**, exit **76**,
  `primary_token_not_appcontainer`.
- Native MXC ProcessContainer with **egress DENY, ingress DENY**:
  **ACCEPTED**, exit **0**, expected marker, no SDK warnings.
- Native MXC ProcessContainer with **egress ALLOW, ingress DENY**:
  **REJECTED**, exit **76**, reason
  `primary_token_has_network_capability`, no SDK warnings.
- End-to-end differential runner: exit **0**, marker
  `D1_EXACT_RUNTIME_TOKEN_GATE_DENY_ALLOW_DIFFERENTIAL_PASS_NO_WFP_ATTESTATION`.
- Windows local source contracts: **2/2 PASS**, 0 failures or skips.
- GitHub Actions workflow
  `.github/workflows/desktop-d1-mxc-endpoint-negative-source.yml` now
  runs these source contracts and native Rust probe compile. Exact-head
  hosted CI status is checked separately; do not confuse hosted CI
  source testing with the native MXC run above.

An initial PowerShell wrapper attempt used `ErrorActionPreference=Stop`,
which treated the **expected** native rejection stderr as a terminating
PowerShell error before checking exit 76. Retesting with captured stderr
and the expected status demonstrated the true result. This wrapper
issue did not change the Rust helper or sandbox policy.

## Residual risks / release NO-GO

This is an **active negative control of the actual helper logic**
under two native MXC AppContainer network configurations, strengthening
confidence in the source-built D1 startup guard. It does not bind
an immutable signed D1 binary to an authenticated MXC instance,
demonstrate prohibition of network egress by OS packet audit, measure
DNS/IPv4/IPv6/UDP leaks, rule out OS/Edge/WebView2 brokers or
network-capability equivalents, or test all application lifecycle
transitions. The previously qualified D1 GUI binary itself was **not**
recompiled or run in this particular differential: the test compiles and
executes the **exact shared Rust gate** as a standalone probe.

Keep issue #662 open and the release decision **NO-GO**. Independent
WFP/packet-level/network-proxy lifecycle and trusted-signing reviews,
dependency governance and owner authorization remain necessary. No
protected-main merge, installer, public release, PHI, clinical data,
global firewall/security modifications or paid services were involved.
