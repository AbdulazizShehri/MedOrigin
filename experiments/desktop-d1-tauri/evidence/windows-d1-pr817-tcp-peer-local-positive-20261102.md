# D1 PR #817 — actual Windows TCP/UDP local-only positive control and fail-closed peer receipts

**2026-11-02 Asia/Riyadh • DRAFT • NONPUBLISHING • SYNTHETIC ONLY • NO PHI • RELEASE NO-GO.**

This report records a **real native, unrestricted localhost-only**
positive-control run of the Rust MXC protocol-matrix probe on the
authorized Windows desktop. It **does not** launch MXC, test denied
egress, observe independent WFP/ETW packets or qualify the D1
WebView2/Tauri application. Issue #662 remains **OPEN / NO-GO**.

## Precise source identity and source-driven bug

- Frozen code source: `f79d0a7131bd494c07b9fce01ba545c91536b97b`
  (this evidence-only commit follows that code SHA).
- Parent [Draft #815](https://github.com/AbdulazizShehri/MedOrigin/pull/815)
  at `18ddc448712e79f794878cb25e73b46c3634446f`.
- Original positive-control verifier accepted one `tcp4Accepts` and
  `tcp6Accepts` count even if those connections came from unknown
  addresses, wrong families or a different local listener port.
  Parent #815 already checked expected UDP bytes, but **did not
  check TCP peer/source identity**.
- Changed pure verifier
  `tests/windows-mxc-protocol-matrix-verdict.mjs` now requires exactly
  one TCP4 and TCP6 host-side peer object, canonical source/local
  `127.0.0.1` / `::1`, explicit `IPv4` / `IPv6`
  remote family, valid remote source port and exact local port
  matching the listener's real ephemeral port.
- The native experimental runner records real `s.remoteAddress`,
  `s.remoteFamily`, `s.remotePort`, `s.localAddress`,
  `s.localPort`, accepts and active listener ports. Existing
  positive-control fixtures were updated to match this contract.
- **Security limitation:** peer identity still does **not** prove the
  peer process is the exact Rust probe, cryptographically challenge
  its connection or establish OS packet denial. A separate nonce
  handshake would be needed to authenticate the caller in an
  adversarial local environment. This is a narrowly scoped
  source-evidence integrity improvement.

## Actual test-first RED → source GREEN

- Test-first source commit
  `0ffa634ead810b0194f401715ba8df3a08adbebc`
  on clean detached Windows worktree:
  **22 tests, 2 PASS / 20 FAIL**, the prior verifier wrongly
  accepted 19 intentionally malformed/absent TCP peer cases and
  the runner lacked required metadata wiring. This was confirmed
  by exact-source hosted
  [Windows RED run #41352973219](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41352973219):
  **99 total: 79 PASS / 20 FAIL**, expected fail-closed regression.
- Repaired pure verifier, native runner and inherited fixtures,
  with **no Tauri/Rust production app or OS policy changes**.
  [Windows GREEN run #41353078714](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41353078714)
  at source `76234a019dca6957f308dfb00d8781688720fdf1`:
  **99/99 PASS, 0 FAIL, 0 SKIP**; raw job log inspected.
- Repeated exact-source local test suite at
  `f79d0a7131bd494c07b9fce01ba545c91536b97b`:
  all **99/99 PASS**, 0 failures/skips; Node syntax check of
  new local-only runner PASS; Git source worktree clean.

## Real native positive-control execution (no MXC, no remote endpoints)

- Windows 11 Home version 10.0.26300, Node.js `v24.19.0`,
  Rust `rustc 1.97.1`; exact clean detached source checkout on D:.
- Executed new file
  `tests/windows-mxc-unconfined-loopback-qualification.mjs`
  with `MEDORIGIN_MXC_TEST_TMP=D:\`, so disposable Rust
  output stays on D: and is cleaned by the runner.
- It builds `windows-mxc-protocol-matrix-probe.rs` with the
  installed Rust toolchain, and runs its **control** mode only.
  Rust `control` mode exercises only `127.0.0.1` and `::1`.
  It does **not** attempt the reserved remote documentation
  addresses present in the separate `denied` mode.
- Verified the SHA-256 of the compiled probe before and after
  the native local run:
  `698a789f1386b8e5b9e0b7a06fcde390c7cedc1ca8680634f7aa562a1232097a`.
- The host's own TCP listener accepted **exactly one** connection
  each on `127.0.0.1` (IPv4) and `::1` (IPv6), with matching
  local ephemeral port and source metadata. Host-owned UDP
  listeners received **exactly one** canonical 23-byte synthetic
  datagram each on IPv4 and IPv6, with exact payload/source checks.
  The strict `assessNativePositiveControl` passed the real native
  results; runner exited **0**.

```text
RUN_EXACT_SOURCE=f79d0a7131bd494c07b9fce01ba545c91536b97b
D1_MXC_LOCAL_ONLY_UNRESTRICTED_TCP4_TCP6_UDP4_UDP6_CONTROL_PASS
D1_MXC_LOCAL_ONLY_PROBE_SHA256=698a789f1386b8e5b9e0b7a06fcde390c7cedc1ca8680634f7aa562a1232097a
D1_MXC_LOCAL_ONLY_TCP4_ACCEPTS=1
D1_MXC_LOCAL_ONLY_TCP6_ACCEPTS=1
D1_MXC_LOCAL_ONLY_UDP4_RECEIPTS=1
D1_MXC_LOCAL_ONLY_UDP6_RECEIPTS=1
D1_MXC_LOCAL_ONLY_NEVER_MXC_WFP_DNS_BROKER_OR_RELEASE_PROOF
LOCAL_NATIVE_CONTROL_EXIT=0
POST_SOURCE=f79d0a7131bd494c07b9fce01ba545c91536b97b
POST_CLEAN=True
```

## What this evidence cannot establish

This is an **unrestricted** loopback control, not a contained
network test, not WFP/ETW packet capture, not MXC denied-case
evidence and not an attributed WebView2 shared-service network audit.
`captureDenials` previously returned `E_NOTIMPL`; the
independent native MXC UDP `send_to=SENT23` ambiguity is
still unresolved. No DNS, IPv4/IPv6 external network, broker,
proxy, signing, immutable executable binding, independent human
security review or end-user machine-wide proof was performed.

Source/host data is sanitized. No admin privileges, global firewall,
system settings, PHI, EHR/patient data, installer, tag, protected
main merge, package upload or publication. Keep
[#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662)
**OPEN** and #603/#574/#622 release security/governance blockers
unresolved. `publication_authorized=false`; **RELEASE NO-GO**.

This report is an append-only author-side observation at the exact
frozen code SHA above. Do not treat the later evidence-only commit
as another compiled/run source SHA.
