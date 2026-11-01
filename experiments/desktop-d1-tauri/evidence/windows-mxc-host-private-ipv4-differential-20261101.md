# MedOrigin D1 — MXC private host-interface TCP/UDP differential (2026-11-01)

**Nonpublishing · synthetic-only · no PHI · issue #662 remains OPEN/NO-GO.**
This is a new *active differential network test* on the authorized Windows
machine, complementary to the earlier local-loopback denial and real D1
WebView2 UIA tests. It is **not** an Internet/WFP packet-denial attestation.

## Scope and source

- Source branch: `test/medorigin-d1-mxc-endpoint-negative-20261101`
  (stacked Draft PR #797). New standalone Rust probe:
  `tests/windows-mxc-synthetic-private-interface-probe.rs`, and matching
  `tests/windows-mxc-synthetic-private-interface-differential.mjs`.
- Exact native compiled probe SHA-256:
  `b67d48aac472d23a0a35efefcc9b336b952241238a694808e1c58506f5f31347`.
  Built with existing Rust toolchain. The same binary hash is verified
  before both the ordinary host and MXC ProcessContainer trials.
- Host harness picks only **actual local-interface-owned RFC1918 IPv4
  addresses** from `os.networkInterfaces()` with `internal=false`.
  Each selected interface is validated as private by explicit octet
  classification and must sustain genuine host-side TCP and UDP
  positive controls before the MXC trial is admitted.
- Native Rust probe also only accepts private, nonloopback IPv4 and a
  fixed `D1_SYNTHETIC_NO_PHI` token; input is a numeric IP address,
  so **no DNS lookup** is done. Each TCP/UDP payload is a fixed fictional
  marker. There is no real patient/EHR data or remote service.
- Host addresses were **not** written into evidence, logs, source,
  comments or GitHub. Only sequential candidate numbers and
  aggregate protocol counts were printed.
- MXC SDK: `@microsoft/mxc-sdk@1.0.1` from existing offline npm cache;
  runtime: supported local Node v24.22.1; native ProcessContainer with
  egress and ingress default deny and `hostLoopback='deny'`. No
  machine-wide firewall or audit configuration changed.

## Verified real Windows result

| Check | Host positive control | Same binary inside MXC |
| --- | --- | --- |
| Candidate 1, private IPv4 TCP | 1 incoming connection | connect failed, 0 arrivals |
| Candidate 1, private IPv4 UDP | 1 received datagram | 0 received datagrams |
| Candidate 2, private IPv4 TCP | 1 incoming connection | connect failed, 0 arrivals |
| Candidate 2, private IPv4 UDP | 1 received datagram | 0 received datagrams |

- Both contained processes returned `exitCode=0`,
  `timedOut=false`, `warnings=[]`; Rust start/finish markers and
  TCP denial marker were present.
- Overall real native differential returned
  `D1_MXC_PRIVATE_INTERFACE_DIFFERENTIAL_PASS candidates=2
  NO_DNS_NO_REMOTE_PACKET_ATTESTATION`; Node exit **0**.
- A second, local source-only test suite:
  `windows-mxc-synthetic-private-interface-source-contract.test.mjs`,
  **2/2 PASS**, validates private IP selection from host interfaces,
  SHA-pinned matching native probe, positive TCP and UDP controls,
  identical contained binary, deny-all request, zero listener
  observations and synthetic payload restrictions.
- Executed explicit negative input checks for `127.0.0.1`, `::1`,
  a documentation-only external IPv4 and a documentation-only
  external IPv6. Each received exit **2** with
  `D1_PRIVATE_INTERFACE_NONPRIVATE_REFUSED` (4/4).
  An initial PowerShell `ErrorActionPreference=Stop` test aborted on
  expected stderr before checking the exit code; rerunning with native
  stderr captured under `Continue` yielded the above four verified
  expected failures.
- GitHub Actions workflow `desktop-d1-mxc-endpoint-negative-source.yml`
  now runs Rust metadata compilation and both JavaScript source
  contracts on Windows 2025. Hosted CI **does not** run native MXC or
  network attempts. Exact-head result must be checked separately.
- The roughly 170 MB temporary QA folder, all compiled native
  binaries and offline npm test dependencies are disposable and should
  be removed after this report is committed.

## Interpretation and release boundary

This test supports the narrow finding that the native MXC
ProcessContainer configured with these deny rules blocked **connections
to TCP/UDP listeners on two actual local private IPv4 network
interfaces**, while the same executable reached them outside the
container. UDP `send_to` could return success even when no host
datagram was observed: receiver non-delivery is the evidence, not
kernel-level logged packet drop.

This does **NOT** prove that a distributed MedOrigin executable
always launches within MXC, that remote IPv4/IPv6 traffic cannot pass,
that DNS (OS resolver or service proxy), other networking protocols,
WebView2/Edge background services, brokered connections, or short
lifecycle windows are confined, or that WFP itself independently
logged packet denial. Only IPv4 RFC1918 local host interfaces were
eligible; **no ULA IPv6 host-owned address** was present, so this
test makes no private nonloopback IPv6 claim. Earlier local `::1`
tests are separate.

**#662 remains OPEN / release NO-GO**, pending a formally deployable
app-scoped isolation mechanism, trusted packet/DNS/TCP/UDP/IPv4/IPv6
negative evidence, full lifecycle verification, independent security
review and dependency governance. No main merge, publication, tag,
installer, PHI or clinical-use authorization follows from this test.
