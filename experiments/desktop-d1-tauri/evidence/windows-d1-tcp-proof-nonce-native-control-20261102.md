# Windows D1 native localhost-only TCP proof challenge: source-bound qualification

**Executed 2026-11-02 Asia/Riyadh • synthetic-only • nonpublishing • owner Windows desktop • release NO-GO.**

This report describes **actual** native Windows source-bound execution of a
controlled **unrestricted 127.0.0.1 and ::1 only** Rust probe. It does not
run MXC denied-mode, WFP/ETW, DNS, WebView2, Tauri, shared-service
broker capture, internet egress or an OS network-security policy.
This is an author-side source/evidence-integrity exercise, not a signed
reviewer attestation.

## Why this source change matters

At parent Draft #817 the host-side positive control required exact
IPv4/IPv6 TCP accepted-peer addresses, port and family, but did not
check any payload from the expected Rust program. An unrelated local
TCP socket could be mistaken for the expected control connection while
a child stdout line independently claimed CONNECTED.

The new **test-only** protocol passes a distinct **128-bit random
lowercase hex nonce** for IPv4 and IPv6 as arguments to the exact
native Rust control probe, writes a canonical
`D1_MXC_TCP4_PROOF=<32hex>` or `D1_MXC_TCP6_PROOF=<32hex>`
frame into the corresponding TCP stream, and requires the host-side
TCP listener to observe **exactly one** bounded binary frame that
matches the independently generated per-family nonce. The pure
validator rejects absent, duplicated, appended, stale, truncated,
malformed, mismatched and re-used IPv4/IPv6 proofs. Only the synthetic
**unrestricted local positive control** is eligible; the MXC
`denied` mode's eight-socket refusal semantics are deliberately
unchanged. Existing UDP exact 23-byte local payload checks remain.
The native host listener tracks at most 128 proof bytes per connection,
marking overflow/socket errors invalid.

**Limit:** a nonce passed on the command line is *not* cryptographic
peer-process identity attestation. A sufficiently privileged local
attacker could inspect/replay arguments or manipulate the host.
Success only correlates bounded TCP proof bytes with the expected
synthetic test invocation; it is not a mandatory signed launcher
or kernel packet-denial proof.

## Test-first RED and GREEN on actual Windows

- Pinned original parent branch: [Draft #817](https://github.com/AbdulazizShehri/MedOrigin/pull/817)
  exact head `5a4c5d276353f049404421095578a3a802b2368c`.
- New RED test+workflow source
  `ed333d931663c1f062d41034d68196a53cdea8bf`,
  at a clean detached Windows worktree on `D:\`:
  **20 tests total, 1 PASS / 19 FAIL (expected RED)**.
  The previous verifier erroneously accepted all 18 new stale/malformed
  TCP-proof mutations, and native probe/runner source lacked proof wiring.
- Repaired Rust control writing, both bounded Node TCP listener
  collectors, strict verifier and existing source fixtures without
  weakening their previous negative cases. One intermediate
  `a3f12fc9dbd2c5472469ff757cffcf5b9e5615d6` test run
  reached **119 total / 118 PASS / 1 FAIL** because an existing
  syntax/source contract test still required `spawnSync(probe,
  [...ports, 'control'])` without the new challenge arguments.
  The test contract was amended to **require** both random nonce
  arguments rather than dropped or waived.
- Exact successful executable/source checkout:
  `677d8be9f31758adb625e16f11a18c98955d26f8`.
  Node.js v24.19.0 (Windows host), Rust `rustc 1.97.1`,
  source tree clean; the seven source regression files ran
  **119/119 PASS, 0 failure, 0 skip**. New native runner,
  network-verifier and MXC runner syntax checks passed.
- Ran the *new exact Rust probe* via
  `tests/windows-mxc-unconfined-loopback-qualification.mjs` with
  `MEDORIGIN_MXC_TEST_TMP=D:\`, using a task-owned
  disposable scratch folder; **one TCP IPv4/IPv6 accept each**
  matched the corresponding dynamic nonce frame; **one canonical
  23-byte UDP4/UDP6 receipt each**; native script **exit 0**,
  working Git source clean.
- Native compiled Rust probe SHA-256:
  `4c3c8b4f5fc3e223a50bc25b13452672ab09a27db7d6380df421ee5d16474a22`.
  Exact native stdout excerpt:

```text
D1_MXC_LOCAL_ONLY_UNRESTRICTED_TCP4_TCP6_UDP4_UDP6_CONTROL_PASS
D1_MXC_LOCAL_ONLY_PROBE_SHA256=4c3c8b4f5fc3e223a50bc25b13452672ab09a27db7d6380df421ee5d16474a22
D1_MXC_LOCAL_ONLY_TCP4_ACCEPTS=1
D1_MXC_LOCAL_ONLY_TCP6_ACCEPTS=1
D1_MXC_LOCAL_ONLY_UDP4_RECEIPTS=1
D1_MXC_LOCAL_ONLY_UDP6_RECEIPTS=1
D1_MXC_LOCAL_ONLY_NEVER_MXC_WFP_DNS_BROKER_OR_RELEASE_PROOF
NATIVE_CONTROL_EXIT=0
SOURCE_CLEAN=True
```

The later CI workflow edit, evidence-only commit and PR HEAD did
**not** produce new native binaries: link actual native results only
to the exact older tested source `677d8be9...`. Fresh hosted Windows
CI at the final source/evidence commit should be evaluated separately;
a hosted source test cannot be described as a native MXC run.

## Non-negotiable security and release limits

Native MXC `captureDenials` earlier returned
`StartLearningModeTraceWithOptions: E_NOTIMPL`; MXC UDP
`send_to=SENT23` with no observed local delivery remains
ambiguous. There is **no** independent OS packet/WFP deny for
WebView2, DNS, proxy, IPv4/IPv6 UDP or broker/shared-service
attribution. No real D1 GUI/MXC contained application was launched
by this new local-only test. [Issue #662](https://github.com/AbdulazizShehri/MedOrigin/issues/662)
remains **OPEN / G3–G7 NO-GO**. Independent security #603, owner
release authority #574, optional dependency governance #622 and
additional platform blockers remain separate.

No PHI, clinical use, Tauri/Rust production mutation, system-wide
firewall/policy changes, elevation, paid infrastructure, protected-main
merge, tag, package registry upload, installer or publication.
`publication_authorized=false`. Any conclusion beyond local source
correlation is outside this report.
