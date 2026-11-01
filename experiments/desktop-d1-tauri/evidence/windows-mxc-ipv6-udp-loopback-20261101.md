# Nonpublishing MXC native IPv4/IPv6 TCP and UDP loopback differential — 2026-11-01

Source parent: Draft #760 at immutable commit `72a3d79e2548cb76279c918b5ad156707a9aafad`. All targets are fictional, local-only ephemeral listeners on `127.0.0.1` or `::1`, except the existing RFC5737 TEST-NET-2 TCP connect attempt. No PHI, clinical use, release, installer, registry, global firewall changes or packet capture.

Authorized Windows 11 Home 26H2 build `26300.9818`, Node `v24.19.0`, Rust `1.97.1`, Microsoft MXC SDK `1.0.1`. Same source-built WinSock Rust executable runs unconfined and in MXC ProcessContainer with explicit `network.egress.default=deny`, `ingress.default=deny`, `hostLoopback=deny`, no network capabilities and no GUI.

## Actual test-first and real native result

- RED on parent: new source contracts fail 2/2 because IPv6 TCP and UDP4/UDP6 were not exercised. Added Rust and Node test-only source, retaining existing IPv4 TCP and RFC5737 tests.
- Same-binary unconfined control: IPv4 and IPv6 loopback TCP `CONNECTED`; UDP4 and UDP6 `SENT` **and both independent host UDP listeners actually received datagrams**. The positive controls validate host routing and receiver readiness.
- Initial strict WSAEACCES-for-UDP assumption failed on the actual Windows MXC kernel boundary. Contained process output: IPv4 TCP loopback `WSA10013`, TEST-NET-2 TCP `WSA10013`, IPv6 TCP loopback `WSA10013`, but both UDP sends reported `SENT`. This failure was not treated as a denial proof.
- Corrected differential acceptance measures independent host UDP delivery after the same contained executable exits. **UDP4 delivered 0 and UDP6 delivered 0** over the bounded 800ms receiver window, despite both send calls returning `SENT`. MXC reported no warnings; child exit 0. Source-only Node contract tests 7/7 passed; pinned Rust formatter, Node syntax and diff checks passed.
- Source marker: `D1_MXC_NATIVE_PROCESSCONTAINER_TCP_IPV4_IPV6_WSAEACCES_UDP_LOOPBACK_NO_DELIVERY_OBSERVED_NOT_PACKET_PROOF`.

## Explicit NO-GO limits

This is **bounded localhost-only non-delivery observation**, not packet/WFP proof, and not evidence that UDP `send_to` was rejected. The Windows API returned `SENT` for both contained UDP attempts. A packet filter can drop datagrams after the send call returns successfully; this test does not establish which layer dropped them. It does not cover external IPv6/UDP destinations, DNS, proxy/broker/service traffic, short-lived children, packet traces or the actual Tauri/WebView2 product process. Windows D1 #662 remains **OPEN/NO-GO**. It does not grant independent #603 security review, #574 owner policy approval or release authority.

Hosted GitHub Actions, if green, validate source/compilation/static tests only and **never run this real MXC runtime**.
