# Windows D1 MXC supported-Node runtime qualification — 2026-10-31

**Nonpublishing / synthetic-only / not network-isolation qualified / no PHI.**
This record extends the exact source of Draft #784 at parent
`1abb52838dc99e62f6be7a6415f0982e90c52917`. The only new
behavior is a fail-closed test-harness runtime gate; no Tauri/WebView2
product code, OS firewall, MXC network allowlist or release path changes.

## Reproducible inputs

- Authorized interactive Windows 11 x64, kernel 10.0.26300.0, non-admin.
- Microsoft MXC SDK 1.0.1, native ProcessContainer, offline npm cache.
- **Node v24.21.0** portable ZIP from the official Node distribution,
  SHA-256 `158f7685b44de51f6c0df1d153526cbcd3e1bc739a8dfc607721cef75de9e541`,
  checked against the official `SHASUMS256.txt`; no system Node install.
- Existing **unpublished** source-qualified D1 synthetic debug executable,
  SHA-256 `7eceea367a05ce60576d633ff48f593d8dbff9ed2a56ff227d37c2280759b74a`.
  This is an older binary, **not rebuilt from this observer PR**.
- Explicit MXC ProcessContainer network egress default deny, ingress
  default deny, hostLoopback deny, interactive UI container isolation.
- Local source contract RED before implementation: missing Node gate module.
  GREEN: 15/15 Node version and integration checks; unsupported local
  Node 24.19.0 rejected before native SDK import, exit 1.

## Real supported-runtime result

```text
QUAL_NODE=v24.21.0
D1_MXC_REAL_UIA_RESULT 0
MXC_D1_UIA_PASS patient-minimal
MXC_D1_UIA_PASS patient-invalid-utf8
MXC_D1_UIA_PASS patient-over-limit
MXC_D1_UIA_PASS patient-exact-limit
MXC_D1_PROCESS_TREE=8 WEBVIEW2=6 OWNED_TCP=0 NONLOOP_TCP=0 UDP_ENDPOINTS=0
MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12 max_owned_tcp=0 max_udp_endpoints=0 NO_PACKET_LEVEL_ATTESTATION
D1_MXC_REAL_APP_RESULT {"exitCode":-1,"timedOut":true,"warnings":[]}
D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO
```

This removes the earlier **unsupported Node 24.19.0** caveat for this
one real interactive MXC run. It does **not** demonstrate OS-kernel
packet-denial telemetry, DNS/UDP/IPv6 denial, external traffic absence,
all WebView2 update/restart lifecycles, or independently approved
security. Snapshot polling may miss short-lived flows. Existing
`captureDenials` `E_NOTIMPL` and historical external WebView2 TCP
observations remain unresolved. **Issue #662 remains OPEN / NO-GO**,
as do #574, #603, #622, #673 and #676. No publication, merge, installer,
tag, registry upload, clinical claim or patient data.
