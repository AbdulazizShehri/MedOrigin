# Windows MXC SDK supported-runtime enforcement — 2026-10-31

**NONPUBLISHING / SYNTHETIC ONLY / OPEN DRAFT #786**, stacked on [#784](https://github.com/AbdulazizShehri/MedOrigin/pull/784) exact parent `1abb52838dc99e62f6be7a6415f0982e90c52917`. This modifies **only the real interactive qualification launcher and its source-only tests**, not the Tauri WebView2 product, Windows firewall/WFP policy, bundled Node installation, production binary, frozen Python lock or package/release permissions.

## Why this correction was necessary

The preceding real interactive MXC ProcessContainer/WebView2 run used **Node v24.19.0** from the Windows machine. Microsoft's Node MXC SDK explicitly requires **Node 24.21.0+ on the 24.x line, or 26.8.0+ on the 26.x line** to correctly support native Windows stdio. A superficially successful UIA run on 24.19 cannot qualify SDK compatibility.

`windows-mxc-d1-runtime-node-qualification.mjs` now performs a **pure, fail-closed check** for a stable strict `major.minor.patch` release and `win32` platform. It allows documented Node 24.21+ and 26.8+ only and rejects malformed, prerelease, custom, other major lines, other OSes and unsupported older releases. The actual interactive `windows-mxc-d1-real-app-qualification.mjs` calls it **before `getPlatformSupport()` and before creating a container**. The check is deliberately conservative: new future Node release lines need an explicit reviewed contract update rather than implicit approval.

A dedicated four-case `node --test` suite checks actual launcher wiring and both accepted and rejected version matrices. The existing read-only Windows source CI includes it without running a GUI, changing OS policy or downloading tools.

## Real expected RED before code

At the **initial test-only branch** containing the new tests but no runtime helper/launcher changes, [GitHub Actions #41232820943](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41232820943) failed on Windows2025 at the new contract because `windows-mxc-d1-runtime-node-qualification.mjs` did not exist. This proves the missing **qualification source contract**, not a WebView2 network exploit.

## Portable official runtime and checksum

The real authorized Windows 11 interactive host reports kernel `10.0.26300.0` and had global Node `v24.19.0`. Without modifying that global installation, the test downloaded official `node-v26.12.1-win-x64.zip` from `https://nodejs.org/download/release/v26.12.1/` to a distinct task-owned `D:\MedOrigin-D1-Node26-MXC-QA-20261031` directory. Independently fetched the Node release `SHASUMS256.txt` over HTTPS; its SHA-256 for the archive and locally computed digest both matched:

`B3EFD5C70CBA3308ED46E7E699A9B8AAC075BBC6B027FCB39C84C31ACC25E2B4`.

The portable binary reported **`v26.12.1`**. **Checksum-match against HTTPS-hosted manifest is not an independently verified detached GPG signature**, so treat it as an authenticated source and integrity consistency check within normal TLS trust, not a cryptographic build provenance attestation. The machine's existing global Node remained `v24.19.0`.

For MXC, `@microsoft/mxc-sdk@1.0.1` installed **offline** from the already available local npm cache into this temporary fixture folder; the system SDK/Node and other project installations were not modified. On portable Node26, `getPlatformSupport()` returned `isSupported:true`, `availableMethods` containing `processcontainer`, and `isolationTier:base-container`.

## Real source-and-binary-bound Windows MXC results

The source-only checkout was pinned initially to existing parent SHA `1abb528...` and then to this branch's **code HEAD before this document**, `99f70ba7bbb49824967b85fdd1c2b3e02f7bf14e`. The Tauri executable was the *already separately qualified, unpublished synthetic Windows D1 binary* (not newly compiled from this PR). Its exact 13,215,232 bytes were SHA-256-checked before both supported Node runs:

`7ECEEA367A05CE60576D633FF48F593D8DBFF9ED2A56FF227D37C2280759B74A`.

**Negative on unsupported global Node 24.19.0:** executing the *actual guarded launcher* returned nonzero exit `1` with `D1_MXC_NODE_RUNTIME_NO_GO` **before launching the executable**; verified **zero D1 processes** afterward. The pure 4/4 test contract also passed locally. The first attempt to record this expected error tripped PowerShell's `ErrorActionPreference=Stop` native stderr handling; the follow-up ran with a consciously controlled error preference and confirmed the actual expected nonzero exit, rather than treating PowerShell's wrapper failure as the security assertion.

**Positive on portable supported Node 26.12.1:** executed that same exact guarded launcher under the MXC V1 `ProcessContainer` in the authorized interactive Windows session with `network.egress.default=deny`, `network.ingress.default=deny`, `hostLoopback=deny`, UI `isolation:container`, a task-only temporary local WebView2 profile, and no permissive proxy or explicit egress exceptions. Real Windows UIAutomation reported:

```text
D1_MXC_REAL_UIA_RESULT 0
MXC_D1_UIA_PASS patient-minimal
MXC_D1_UIA_PASS patient-invalid-utf8
MXC_D1_UIA_PASS patient-over-limit
MXC_D1_UIA_PASS patient-exact-limit
MXC_D1_PROCESS_TREE=8 WEBVIEW2=6 OWNED_TCP=0 NONLOOP_TCP=0 UDP_ENDPOINTS=0
MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12 max_owned_tcp=0 max_udp_endpoints=0 NO_PACKET_LEVEL_ATTESTATION
D1_MXC_REAL_APP_RESULT {"stdout":"","stderr":"","exitCode":-1,"timedOut":true,"warnings":[]}
D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO
Node command exited 0 (54.29 seconds including bounded timeout and cleanup)
```

The observed 12-sample network report is **socket/owner inventory only**. The debug executable is unchanged from previous builds and does not gain provenance attestation by running on a supported version of Node. Real WebView2 child identity evidence remains qualified only for the observed process windows.

## Qualification and cleanup

- **Pre-implementation CI RED:** [#41232820943](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41232820943).
- **After implementation prior to this documentation commit:** Windows2025 GitHub Actions [PR #41232873115](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41232873115) and [push #41232867662](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41232867662) **SUCCESS** at exact code SHA `99f70ba7bbb49824967b85fdd1c2b3e02f7bf14e`. Includes new pure Node runtime suite plus original root/descendant and lifecycle CI.
- **Final exact SHA after adding this document** must be separately checked for source-only CI success; do not reuse earlier run as final-head evidence.
- **Task-owned cleanup required:** portable Node archive/extract, SHA manifest, sparse Git checkout, offline SDK node_modules and all synthetic task test data under `D:\MedOrigin-D1-Node26-MXC-QA-20261031` must be deleted following durable evidence; do not claim deletion until verified.

## Real blockers remaining

Issue **#662** is **not closed**: 12 empty socket snapshots do not prove denied TCP, UDP, DNS, IPv4 or IPv6 packets, zero briefly-lived traffic, intercepted WinHTTP broker requests, or WFP policy behavior. MXC native `captureDenials` returned `E_NOTIMPL 0x80004001` on this host. No unprivileged global packet trace was started, no host firewall was altered, no OS updates were installed and no live external request/denial evidence was captured. A supported Windows build/capture provider or a reviewed OS-scoped equivalent is necessary to remove that NO-GO; prior observed WebView2 outbound TCP is still valid.

Other open blocking gates: **#574** owner/version/ADR release authority; **#603** independent security review; **#622** frozen optional research dependencies; **#673** Linux D2 unmaintained AccessKit/zbus; **#676** macOS VoiceOver. **Publication remains NO-GO**. No protected-main merge, tag, production installer, GitHub Release, PyPI upload, PHI, EHR writes, clinical claims or paid services.
