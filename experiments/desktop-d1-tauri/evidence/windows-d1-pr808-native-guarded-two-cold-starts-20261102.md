# MedOrigin D1 PR #808: actual native Windows guarded two-cold-start replay

**Executed 2026-11-02 (Asia/Riyadh). Unpublished synthetic-only developer
preview. NO PHI, NO clinical or patient use, RELEASE NO-GO.**

This is **actual** authorized interactive Windows execution, at the exact
**source code commit** `a7cdbdf4d498f1a75017333a20f6ae1db4a476b1`
([Draft PR #808](https://github.com/AbdulazizShehri/MedOrigin/pull/808)).
It is a newly rebuilt, independently SHA-pinned native executable and
two fresh cold starts of #808's strict PowerShell UIA stdio changes;
it is **not** a replay of the older #807 EXE.
This evidence-only Draft PR is a child of #808 and does not mutate the
original #808 head, its stacked descendants, or protected `main`.

## Exact-source build and verification

- Authorized Windows 11 Home, `10.0.26300`, desktop session.
- Clean detached Git worktree on the `D:` drive at the exact SHA above.
  No source modifications; tracked/untracked worktree status empty
  before source tests, before native run and after negative controls.
- Official portable Node.js **v24.22.1** extracted in a disposable
  toolchain directory, **not** installed globally. Downloaded official
  `node-v24.22.1-win-x64.zip` (37,748,064 bytes). Archive SHA-256
  was compared **directly** with the exact
  `node-v24.22.1-win-x64.zip` entry in the official
  `https://nodejs.org/dist/v24.22.1/SHASUMS256.txt`:
  `d2046d28c2c3dcd211ac5145c0bf30e2047ef9dfb306693c8c6e2eccd8b95fa5`.
  A manually transcribed candidate digest was rejected before extraction
  because it did not match; the independently fetched **official manifest
  and actual archive matched exactly** before executable use.
- Rust `rustc 1.97.1`, offline existing Cargo registry, isolated
  `CARGO_TARGET_DIR`, and offline npm cache. `npm ci --offline
  --no-audit --no-fund` succeeded; `npm run build` (TypeScript/Vite)
  succeeded. `npm run tauri build -- --debug --no-bundle` actually
  succeeded, **exit 0**, Rust `dev` build in **4m 26s**.
  No installer or release bundle was created.
- Newly built `medorigin-desktop-d1-preview.exe` exactly
  **13,236,224 bytes** with SHA-256
  `9313cf2dd1907be2572021236a3515bfd9c5a88f4893695a656e877787fbf084`.
  This is a **different EXE hash** from #807's
  `ed4a30167c4a8a6bb8b4af30ce86dee0607f3494ee6e5d84eeed13f7da2a9381`.
  Its digest was checked before MXC, after both cold starts and after
  the direct-launch negative controls, always unchanged.
- Staged cached `@microsoft/mxc-sdk@1.0.1` inside the disposable
  `node_modules` with `npm install --offline --no-save
  --package-lock=false`; `@microsoft/mxc-sdk/v1`
  `run` and `getPlatformSupport` imports succeeded.
  Git tracked/untracked tree remained clean.

## Actual source-only regression at exact build SHA

The **same source** ran the workflow's actual
`windows-mxc-d1-guarded-uia-observer.test.mjs` and
`windows-mxc-d1-guarded-cold-restart.test.mjs` with the verified
portable Node. Observer and launcher syntax checks succeeded.
**25/25 Node tests PASS, 0 failed/skipped**, including strict ordering,
replayed/forged receipts, extraneous stdout, nonempty observer stderr,
duplicate process identities, and stale/extraneous socket markers.
This is source regression, not a native packet/WFP security gate.

## Actual native guarded two-cold-start replay: 8/8 PASS

Invoked unchanged repository
`tests/windows-mxc-d1-cold-restart-qualification.mjs` with the exact
new executable path and the exact new binary SHA-256 from portable Node.
It called the guarded MXC launcher in two **separate** contained Windows
lifecycles, each requiring real GUI/UIA → Tauri IPC → Rust SHA fixture
journeys and exact-process-identity cleanup:

```text
EXACT_SOURCE=a7cdbdf4d498f1a75017333a20f6ae1db4a476b1
PRE_NATIVE_SHA256=9313cf2dd1907be2572021236a3515bfd9c5a88f4893695a656e877787fbf084
D1_MXC_GUARDED_COLD_START_1_RUNNER_EXIT=0
D1_MXC_GUARDED_COLD_START_1_GUI_4_OF_4_AND_NO_RESIDUAL_PROCESS_IDENTITIES_PASS
D1_MXC_GUARDED_COLD_START_2_RUNNER_EXIT=0
D1_MXC_GUARDED_COLD_START_2_GUI_4_OF_4_AND_NO_RESIDUAL_PROCESS_IDENTITIES_PASS
D1_MXC_TWO_GUARDED_COLD_STARTS_GUI_8_OF_8_NO_RESIDUAL_PASS_PACKET_WFP_STILL_NO_GO
PR808_TWO_COLD_START_EXIT=0
POST_NATIVE_SHA256=9313cf2dd1907be2572021236a3515bfd9c5a88f4893695a656e877787fbf084
TRACKED_SOURCE_DIRTY_COUNT=0
```

Afterward a separate Windows read-only host query confirmed
**zero remaining `medorigin-desktop-d1-preview.exe` roots**.
The runner's identity-bracketed descendant checks found no matching
root/descendant process identities remaining after either cold start.
It also rejects nonempty observer stderr, hidden stdout diagnostics,
unexpected signals, malformed exact-SHA and fixture/process receipts.
Each GUI journey was synthetic and source-bound.

## Actual direct-execution negative controls: two native exit-76 refusals

Ran the **same exact EXE** directly outside MXC, in (1) an ordinary
uncontained child environment and (2) a child with deliberately spoofed
`APP_CONTAINER=1`, `MXC_CONTAINER=1`,
`MEDORIGIN_SKIP_GATE=1` environment variables. Each child was
time-bounded; neither required elevation or modified any OS policy.

```text
D1_UNCONTAINED_EXIT=76 ERROR=NONE MARKER=true
D1_SPOOFED_ENV_EXIT=76 ERROR=NONE MARKER=true
PR808_TWO_DIRECT_EXECUTIONS_REFUSED_WITH_NATIVE_TOKEN_GATE
NATIVE_TWO_NEGATIVES_EXIT=0
EXECUTABLE_SHA256=9313cf2dd1907be2572021236a3515bfd9c5a88f4893695a656e877787fbf084
SOURCE_CLEAN=True
POST_NATIVE_HOST_D1_ROOT_COUNT=0
```

Both emitted `D1_WINDOWS_APPCONTAINER_REQUIRED_NO_GO`.
This demonstrates the native AppContainer **admission gate for these
two exact runs**, not a mandatory signed launcher, policy identity,
OS-enforced whole-process-tree packet denial or release readiness.

## Critical network / security / governance limitations

**This experiment is *NOT* a WFP/ETW, packet, DNS, IPv4/IPv6 UDP
or full WebView2 broker isolation proof.** MXC requested denied
egress/ingress/host-loopback; UIA source checked sampled endpoints,
not complete packet/audit events. No independent kernel-level blocked
flow events, network positive/negative observer controls, DNS
attribution, short-lived packets or external shared-service/broker
packet evidence were collected. Do not infer "zero network" from
bounded GUI/process observations.

Prior native MXC `captureDenials` still failed
`StartLearningModeTraceWithOptions: E_NOTIMPL`; the separate
UDP probe's `send_to=SENT23` with no local listener delivery remains
ambiguous. Keep
[#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662)
**OPEN / independent OS network denial NO-GO** and G3–G7 blocked
or not run. Independent security review
[#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603),
owner release/version governance
[#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574)
and optional dependency
[#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622)
remain separate open blockers.

No `main` merge, tag, signed installer, package distribution, PHI,
clinical use, external network probes, global firewall changes,
elevation or production/publishing activity was performed.
`publication_authorized=false`. The old #807 native receipt still
belongs exclusively to its own old source SHA; the new receipt belongs
exclusively to **#808 code SHA and new executable hash above**.
