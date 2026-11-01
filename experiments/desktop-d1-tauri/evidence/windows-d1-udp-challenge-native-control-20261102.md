# D1 native local UDP challenge receipt hardening — 2026-11-02 (NO RELEASE)

Repository: `AbdulazizShehri/MedOrigin`. Draft stack parent PR #819 exact
`a22a8cfa15336ae312ea9771c2fe42abb4951140`. This change is entirely
**test-only** and does not alter Tauri/WebView2 product, MXC policy, OS firewall,
Python research roots, packaging, or protected main.

## Finding and test-first proof

The previous positive-control Rust probe sent the same fixed 23-byte
`synthetic-mxc-udp-probe` payload to localhost for every run. Its Node verifier
checked family, source address, size, count and fixed bytes, but never correlated
UDP4/UDP6 datagrams to a **fresh invocation**. A replayed or unrelated local
datagram could be misattributed even while a separate child stdout said SENT23.

- RED `1c057d465fc32f687ef4bc3cf9877b6fd2d16acd`: new adversarial test
  module added before verifier/runner changes. Actual Windows TAP: 14 tests,
  12 pass, **2 intentional fail** (fresh nonce positive case and missing source
  wiring), exit 1.
- RED `e0fd3949c8365c3a2e21fdc414c7376f761bee15`: adds explicit legacy
  *two-family static packet replay* fixture. Actual Windows TAP: 15 tests,
  12 pass, **3 intentional fail**; crucially old verifier accepted both legacy
  UDP packets despite supplied fresh expected nonces. Exit 1.
- GREEN code `c20e2d140d3c03ce82df7c5ceb6e06df8b3b3cf8`: four distinct
  random 128-bit lowercase hex challenges (TCP4, TCP6, UDP4, UDP6), passed
  only to the unrestricted Rust control. UDP payload remains exactly 23 bytes:
  ASCII `mxcudp:` (7) + 16 raw nonce bytes. Rust denied mode retains its
  previous 23-byte synthetic payload and unchanged fail-closed WSA10013
  interpretation. The Node verifier rejects missing, stale, static, swapped,
  duplicated, truncated, extra, malformed or cross-family UDP proof.
- Actual authorized Windows Node v24.19.0 / rustc v1.97.1: scoped **134/134
  PASS**, zero skip/fail, Rust `--emit=metadata` and `rustfmt --check` PASS,
  `git diff --check` PASS. Source code SHA is the code commit above.
- Actual native **unrestricted localhost only** control on same source:
  compiled Rust probe SHA-256
  `0356b8adab9c2bbb0cf75c2094afb58ad42f573130eab784b750f3f18749d6ee`.
  One actual accepted TCP4 and TCP6 challenge proof each and one UDP4/UDP6
  fresh challenge payload each. Native script exit 0, no residual test process
  reported. Only 127.0.0.1 and ::1; no remote or MXC denied-mode test.
- A separate *broader* 205-test glob had 204 PASS / 1 FAIL in
  `windows-mxc-d1-real-app-contract.test.mjs` concerning a distinct UIA
  PowerShell string expectation; **not** represented as a clean full suite.
  The targeted source-bound security contract is the eight-file 134-test suite.

## Security and release limits

This proves local *positive-control receipt freshness*, not process
authentication: nonce arguments are visible in the local child command line.
It does **not** prove Windows MXC denied UDP, WFP/ETW packet-level enforcement,
DNS, IPv4/IPv6 remote TCP/UDP, WebView2 transient descendants, brokers,
proxies or shared services. Prior native MXC captureDenials `E_NOTIMPL`
and UDP `SENT23` ambiguity remain unresolved. Issue #662 remains OPEN;
G3 BLOCKED, G4/G5 NOT_RUN, G7 BLOCKED. Human independent security review
#603, owner authority #574, optional research extras #622, Linux RustSec
#673 and spoken VoiceOver #676 remain separate NO-GO gates.

All evidence synthetic, no PHI, clinical claims, privileged capture,
global firewall, release, tag, installer, registry upload, main merge or
publication. `publication_authorized=false`.
