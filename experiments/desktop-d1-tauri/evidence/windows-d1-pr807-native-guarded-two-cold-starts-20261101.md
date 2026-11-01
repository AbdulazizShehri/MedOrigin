# MedOrigin D1 PR #807: real Windows guarded two-cold-start qualification

**2026-11-01 • NONPUBLISHING • SYNTHETIC ONLY • NO PHI • NO CLINICAL USE • RELEASE NO-GO.**

This records actual native Windows execution from the **exact source commit**
`03498d7856cf15e32e3a5f627a778000365a08cc`. A later evidence-only
commit attaching this document does not itself constitute a rebuild of that
later Git commit. The result qualifies only the named artifact and bounded
test conditions; it does **not** close [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662).

## Host and reproducible input

- Authorized interactive Windows 11 Home, version 10.0.26300, 64-bit.
- Detached, isolated exact-source worktree on the **D:** drive;
  original persistent worktree and protected `main` unchanged.
- Portable, separately staged **Node.js v24.22.1** from official
  `nodejs.org/dist/v24.22.1/node-v24.22.1-win-x64.zip`;
  archive SHA-256 matched the official SHASUMS256 manifest:
  `d2046d28c2c3dcd211ac5145c0bf30e2047ef9dfb306693c8c6e2eccd8b95fa5`.
  The system Node installation was not replaced.
- Rust `rustc 1.97.1`, offline cached cargo registry;
  `npm ci --offline --no-audit --no-fund` succeeded.
- Official `npm run tauri build -- --debug --no-bundle` succeeded,
  including React/Vite, TypeScript and native Tauri/Rust Windows build.
  **No installer/bundle, deployment or package release** was produced.
- Exact native unpublished executable:
  `medorigin-desktop-d1-preview.exe`, **13,236,224 bytes**,
  SHA-256
  `ed4a30167c4a8a6bb8b4af30ce86dee0607f3494ee6e5d84eeed13f7da2a9381`.
- Offline cached `@microsoft/mxc-sdk@1.0.1` staged only in this
  disposable worktree's `node_modules`, with no tracked Git changes,
  and its `@microsoft/mxc-sdk/v1` `run` export imported successfully.

## Actual two-cold-start MXC run — PASS within narrow evidence boundary

Executed the exact repository
`tests/windows-mxc-d1-cold-restart-qualification.mjs`, supplying
the exact executable path and its SHA-256, from the supported Node runtime.
This runner invokes the newly guarded launcher twice; checks fresh
process identities, requires strict ordered SHA-bound sanitized UIA receipts,
rejects nonempty child stderr/unexpected stdout/signals, and checks exact
process identity absence after shutdown.

Actual captured source-runner transcript (two native Windows starts):

```text
EXACT_SOURCE=03498d7856cf15e32e3a5f627a778000365a08cc
PRE_NATIVE_SHA256=ed4a30167c4a8a6bb8b4af30ce86dee0607f3494ee6e5d84eeed13f7da2a9381
D1_MXC_GUARDED_COLD_START_1_RUNNER_EXIT=0
D1_MXC_GUARDED_COLD_START_1_GUI_4_OF_4_AND_NO_RESIDUAL_PROCESS_IDENTITIES_PASS
D1_MXC_GUARDED_COLD_START_2_RUNNER_EXIT=0
D1_MXC_GUARDED_COLD_START_2_GUI_4_OF_4_AND_NO_RESIDUAL_PROCESS_IDENTITIES_PASS
D1_MXC_TWO_GUARDED_COLD_STARTS_GUI_8_OF_8_NO_RESIDUAL_PASS_PACKET_WFP_STILL_NO_GO
NATIVE_TWO_COLD_START_EXIT=0
POST_NATIVE_SHA256=ed4a30167c4a8a6bb8b4af30ce86dee0607f3494ee6e5d84eeed13f7da2a9381
```

**8/8 fictional source-bound UIA journeys** succeeded across two
distinct guarded lifecycles; the actual process-root and WebView2
process identity checks found no exact descendants remaining after either
cycle. A separate post-run host process query counted **zero**
`medorigin-desktop-d1-preview` roots. The binary digest was unchanged
before/after. The local exact-source Git worktree stayed clean.

## Actual negative controls — PASS

The *same exact* EXE was launched directly outside MXC, twice, through a
bounded child-process test: (1) default uncontained environment, and
(2) synthetic spoof variables
`APP_CONTAINER=1`, `MXC_CONTAINER=1`,
`MEDORIGIN_SKIP_GATE=1` only in the spawned child environment.
Both real executions immediately refused as required by the native
Windows AppContainer token gate, with **exit 76** and
`D1_WINDOWS_APPCONTAINER_REQUIRED_NO_GO`:

```text
D1_UNCONTAINED_EXIT=76 ERROR=NONE MARKER=true
D1_SPOOFED_ENV_EXIT=76 ERROR=NONE MARKER=true
D1_TWO_DIRECT_EXECUTIONS_REFUSED_WITH_NATIVE_GATE
```

The negative tester had a bounded timeout and made no firewall, admin,
OS-wide policy or application-distribution changes.

## Source CI and incomplete security evidence

[Hosted Windows exact-source workflow run #41322308130](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41322308130)
passed **34/34** synthetic source/receipt mutation tests at the same
pre-evidence commit. The same **34/34** were independently rerun on the
authorized Windows device using checksum-verified portable Node 24.22.1.

**This is not a packet/WFP/DNS/UDP or full WebView2 broker network denial
proof.** The GUI's bounded socket sampling does not see all short-lived
packets, DNS, brokered connections or external UDP. Independent OS
packet-level capture for the complete app, IPv4/IPv6, proxies, lifecycle,
DNS and WebView2 brokers remains outstanding. Native
`captureDenials` previously produced `E_NOTIMPL` on this host;
the separate protocol matrix previously observed UDP `send_to`
soft-accept despite zero local-loopback delivery. Neither finding can be
relabelled as demonstrated total egress isolation.

No independent Goldfish/security approval, mandatory signed production
launcher, clinical-safety qualification or release/governance acceptance
has occurred. Keep **#662, #622, #603 and #574 OPEN** and keep
`publication_authorized=false`: **NO-GO** for protected-main merge,
release, installer, PyPI/TestPyPI publication, real patient data or
clinical use. This report is a factual native experimental receipt only.
