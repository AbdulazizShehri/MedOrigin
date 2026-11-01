# Windows D1 MXC synthetic TCP OS-error qualification — 2026-11-01

**Status: nonpublishing engineering evidence, NOT release or network-zero-egress clearance.** Parent Draft PR #797 immutable source `ea5eb93e4aed2d3ba822a3915411043689fce305`. Only fictional local probes, no PHI/EHR, Internet target, DNS query or OS policy change.

## Test-first source finding

The pre-existing loopback differential harness accepted the generic `D1_TCP_CONNECT_DENIED_OR_FAILED` string for **any** TCP error, so a refused connection or timeout could satisfy the check even without an OS access-denied code. On the unmodified parent, a new source regression was **RED (2 pass, 1 fail)** because `raw_os_error()` and the required `D1_TCP_WSAEACCES_10013` proof were absent.

The test-only native Rust probe now emits the distinct marker **only** when `TcpStream::connect_timeout` returns raw Windows socket error **10013 (WSAEACCES)**; other failures emit `D1_TCP_OTHER_ERROR_NOT_OS_DENIAL`. The source-controlled MXC harness requires the exact 10013 marker for both IPv4 and IPv6 loopback cases, in addition to its existing same-binary host-positive controls, zero listener deliveries, SDK warning checks and no network-capability policy.

## Actual authorized Windows evidence

On the authorized Windows 11 x64 device `ABDULAZIZ`, Rust **1.97.1**, task-local Node **24.21.0** (the globally installed 24.19.0 correctly failed the existing Node admission gate), Microsoft MXC SDK **1.0.1**, same pinned standalone Rust probe SHA-256:

`850334d094364404426db662716769f9d1f926211c78c32d8b157b7ece87d66b`

- IPv4 `127.0.0.1`: uncontained host-positive **TCP 1 delivery, UDP 1 delivery**; MXC explicit egress/ingress deny, `D1_TCP_WSAEACCES_10013`, **TCP 0 deliveries, UDP 0 deliveries**, exit 0, no SDK warnings.
- IPv6 `::1`: uncontained host-positive **TCP 1 delivery, UDP 1 delivery**; same MXC deny, `D1_TCP_WSAEACCES_10013`, **TCP 0 deliveries, UDP 0 deliveries**, exit 0, no SDK warnings.
- After fix, Node source contract **3/3 PASS**, `rustc --edition 2024 -D warnings` PASS, native differential PASS both address families, `git diff --check` PASS.

**Important UDP nuance:** the contained probe printed `D1_UDP_SEND_RETURNED` even though neither host listener received a datagram. Successful `send_to` is **not** proof of UDP delivery or of packet-level denial. TCP WSAEACCES is a bounded OS error observation, **not** independently audited WFP rule/packet attribution.

This is a **standalone synthetic helper**, not the actual Tauri/WebView2 D1 product process or descendants. It does **not** establish IPv4/IPv6 external egress denial, DNS/proxy/service paths, UDP packet filtering, process-tree lifecycle containment, independent security approval or owner release authority. Issue #662 remains **OPEN / NO-GO**. No release, installer, tag, protected-main merge, frozen research dependency edits or publishing.
