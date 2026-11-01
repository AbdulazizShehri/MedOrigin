# Guarded Windows D1 — two real cold starts and process-identity cleanup

> **2026-11-01 | synthetic-only | nonpublishing | no PHI | release NO-GO.**
> This evidence qualifies a narrow candidate **experimental** MXC launcher and
> process lifecycle. It is **not** OS WFP/packet/DNS or full WebView2 broker
> egress attestation, and does not turn the candidate launcher into a signed,
> mandatory production entrypoint.

## What changed

The pre-existing
`tests/windows-mxc-d1-cold-restart-qualification.mjs` previously called
the *older* `windows-mxc-d1-real-app-qualification.mjs` and accepted
`requireQualifiedRun` legacy free-text success fragments. This was a
weaker transcript policy than the strict, source-backed four-journey UIA
proof qualified in [Draft #805](https://github.com/AbdulazizShehri/MedOrigin/pull/805).

The updated test code now:

1. Uses `requirePinnedD1Executable` for the exact normal Windows executable
   path, regular file, every parent-path symlink/junction and SHA-256; checks
   the approved SHA before **both** native starts.
2. Invokes the exact existing
   `windows-mxc-d1-guarded-preview-launch.mjs` twice, **never** the legacy
   unguarded runner. The guarded entrypoint requires MXC
   `network.egress.default=deny`, `network.ingress.default=deny`,
   `hostLoopback=deny` and GUI process-container isolation and refuses
   any fallback to a direct process spawn.
3. After MXC completes and its own strict UIA observer has validated
   four source-bound React/Tauri/Rust SHA fixture journeys, one real D1 +
   WebView2 process inventory with immutable PID/start ticks, exact binary
   SHA and bounded 12-sample TCP/UDP checks, the launcher prints **only**
   the sanitized validated process inventory, exact SHA and final marker.
4. New `requireGuardedQualifiedRun` accepts exactly the **three unique,
   ordered** guarded receipts, rejects a missing/malformed/duplicate or
   mismatched SHA and uses the pre-existing lifecycle inventory validator.
   It will not accept the old runner's free-text success fragments.
5. After each complete native run the parent re-enumerates the observed
   process PIDs/start ticks, refuses *any* surviving exact identity and
   refuses a pre-existing exact-path D1 root. The next run must have a
   **different** root PID/start-time identity.
6. The pure tests deliberately reject old, partial, replayed, duplicated,
   out-of-order, foreign or corrupted transcripts, invalid/missing
   descendants, changed source SHA, and lingering exact process identity.

Only experimental test JS, source-only Windows CI, and this evidence
report changed. No production Rust/Tauri UI, host-global firewall/OS
security policy, clinical code, paid service or installation workflow changed.

## Automated source qualification

- Checked branch source commit
  `52bee7d5034c6661427cf591a70ca43dd6bab568`.
- Authorized local Windows Node 24 source contracts:
  **31 tests / 31 pass / 0 fail** across guarded launcher, guarded
  cold-restart receipt, UIA evidence, and exact lifecycle identity.
  An initial disposable partial scratch was missing an existing
  PowerShell source helper; it was **not** a valid source failure.
  The missing canonical file was staged unchanged, and the entire
  combined suite passed.
- [Exact-source Windows GitHub Actions run #41321814744](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41321814744)
  completed **SUCCESS**, with all hosted job steps checked:
  **31/31 PASS**. This CI is source-only; the following native GUI
  trials were run separately on an authorized Windows device.

## Native real-world test A — historic approved synthetic D1 executable

In a fresh disposable, local-only MXC SDK `1.0.1` stage with supported
Windows Node `24.22.1`, the earlier approved source-built synthetic
D1 preview binary (staged **2026-10-29**) had SHA-256:

`7eceea367a05ce60576d633ff48f593d8dbff9ed2a56ff227d37c2280759b74a`

and file size **13,215,232 bytes**.

The new guarded cold-start runner executed two native MXC GUI sessions:

```text
D1_MXC_GUARDED_COLD_START_1_RUNNER_EXIT=0
D1_MXC_GUARDED_COLD_START_1_GUI_4_OF_4_AND_NO_RESIDUAL_PROCESS_IDENTITIES_PASS
D1_MXC_GUARDED_COLD_START_2_RUNNER_EXIT=0
D1_MXC_GUARDED_COLD_START_2_GUI_4_OF_4_AND_NO_RESIDUAL_PROCESS_IDENTITIES_PASS
D1_MXC_TWO_GUARDED_COLD_STARTS_GUI_8_OF_8_NO_RESIDUAL_PASS_PACKET_WFP_STILL_NO_GO
ACTUAL_GUARDED_D1_TWO_COLD_STARTS_EXIT=0
```

The input binary SHA matched after completion, **0** exact-path D1
roots and **0** task-owned guarded scratch folders remained.
**Important provenance limit:** this old 2026-10-29 binary predates
the later networkLoopback AppContainer capability guard hardening. It
qualifies the newly guarded **test harness**, not the current security
binary. We therefore rebuilt current source and repeated the trial.

## Native real-world test B — CURRENT SOURCE Windows D1 binary

- Exact checked-out source:
  `52bee7d5034c6661427cf591a70ca43dd6bab568`;
  `npm ci --offline --no-audit --no-fund` and the official
  `npm run tauri build -- --debug --no-bundle` **PASS**,
  including TypeScript/Vite and native Tauri/Rust.
- Windows D1 executable **13,236,224 bytes**, SHA-256:
  `a36043a4028d9703e2cc29cc9e7e1b0a49476b74d5c02e0a17c8bb786aac8c6b`.
- On Windows 11 Home 26H2 **build 26300.9818** with
  `@microsoft/mxc-sdk@1.0.1`, supported Node 24.22.1, in a
  per-test contained profile with **egress/ingress/hostLoopback deny**:
  the **same newly built exact binary** completed two actual GUI/UIA
  4/4 journeys, giving **8/8 passes**. Guarded runners both EXIT 0,
  all source-bound UIA transcript and 12 process-attributed TCP/UDP
  socket samples accepted, the exact process census checked after
  each shutdown, and both root lifecycles were distinct.
- Terminal marker:
  `D1_MXC_TWO_GUARDED_COLD_STARTS_GUI_8_OF_8_NO_RESIDUAL_PASS_PACKET_WFP_STILL_NO_GO`;
  parent test `CURRENT_EXACT_SOURCE_GUARDED_TWO_COLD_START_EXIT=0`.
- The exact binary SHA was reverified after the native trials;
  **0** exact-path D1 roots and **0** task-owned guarded MXC
  temporary directories remained.
- Same exact new executable: **2/2 direct Windows starts fail closed**
  with exit **76**, both plain and deliberately environment-spoofed,
  displaying `D1_WINDOWS_APPCONTAINER_REQUIRED_NO_GO`.
- `cargo test --locked --offline` on the exact current source
  **2 passed, 0 failed** (plus zero main/doc tests), exit **0**.
- No admin UAC, global OS/firewall policy changes, PHI or
  uncontained successful app launch. Compiled binaries remain
  nonpublishing test artifacts; no installer or release produced.

## What the test does NOT establish

The 12 sampled owned TCP/UDP endpoint checks are bounded *socket
snapshots*, not an independent WFP network packet log. They may miss
short-lived packets, DNS traffic, or network service/broker processes
outside the D1 descendant tree. Earlier real direct/uncontained
WebView2 IPv6 TCP connections in [issue #662](https://github.com/AbdulazizShehri/MedOrigin/issues/662)
are not disproved. On this Windows host the separate native MXC
`captureDenials` request reported `E_NOTIMPL 0x80004001` despite
a positive request probe, and synthetic UDP `send_to` returned
`SENT23` even with no loopback listeners receiving. Those
independent WFP/DNS/IPv4/IPv6/UDP/broker release blockers are not
addressed by an 8/8 UIA lifecycle result.

The guarded launcher remains an experimental **optional** entrypoint.
It is not a signed, OS-mandatory, immutable file-handle-bound
production trust anchor, and no genuine fresh-context EGM Goldfish
or independent security approval was performed.

**Status:** keep #662, #603, #574 and #622 **OPEN / release NO-GO**;
keep stacked PRs Draft; no protected main merge, tag, installer,
publication, distribution, PHI or clinical use. Store durable evidence
in this repo and remove task-owned scratch / native build stages
without touching the owner's original workspace or the historical
approved executable.
