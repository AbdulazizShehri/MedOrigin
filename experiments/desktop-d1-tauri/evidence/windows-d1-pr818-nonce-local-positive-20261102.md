# Windows D1 synthetic TCP nonce control qualification — 2026-11-02

**NONPUBLISHING / NO-GO.** Repository: `AbdulazizShehri/MedOrigin`.
Parent Draft PR #817 immutable source `5a4c5d276353f049404421095578a3a802b2368c`.
Code commit: `77e416b15ccfd041eaef15a2d9e1c7b90ce28d8e` (Draft PR #818).
Only seven experimental test/contract/read-only CI paths changed relative to #817.

## Actual defect and test-first evidence

The preceding positive-control listener counted real TCP accepts and validated
local peer metadata but could not distinguish an incidental same-host TCP client
from the launched Rust control. A new synthetic adversarial test first returned
**RED exit 1** on actual Windows/Node 24.19.0 because the fail-closed
`assessTcpNonceBinding` export was missing. No pre-fix GREEN was claimed.

The correction adds distinct per-run 32-byte random values encoded as 64 ASCII
hex bytes, two distinct 32-byte server challenges, and exact 96-byte TCP
nonce/challenge replies for IPv4 and IPv6. The Rust probe reads each challenge
and writes the matching nonce and challenge on its **unrestricted control**
connection. The host rejects wrong, missing, duplicated, incomplete, malformed,
oversized, errored, reused or stale evidence. The runner must use asynchronous
`execFile` so Node can serve challenges while the Rust process is alive.
The same source-built Rust binary still supports the unchanged denied-mode
eight-socket test path; **denied-mode MXC was not executed in this qualification**.

## Source-bound Windows evidence

- Actual authorized Windows build `10.0.26300`, Node `v24.19.0`,
  Rust `1.97.1`. Synthetic fixtures and `127.0.0.1` / `::1` only.
- After code commit, checked local HEAD and GitHub remote head both exactly
  `77e416b15ccfd041eaef15a2d9e1c7b90ce28d8e`.
- **121/121 source tests PASS**, 0 fail / 0 skipped; 22 new nonce tests.
  Pinned Rustfmt, Node syntax and git diff --check PASS.
- Real source-built **unrestricted localhost-only** Rust probe runner exit 0.
  Exactly one IPv4 and one IPv6 accepted TCP connection with correct local
  peer metadata and per-run nonce/challenge replies; exactly one expected
  23-byte UDP payload received on each local family.
- Actual compiled native EXE SHA-256 for the post-commit run:
  `21c2a2aaa5bc856a3d5796f87c270f13f5cb243861b16b563eb813348d01c332`.
  A preceding same-source local run produced
  `302f0bbc34d7ff6b8bc91fbbf731d46510c667c6438fe73536e3c12f539a1ddb`;
  ephemeral build-path differences mean these bytes are **not claimed
  reproducible**. Both native local runs exited 0.
- GitHub Actions exact-code-head [Windows PR run #41354165015](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41354165015)
  **COMPLETED SUCCESS, 1/1 job** at the code commit above. Raw job logs
  confirm **121 PASS / 0 FAIL / 0 SKIP** and pinned Rust 1.97.1 formatting
  and metadata-only compile. Hosted CI does **not** execute native sockets.
- No native EXE, secrets, patient data, network capture or local scratch
  is uploaded to the repository. The nonce and challenge values are not logged.

## Hard limits

This is a bounded synthetic **positive-control receipt**, not independent
process authentication: the nonce is visible in the child command line to
other local processes. It is not an OS-enforced network deny or independent
security attestation. It does not test MXC denied-mode, actual D1 WebView2
descendants, shared brokers, WFP/ETW, DNS, IPv4/IPv6 external packet delivery,
UDP upstream loss, or privileged observers. Historical `captureDenials
E_NOTIMPL` and MXC UDP `SENT23` ambiguity remain unresolved.

**Issue #662 OPEN / NO-GO; G3 BLOCKED, G4/G5 NOT_RUN.**
Independent release security #603, owner authority #574, frozen optional
research dependencies #622, Linux RustSec #673 and VoiceOver #676 remain
unqualified. No protected-main merge, release, tag, installer, publication,
global host firewall change, PHI or clinical claim is authorized.
