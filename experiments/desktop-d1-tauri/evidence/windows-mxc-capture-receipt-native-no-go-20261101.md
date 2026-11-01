# MedOrigin D1 — MXC denial-capture receipt integrity and native-capture NO-GO

**2026-11-01 • NONPUBLISHING • SYNTHETIC ONLY • NO PHI • NO RELEASE.**
This is an author-side, bounded Windows qualification in a stacked Draft
branch. The EGM design draft remains unreviewed by fresh Goldfish agents.
Nothing here proves D1/WebView2/Windows broker packet egress denial.

## 1. Source-level fail-closed defect and repair

The existing `windows-mxc-capture-report-verdict.mjs` accepted an arbitrary
nonempty `denials` array and any `summary` object. It did **not**
compare `summary.totalDenials` against the SDK's structured
`outputMetadata.captureDenials.totalDenials`, require
`deniedResourcesTruncated === false`, validate records, or check that
at least one report row involved a network or capability denial.
A fabricated non-network row could therefore pass a *source-only*
report-verifier test as if it established evidence of network denial.

The existing capture runner additionally listed every `*.json` in
the output directory as an actionable report; MXC actually generates
`denials.<run-id>.json` plus
`denials.<run-id>.verbose.json`. It also granted the contained workload
`filesystem.readwritePaths: [output]`, placing the host-owned capture
directory inside the workload's writable policy.

The repaired source:
- Separates sandbox writable scratch (`work`) from the host-owned
  capture output (`output`). The workload is **not** granted the
  capture output as writable, while the native MXC capture manager
  writes the completed files on the host.
- Selects only the per-run actionable receipt from the **SDK-returned
  exact `outputPath`**, requires the matching verbose sibling, and
  rejects missing, unexpected or ambiguous JSON files.
- Requires a clean native completion (`exitCode=0`,
  `timedOut=false`, `warnings=[]`), three exact native
  `WSA10013` denial markers, valid SDK metadata, and explicit
  non-truncated status in **both SDK metadata and JSON**.
- Requires identical SDK, JSON summary and row counts plus native
  exit-code agreement, bounded input, known report enums, valid
  decimal-string filetime and PID, unique (resource,accessType) rows,
  and **at least one network or capability denial row**.
- Logs only bounded counts and an explicit
  `NOT_WFP_OR_PACKET_ATTESTED` classification, never raw resources,
  network names, ETL, retained trace or report payloads.
- Adds `probe(request)` before `run(request)` and a strict
  `requireNativeCapturePreflight` to **reject** any backend
  other than a warning-free `base-container` with
  `probes.nativeCaptureAvailable === true`. Guarded WPR/UAC capture
  or an unknown tier is **NO-GO**, not an automatic fallback.

The Windows native Node 24.22.1 offline source test suite returned
**30 PASS, 0 FAIL** at source commit
`3235ad707e0c64524b4604787c06e8a6cebbdb35`. These are tests
of JS validation and policy wiring, **not** OS packet capture.

## 2. Actual read-only request preflight — PASS only as a probe

Authorized Windows host, OS reported `10.0.26300`, x64.
Supported local Node `v24.22.1`, offline cached
`@microsoft/mxc-sdk@1.0.1`, Rust `1.97.1`. No paid service.

A disposable Node script invoked the documented SDK
`probe(request)` on an **explicit** ProcessContainer request with
`captureDenials.mode='block'`,
`network.egress.default='deny'`,
`network.ingress.default='deny'`, `hostLoopback='deny'`.
`probe` did not create a container, execute a workload or request UAC.
Sanitized observations:

```text
tier=base-container
probes.nativeCaptureAvailable=true
probes.guardedCaptureAvailable=false
warningsCount=0
errorCode=null
```

**Important:** This is a request compatibility check, not a guarantee
that `StartLearningModeTraceWithOptions` will execute successfully.
A successful `probe` must not be recorded as actual blocked traffic.

## 3. Real synthetic native capture execution — FAIL / NO-GO

After the preceding check, the freshly staged unchanged
`windows-mxc-capture-denials-experiment.mjs` invoked actual MXC
`run(request)` with the repaired verifier and no policy relaxation.
Its Rust test-only binary would attempt one ephemeral
`127.0.0.1` listener connection and one reserved RFC 5737
`198.51.100.7:443` connection, neither carrying patient data.

Result **before a capture report could be produced**:

```text
MXC_CAPTURE_NATIVE_PREFLIGHT base-container PROBE_ONLY_NO_UAC_NO_PACKET_PROOF
MXC_CAPTURE_REQUEST_BLOCK_WITH_NO_ALLOW
MXC_CAPTURE_NO_GO captureDenials: failed to start learning-mode capture:
  StartLearningModeTraceWithOptions failed (HRESULT = 0x80004001)
REAL_NATIVE_MXC_DENIAL_CAPTURE_EXIT=1
```

Windows `0x80004001` represents `E_NOTIMPL`. No actionable report
was emitted (`CAPTURE_REPORT_COUNT=0`) and no
`scratch-capture-*` temporary run folder remained. Consequently,
**there is no accepted capture or observed WFP packet-block receipt**.
This is not a green security test; it is a request-specific runtime
failure despite a clean request preflight. No UAC approval, admin
privileges, host-global firewall/audit changes, permissive Learning
Mode, PHI or background network monitoring were used.

A `base-container` native capture tier also does **not** automatically
match the previously qualified D1 AppContainer **primary-token gate**;
a real D1 GUI under this tier would require separate admission and
product-parity qualification. None occurred here.

## 4. Independent source references and next decision

- Microsoft [MXC Learning Mode](https://learn.microsoft.com/en-us/windows/apps/develop/mxc/learning-mode):
  a request `probe` does not start a container; capture can select
  a different isolation tier; incomplete/truncated reports are not
  valid policy evidence.
- Microsoft
  [Learning Mode denial format](https://github.com/microsoft/mxc/blob/main/docs/logging-access-denied.md):
  an actionable denials JSON has `denials[]` and a summary with
  `exitCode`, `totalDenials` and
  `deniedResourcesTruncated`, plus a verbose diagnostic sibling;
  network decisions may be summarized without a workload PID.
- Source: `experiments/desktop-d1-tauri/tests/windows-mxc-capture-denials-experiment.mjs`,
  `windows-mxc-capture-report-verdict.mjs`, and
  `windows-mxc-capture-contract.test.mjs`.
- Security source of truth: [issue #662](https://github.com/AbdulazizShehri/MedOrigin/issues/662)
  records real earlier WebView2 IPv6 TCP endpoints outside MXC.
  [Draft #797](https://github.com/AbdulazizShehri/MedOrigin/pull/797)
  has separate actual AppContainer-gated four-journey WebView2 tests.
  No evidence from one context may substitute for the other.

**Decision:** keep #662 **OPEN** and MedOrigin **RELEASE NO-GO**.
Next work requires reviewing the exact Microsoft OS-build/MXC learning
trace contract on an **authorized disposable Windows environment**
with independent capture, exact binary and policy identities,
DNS/IPv4/IPv6/TCP/UDP positive+negative flow evidence and
broker/process ancestry. Do not work around `E_NOTIMPL` by enabling
`mode='allow'`, modifying Windows globally, downgrading to a
weaker capture tier or treating socket snapshots as packets.

**No release, tag, protected-main merge, installer, clinical use,
patient data, paid service or global OS security-policy change.**
