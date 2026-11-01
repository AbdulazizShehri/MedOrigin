# MedOrigin D1 — Native MXC vs host synthetic loopback TCP/UDP differential

Date: **2026-11-01**. **NONPUBLISHING / synthetic only / no PHI / no release.**
This is experimental evidence for issue #662, **not** complete Windows WFP
packet-denial evidence, application product isolation or DNS attestation.

## Intent and method

The existing 12-sample real WebView2 socket observer establishes only
**absence of observed endpoints at sample instants**, which can miss real
network packets. To add an independent *active network-denial attempt*,
a standalone Rust executable was compiled from
`tests/windows-mxc-synthetic-local-socket-probe.rs` with the existing
Windows Rust toolchain (no external Rust crates).

The binary requires a strict loopback-only IP address, two ephemeral
local TCP/UDP ports, and the fixed `D1_SYNTHETIC_NO_PHI` token.
It rejects any non-loopback IP input. It makes one TCP connect attempt,
writes only the fictional TCP marker if connected, and sends one fictional
UDP marker from a local ephemeral socket. No user files, PHI, actual
patient/EHR payload, DNS lookup, or remote Internet endpoint is involved.

The host-side
`tests/windows-mxc-synthetic-local-socket-differential.mjs`:
1. Creates TCP and UDP listeners on the **same loopback family** with
   OS-selected ephemeral ports.
2. Executes the **same SHA-256-pinned compiled Rust binary** on the ordinary
   authorized Windows host. It refuses to continue unless both listeners
   observed the positive control and the native probe reports TCP connected
   and UDP send successful.
3. Resets TCP/UDP arrival counters, runs the identical native binary
   under the native MXC SDK `processcontainer` with
   `network.egress.default='deny'`,
   `network.ingress.default='deny'` and
   `network.ingress.hostLoopback='deny'`.
4. Requires a real, successful, warning-free contained process execution,
   the expected probe start/finish markers, TCP connect failure, and **zero
   observed host listener arrivals** on both protocols. It refuses silent
   process launch failure as a success.
5. Separately repeats the whole sequence for IPv4 `127.0.0.1` and
   IPv6 `::1`. Inability to establish the host positive control is
   **NO-GO**, not an automatic skip.

## Actual authorized Windows results

- Native Windows Node `v24.22.1` satisfying MXC platform gate;
  `@microsoft/mxc-sdk@1.0.1` installed offline from the existing local
  npm cache into a dedicated temporary QA directory.
- Rust source compiled by `rustc --edition 2024`, Windows synthetic
  executable SHA-256
  `796db2f3aeb6eaac2cfb7ef46c7f7b461fd492c94514bb6e26630d4c5baebbbc`,
  182,272 bytes. Hash was computed after compilation, then passed to the
  host differential harness and verified before execution.
- A prerequisite MXC child-launch test using the existing Node portable exe
  was **inconclusive**: process exited with Windows native status
  `0xC0000142` (DLL initialization failure) and no start marker.
  This was not treated as a networking denial. A separate contained
  `cmd.exe` marker proved the MXC launcher itself worked; hence the
  standalone Rust native executable was used for the actual comparison.
- **IPv4 positive control:** host TCP listener observed 1 connection,
  UDP listener 1 packet. Identical contained executable reported probe
  start/finish, TCP connect failed, UDP `send_to` returned success but
  **host listener received zero TCP and zero UDP events**, MXC exit
  **0**, `timedOut=false`, `warnings=[]`.
- **IPv6 positive control:** host TCP listener observed 1 connection,
  UDP listener 1 packet. Identical contained executable reported the
  same TCP refusal and UDP send return, with **zero host TCP/UDP listener
  arrivals**, MXC exit **0**, `timedOut=false`, `warnings=[]`.
- Full differential Node harness returned **exit 0** and marker
  `D1_MXC_IPV4_IPV6_TCP_UDP_LOCAL_DIFFERENTIAL_PASS_NO_PACKET_OR_DNS_PROOF`.
- Two independent source-only Node tests also passed locally (**2/2**) to
  protect loopback-only targets, fixed fictional payloads, matching host
  and MXC executable, strict runtime admission and denied policy.
- Windows CI validates the Rust probe syntax/metadata build and the
  source-only differential contracts. Hosted CI does **not** execute
  native MXC, a packet capture or a DNS request. Always review the
  exact-head hosted run result before claiming green CI.

## Scope and remaining blockers

This is **differential evidence of the specified sandbox denying
connections to local synthetic listeners in two IP families**. In the
contained run the UDP userspace send returned; server non-arrival is the
observable result, not an audited blocked packet count. Host-local listener
non-arrival does not establish denial of real public IP packets, DNS
resolution, QUIC, broker/system-service egress or very short-lived traffic
outside the test scenario. None of these tests assesses a general-purpose
MedOrigin release or its unsigned, unapproved standalone runtime.

An independent qualified Windows environment with application-scoped
OS/WFP enforcement and trusted packet/DNS/UDP/IPv4/IPv6 negative proof,
WebView2 subprocess lifecycle coverage and a separate security review
remain necessary before closing #662. This additional evidence **must not**
be rephrased as universal network confinement, user-PHI approval,
public release, installer, protected-main merge or clinical deployment.
