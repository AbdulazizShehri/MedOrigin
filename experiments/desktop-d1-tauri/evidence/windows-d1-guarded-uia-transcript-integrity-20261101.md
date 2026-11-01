# Windows D1 guarded UIAutomation transcript integrity — native RED/GREEN qualification

**2026-11-01 • NONPUBLISHING • SYNTHETIC ONLY • NO PHI • RELEASE NO-GO.**

## Why this was necessary

The existing experimental guarded MXC entrypoint checked four UIA journey
markers, one unanchored `MXC_D1_PROCESS_TREE` regex and a source SHA string,
but did not require a unique complete-line process-tree record, reconcile
its reported process/WebView2 counts with the available
`MXC_D1_PROCESS_SNAPSHOT_JSON`, or detect replayed/out-of-order evidence.
These limitations could allow a bad or truncated *test transcript* to look
like successful qualification. They are not proof of an actual product
network vulnerability or exfiltration.

The repaired, still **experimental** local
`tests/windows-mxc-d1-guarded-uia-observer.mjs` now validates:
- Exact once-only, chronological receipt for each of four immutable
  synthetic SHA journeys; no unknown, duplicated, prefixed, suffixed or
  replayed `MXC_D1_UIA_PASS` records.
- Exactly one bounded JSON process census, parsed through the already
  existing `windows-mxc-d1-lifecycle-proof.mjs` (not a second independent
  parser), containing a real D1 process identity and WebView2 descendants
  with distinct valid PIDs and creation ticks.
- Exactly one complete-line process summary matching both actual
  process count and WebView2 count, zero observed TCP/UDP endpoints and
  the exact SHA-256 of the source-built executable.
- A unique final `samples=12` bounded socket sampling sentinel,
  source-bound final marker and strict ordering after UIA/process evidence.
- Explicit fail-closed status, output-size bound and incomplete/extra
  receipt rejection. These tests cannot turn **sampled** socket
  observations into WFP/packet/DNS/broker egress evidence.

Source-only tests also examine the actual PowerShell UIA script's receipt
emission order, preventing a source drift between producer and verifier.

## Native Windows qualification on exact current source

**Device:** authorized interactive Windows 11 Home 26H2, build
`26300.9818` x64. No admin/UAC or global firewall/security-policy edits.
**SDK:** locally cached `@microsoft/mxc-sdk@1.0.1` with supported
Windows Node 24.22.1. No paid services or PHI.

- Detached exact-source, unchanged product worktree at
  `ce9028d4f288b48b6f87b756fc078db9eac89680`, corresponding to
  the strict observer and test edits (subsequent branch commit adds only
  the source-CI workflow and evidence).
- From `experiments/desktop-d1-tauri`:
  `npm ci --offline --no-audit --no-fund` and the **official**
  `npm run tauri build -- --debug --no-bundle`: **PASS**, including
  TypeScript/Vite and native Tauri/Rust Windows compilation.
- Exact resulting *unpublished* Windows
  `medorigin-desktop-d1-preview.exe`: **13,236,224 bytes**,
  SHA-256
  `0bb694a541554bbba2419c425a2859090d8ca18aca31973869bb554a43a90189`.
- The identical source-built file run via the actual
  `windows-mxc-d1-guarded-preview-launch.mjs`, under native MXC
  ProcessContainer `egress=deny`, `ingress=deny`,
  `hostLoopback=deny`, GUI isolation and a disposable writable profile:
  **PASS**, full launcher **EXIT 0**, exact
  `D1_GUARDED_REAL_UIA_4_OF_4_AND_SOCKETS_PASS_NETWORK_STILL_NO_GO`
  marker. The launcher checks the actual SDK result and guarded UIA
  observer's stricter transcript validation. Prior actual UIA source
  produces four synthetic React/Tauri/Rust SHA journeys, WebView2
  descendants, process identity snapshot, and 12 identity-bracketed
  TCP/UDP samples (a sampled observation **only**).
- Source-built binary SHA-256 reverified byte-identical after the
  MXC trial.
- Direct launch of the **same exact EXE** without a ProcessContainer,
  both with normal environment and with `APP_CONTAINER` /
  `MXC_CONTAINER` / `MEDORIGIN_SKIP_GATE` environment spoofing:
  **2/2 refused**, each **exit 76** with
  `D1_WINDOWS_APPCONTAINER_REQUIRED_NO_GO`.
- After the guarded run, **zero** matching app roots remained.
- Actual authorized Windows source integrity tests for guarded launcher,
  strict UIA transcript and lifecycle: **23/23 PASS** (zero failures).
- [Hosted Windows source CI #41319271213](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41319271213):
  **SUCCESS**, 23/23 tests, all job steps inspected. Hosted CI checks
  sources and synthetic transcripts only; the native GUI trial above
  was executed separately on the authorized Windows desktop.

## Boundaries and remaining NO-GO

This is a trustworthy improvement to **test receipt integrity**, not a
claim of independent native OS network audit, authenticated signing of
the launcher, immutable file-handle binding, WFP packet-level denial,
DNS/IPv4/IPv6/UDP or WebView2 service/broker egress attribution. The
separate source-built app remains an *unpublished synthetic-only D1
experimental preview* and cannot be offered for patients or clinical use.

The original external WebView2 IPv6/TCP evidence
([#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662))
is not invalidated by the sampled zero-socket GUI checks. The native
`captureDenials` test still fails `StartLearningModeTraceWithOptions`
with `HRESULT 0x80004001` on this Windows host; the separate
UDP protocol matrix still yields `SENT23` despite zero local delivery
under deny-all. [Draft #804](https://github.com/AbdulazizShehri/MedOrigin/pull/804)
documents that network gap; independent OS packet and DNS audit,
full broker/service/lifecycle testing and external security sign-off
have **not** been completed.

**Keep #662/#603/#574/#622 OPEN and project RELEASE NO-GO**. Do not
merge protected main, tag, publish, distribute installers, elevate
privileges, modify Windows security globally, process PHI or claim
independent Goldfish/security approval. All disposable local worktrees,
binaries and temporary SDK/test stages should be removed after saving
this GitHub evidence; historical research receipts and original
persistent workspace remain untouched.
