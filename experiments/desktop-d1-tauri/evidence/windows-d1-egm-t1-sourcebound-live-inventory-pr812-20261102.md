# T1 Windows read-only source-bound feasibility: native host receipt

**Executed:** 2026-11-02 Asia/Riyadh, authorized Windows desktop.
**Source implementation SHA:** `402c2615fa9d6e7199ea17265bdf9e4a24a1cd77` (Draft #812).
**Status:** **SOURCE-ONLY AND READ-ONLY FEASIBILITY PASS; NETWORK ISOLATION NO-GO**.

## Execution boundary and reproducibility

- Detached disposable clean Git worktree at
  `D:\MedOrigin-T1-PR812-exact-source-20261102`, obtained from
  `test/medorigin-d1-t1-clean-source-20261101`; original working
  tree untouched. Exact source SHA confirmed before and after.
- Node.js **v24.19.0** on Windows **10.0.26300** (the on-host runtime,
  not the v24.22.1 plan-pinned native MXC runtime).
- Executed from exact detached project root:
  `node --test experiments/desktop-d1-tauri/tests/windows-d1-observer-capability-inventory.test.mjs experiments/desktop-d1-tauri/tests/windows-d1-egm-evidence-verdict.test.mjs`.
- **24 tests passed, 0 failed, 0 skipped**: 12 T1 capability/provenance
  cases plus 12 T2 pure, backend-neutral, source-receipt cases.
- Executed **actual nonprivileged read-only Windows CLI**
  `node experiments/desktop-d1-tauri/tests/windows-d1-observer-capability-inventory.mjs`,
  **exit 0**, and captured its deliberately low-sensitivity,
  fixed-schema JSON output:

```json
{
  "status": "READ_ONLY_FEASIBILITY",
  "sourceSha": "402c2615fa9d6e7199ea17265bdf9e4a24a1cd77",
  "osBuild": "10.0.26300",
  "sdkVersion": "UNAVAILABLE",
  "observerAvailable": false,
  "captureProbeOnly": false,
  "privilegeRequired": "UNKNOWN",
  "reason": "SDK_UNAVAILABLE"
}
```

- `PRE_SHA = POST_SHA =
  402c2615fa9d6e7199ea17265bdf9e4a24a1cd77`.
  Source worktree clean before/after; `POST_STATUS_COUNT=0`.
  Script's internal `readCleanGitSourceIdentity` also independently
  checked clean and identical HEAD around its host query. This is a
  two-snapshot provenance check, **not** an atomic file-system attestation.
- **No admin elevation, firewall rule, WFP/ETW audit activation,
  native MXC/SDK import, external network probe, packet capture,
  WebView2 or Tauri launch, personally identifying host data, PHI,
  clinical/production data, paid model or release operation.**

## Interpretation and hard limits

`sdkVersion="UNAVAILABLE"` specifically means no recognized
`@microsoft/mxc-sdk` release was found in the checked-in
`experiments/desktop-d1-tauri/package-lock.json` metadata
without installing or importing SDK. It is **NOT** a finding that
the Windows host has no MXC SDK anywhere, nor an assertion about
the underlying Windows observer backend. The earlier **actual native**
MXC `captureDenials` invocation on Windows 26300/SDK 1.0.1
failed `StartLearningModeTraceWithOptions: E_NOTIMPL`
([existing native NO-GO evidence](windows-mxc-capture-receipt-native-no-go-20261101.md)).
That remains unresolved.

This new receipt does not prove `observerAvailable`, WFP/ETW packet
events, DNS capture, IPv4/IPv6 TCP/UDP denial, Windows shared-service
or WebView2 broker attribution. The earlier UDP `send_to=SENT23`
soft-accept remains inconclusive. **G3 BLOCKED; G4/G5 NOT_RUN;
G7 BLOCKED; #662 OPEN; release NO-GO.**

The post-test documentation-only evidence commit comes **after** this
exact-source execution. Do not imply that the native T1 executable
was rebuilt or rerun from a later evidence-only SHA.
Issue #603 independent security review, #574 owner/release
governance and #622 dependency remediation remain outstanding.
This report is author-side evidence, not a signed independent
security-review receipt. No tag, installer, protected-main merge,
publication or clinical clearance; `publication_authorized=false`.
