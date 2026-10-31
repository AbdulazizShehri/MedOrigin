# MedOrigin Desktop D1 — synthetic-only local Tauri preview

**Status: experimental / unpublished / not reviewed for release.** This standalone Tauri 2 + React/TypeScript app is a *consumer* of the sibling isolated Rust D0 fixture-hash crate. It is not a clinician-facing product, a distributable installer, or a replacement for the Python Research Core.

## What is implemented

- One fixed local window, visibly marked **SYNTHETIC / DEVELOPER PREVIEW**.
- Exactly two native commands: `preview_status` and `hash_fixture`.
- Four *fictional, static in-memory* samples with source-bound SHA-256 golden digests. UI accepts only an enumerated fixture ID; Rust validates it again and enforces a byte cap.
- No application HTTP server in the compiled preview, opener/shell/filesystem/updater plugin, remote assets, application telemetry, model weights, Python worker, application network permission, patient records or EHR interaction. Vite's localhost server is **development-only**. **WebView2 itself may contact external services** even when the app has no network plugin; this is not yet an offline/zero-egress-qualified runtime.
- Tauri capability permits core window functionality only; CSP restricts application fetch to local Tauri IPC, **not WebView2's own background network traffic**. Packaging is disabled (`bundle.active=false`), and the app version is intentionally `0.0.0`.
- Rust errors are stable non-sensitive codes. No user-controlled path, URL or file contents enters the command.

## Local developer qualification (free tooling)

```powershell
cd experiments/desktop-d1-tauri
npm ci --no-audit --no-fund
npm run build
cd src-tauri
cargo fmt --all -- --check
cargo check --locked
cargo test --locked
```

A bundle/uninstaller is **not generated**; verify the native window only by running `npm run tauri dev` on an authorized development device and inspecting its behavior. The general D0 Rust 3-OS evidence is not a substitute for D1 Tauri build evidence on each OS.

## Reproducible native Windows UI and egress checks

From an **interactive** Windows desktop, build the local debug preview with `npm run tauri build -- --debug --no-bundle`, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows-uia-smoke.ps1 -ExePath '<absolute-path-to-built-debug-exe>'
# Launch the same executable separately; capture its PID as $p.Id:
$p = Start-Process -FilePath '<absolute-path-to-built-debug-exe>' -PassThru
Start-Sleep -Seconds 5
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows-egress-snapshot.ps1 -RootPid $p.Id
Stop-Process -Id $p.Id -Force
```

The UI Automation smoke test verifies all four fictional fixture IDs through **React → Tauri IPC → Rust → React** and checks exact SHA-256 goldens. The invalid-encoding and oversize samples are *expected to hash successfully*; this does **not** mean they pass FHIR validation. The egress audit inspects the root process and descendant WebView2 processes; it exits 2 on any observed non-loopback TCP state (including `SynSent`), and fails closed if process/socket enumeration fails. Its separate `tests/windows-egress-probe-selftest.ps1` runs nine mocked scenarios, including external TCP attempts from nested descendants, unrelated-process exclusion, missing-root fail-closed behavior, socket-enumeration errors, and loopback allowance. It does **not** exercise the actual OS network boundary. A clean snapshot is **not** proof of zero network activity.

**Observed security NO-GO on Windows, 2026-10-29:** With the local D1 debug preview running, `msedgewebview2.exe` descendants established **external IPv6 TCP port 443** connections (two to three in repeated snapshots). The same problem persisted with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS='--disable-background-networking --disable-component-update'`. This is a runtime observation, not proof of what content was sent or whether the app initiated the traffic. Do **not** claim the desktop is zero-egress/offline-isolated, or allow PHI, release, or clinical use. Any future resolution requires a separately reviewed, application-scoped OS isolation policy and packet-level verification; do not disable system-wide WebView2 security updates or firewall other applications.

## Known blocks

This independent D1 experiment must remain a **Draft** until a separately accepted topology/language decision (ADR-0003 + proposed ADR-0013), reviewed dependency locks/licenses/advisories, Windows/macOS/Linux app-level tests, verified zero network calls, IPC negative tests, WebView2 behavior, accessibility, process resource budgets and signed installer/uninstall lifecycle receipts. No release, tag, protected-main merge, PHI authorization or clinical-performance claim may be inferred from successful builds.

## Windowed native process-tree TCP observation — fail-closed but not isolation

The new separate, **nonpublishing** script
`tests/windows-egress-window.ps1` checks for a **real already-running
authorized D1 preview** during a bounded observation window. It does not
launch/stop applications or modify Windows firewall/WFP, the registry,
WebView2 runtimes, OS updates, network interfaces, the source package,
or any release setting. The script requires the **actual process PID**
and an independently computed **SHA-256 digest of its executable bytes**:

```powershell
$exe = 'D:\path\to\medorigin-desktop-d1-preview.exe'
$sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash
$p = Start-Process -FilePath $exe -PassThru
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/windows-egress-window.ps1 `
  -RootPid $p.Id -ExpectedExeSha256 $sha -DurationSeconds 15 `
  -IntervalMilliseconds 250
# Stop ONLY this personally launched test process when finished.
```

**Fail closed:** verifies exact D1 process name, executable path, byte SHA,
process start timestamp and absence of PID-reuse before each sample. Rebuilds
descendant PID ownership from a fresh `Win32_Process` snapshot, observes
ALL states of `Get-NetTCPConnection` including `SynSent`, and queries
`Get-NetUDPEndpoint` each sample. Any observed non-loopback TCP in the
tree (or malformed/ambiguous remote address on a non-listening socket)
triggers **exit 2**. A missing/changed root, corrupt sample, denied
process/TCP/UDP enumeration or invalid arguments triggers **exit 1**.
Clean bounded observation exits **0** but prints
`D1_NETWORK_ISOLATION_STILL_NO_GO`; it NEVER prints a
`ZERO_EGRESS_PASS` or authorizes release. It reports the maximum number
of UDP sockets **without claiming to inspect UDP payloads or destination
addresses**. This only supplements the existing instant snapshot
`tests/windows-egress-snapshot.ps1`; it does NOT supersede source or
kernel packet-level/WFP evidence.

**Technical self-tests, 2026-10-31:** Windows PowerShell 5.1,
`tests/windows-egress-window-selftest.ps1` **12/12 PASS**, including nested
descendant ownership, unrelated-PID exclusion, loopback IPv4,
127/8, IPv6 and IPv4-mapped IPv6, missing root, non-loopback IPv4/IPv6,
`SynSent`, delayed second-sample exfiltration attempt, ambiguous remote
address and unexpected established wildcard. The separate invalid real PID
watcher call fails closed exit 1. Unit tests use **mocked Win32 process
and TCP records**; no outside traffic is generated and no actual D1
binary was available during this development run. Thus **no real D1
WebView2 runtime verdict** follows from those self-tests, unlike the
historical real Windows observed external traffic in issue #662.

**Important blind spots:** intervals can miss fast TCP handshakes and
connections after process exit; process-tree sampling can miss short-lived
descendants or broker/service traffic not owned by the child tree.
UDP endpoint enumeration does not expose UDP packet destinations, and
DNS/IPv6 UDP/proxy brokers remain outside this TCP-only verdict.
The script cannot prove Windows Filtering Platform OS-enforced outbound
denial, cannot guarantee that background WebView2 security updates are
untouched, and is not a replacement for signed external review. It does
not automatically close #662, approve D2 over D1, or change frozen
research, version, clinical or publisher policy. No release, package,
installer, real PHI, EHR writes or public publication.

## Windows native ProcessContainer OS WFP-denial candidate (2026-10-31, NONPUBLISHING)

A promising **application-scoped** OS-enforced alternative to globally blocking
`msedgewebview2.exe` has been tested using Microsoft's
[MXC ProcessContainer](https://learn.microsoft.com/en-us/windows/apps/develop/mxc/quickstart)
and [directional network policy](https://github.com/microsoft/mxc/blob/main/docs/backends/process-container/networking.md).
Unlike a global program-path Windows Defender Firewall rule, the MXC
ProcessContainer uses native PSEC and container-lifetime Windows Filtering
Platform (WFP) conditions for **only the contained workload**. No Edge
runtime update, global firewall policy or parent OS privilege was changed.

### Reproduced on a real Windows host

Authorized Windows 11 Home **26H2 build 26300.9818**, normal non-admin user,
Node 24.19.0, isolated `@microsoft/mxc-sdk@1.0.1`, Rust 1.97.1 MSVC:
- `getPlatformSupport()`: `isSupported=true`,
  `availableMethods` includes `processcontainer`, no isolation warnings.
  Native Win32 `cmd.exe` test ran successfully in the OS container (exit0).
- Compiled standalone test-only
  `tests/windows-mxc-tcp-probe.rs` using exact Rust1.97.1. Bound a
  temporary host listener **only** to `127.0.0.1`. The **identical compiled
  executable** launched unrestricted connected successfully to the host
  listener (positive control).
- Ran that same Rust binary **inside MXC ProcessContainer** with explicit
  `network.egress.default=deny`, `network.ingress.default=deny`,
  `network.ingress.hostLoopback=deny`, no internet/private-network capability,
  no GUI/clipboard privilege. Native WinSock returned **`WSA10013`
  (WSAEACCES)** for the host-local synthetic listener **and** for
  `198.51.100.7:443` (reserved RFC5737 TEST-NET-2, not an external service).
  A timeout, connection-refused, missing listener or routing error fails
  the qualification. The source-bound test exited0:
  `D1_MXC_NATIVE_PROCESSCONTAINER_EXPLICIT_IPV4_TCP_DENIAL_PASS_NOT_D1_APP`.
- Early attempted Node.exe *inside* MXC exited `0xC0000142` during Windows
  DLL initialization, **before** network testing; it was never counted as
  denial evidence. Replaced with the minimal native Rust test executable and
  reran successful OS checks under explicit policy. A host-local TCP
  positive control prevents conflating a missing server with WFP denial.
- The OS container is ephemeral. No UAC, global WFP/Defender rule, registry
  change, AppContainer profile persistence, data transfer, PHI, installer,
  package publication, or clinical use. Test SDK and binary stored only
  in disposable developer scratch; no MXC package is added to D1 product
  dependencies.

### Re-run on an authorized compatible Windows 11 developer host

The test sources are independent from the production executable. Run in
`experiments/desktop-d1-tauri/tests` with supported Windows/Rust, and a
separate expendable scratch location. The normal Windows command shell is
used only to run this local experiment.

```powershell
npm install --no-save --no-package-lock --no-audit --no-fund @microsoft/mxc-sdk@1.0.1
$env:MEDORIGIN_MXC_TEST_TMP = 'D:\\YourDisposableScratchDirectory'
node windows-mxc-processcontainer-network-negative.mjs
node --test windows-mxc-policy-contract.test.mjs
```

The harness compiles the exact test-only Rust source in a temporary directory,
verifies unconfined loopback success, runs the child once inside native MXC,
checks **both** explicit Windows `WSA10013` denials and an exit0 sentinel,
then removes that temporary compiled executable and directory even on failure.
The developer should remove any task-owned `node_modules` after validation.
GitHub hosted CI performs *source-only* Rust compilation/formatting and Node
syntactic/static policy gates. It does NOT claim interactive Win32 or native
WFP runtime proof on the hosted runner.

### Critical distinction — Issue #662 remains OPEN / NO-GO

**This is NOT an egress test of the D1 Tauri application or its real
WebView2 descendants.** MXC as configured above disables GUI; actual
D1 UI requires separately reviewed `ui.disable=false` with appropriate
least-privilege window/IPC permissions and cold-start/interaction tests.
WebView2 may fail to initialize under restricted AppContainer filesystem
ACLs and multi-process constraints. A future D1 evaluation must prove real
fixture verification, native IPC, all spawned process containment, and
both IPv4/IPv6 TCP+UDP/DNS-denial evidence under a verified enforcing MXC
policy. It must NOT grant broad `internetClient`, open host networking,
weaken WFP filters to make the UI work, or silently fall back to unsandboxed
execution. Windows 26H2 build support is not blanket approval for older
Windows versions; probe every target host and fail closed if unavailable.

No D1 code or release policy is modified here. There is no signed/packaged
MedOrigin WFP launch integration, no independent review #603, no approved
desktop architecture substitution, no package/installer and no publication.
All existing developer/clinical NO-GOs and protected-main rules remain.

## Native MXC IPv4/IPv6 TCP/UDP matrix — partial evidence, **NO-GO** (2026-10-31)

The isolated, synthetic-only `tests/windows-mxc-protocol-matrix-{probe.rs,negative.mjs,contract.test.mjs}` experiment is a deliberately **failing** negative for the unqualified UDP API surface. It is a child of the earlier IPv4/TCP-only #760 proof, and it must not be substituted for the actual D1 Tauri/WebView2 descendant tree.

On the authorized Windows 11 26H2 (build 26300.9818) non-admin host, native Rust 1.97.1 and Microsoft MXC SDK 1.0.1 were used **only in disposable D: scratch**. The exact same compiled Rust executable ran an unrestricted positive control: real local IPv4/IPv6 TCP listeners accepted both connections and real local IPv4/IPv6 UDP listeners each received one synthetic datagram. The contained executable then used explicit deny-by-default ingress, egress and host-loopback policy, without adding any global firewall rule or privileged capability.

Observed in the OS-contained binary: `TCP4_LOOPBACK`, `TCP6_LOOPBACK`, `TCP4_TEST_NET`, `TCP6_DOC_NET` all returned **WSA10013**. But `UDP4_LOOPBACK`, `UDP6_LOOPBACK`, `UDP4_TEST_NET`, and `UDP6_DOC_NET` each returned **SENT23** from the WinSock send API. The independently listening local UDP receiver observed **zero additional contained UDP datagrams** on both loopback families during a bounded post-run observation. **Successful UDP send API return is not a delivery proof, and lack of local reception does not prove remote UDP/DNS egress is denied**; no packet/ETW trace or remote receiver exists for these observations. This distinction is why the runtime exits deliberately **1 / D1_MXC_PROTOCOL_MATRIX_NO_GO**, rather than producing any all-protocol pass.

The extra hosted Windows workflow compiles/format-checks the native source and checks the fail-closed JavaScript policy. Hosted CI **never runs native MXC** and cannot prove OS-enforced WFP or real GUI/WebView2 behavior. To clear #662, an application-scoped process-container trial must launch the actual native GUI/WebView2 descendant tree and attest real IPv4/IPv6 TCP + UDP/DNS delivery at a separate observer, with no privileged/global policy changes or unsandboxed fallback. **Keep D1 NO-GO**. No publication, tags, distribution, PHI, production dependency or protected-main merge.

## D1 real native MXC Tauri/WebView2 GUI — bounded nonpublishing Windows evidence (2026-10-31)

**Experimental, NOT a release gate pass.** This separate child of Draft #761 introduces read-only/source-controlled `tests/windows-mxc-d1-real-app-qualification.mjs`, `tests/windows-mxc-d1-real-uia-qualification.ps1`, seven source guard tests and an isolated, source-only Windows CI workflow. It adds no SDK or production dependencies and changes no D1 product source, packaging config, publisher, frozen root research, installer or protected main.

**Real on-host run (not simulated UI):** On authorized Windows 11 26H2 26300.9818 as a non-admin user, a source-built D1 debug executable already present from its parent #760 source checkout was matched by exact file SHA-256 `33348C40676924071F13EE7B36869715435B859FAD0805743DCF1A63450689ED`. A transient local `@microsoft/mxc-sdk@1.0.1` SDK was installed only in scratch on D:. The actual native Tauri + WebView2 application launched through MXC ProcessContainer with `ui.disable=false`, `ui.isolation='container'`, explicit `egress.default='deny'`, `ingress.default='deny'`, `hostLoopback='deny'`, one readonly executable, task-owned write scratch, and no remote network capability or host firewall rule.

An **independent host Windows UI Automation observer** located the exact executable and visible window, interacted via toggle/invoke with **all four fictional synthetic fixtures**, and verified actual React → Rust IPC SHA-256 outputs and the reference-match status: **4/4 PASS**. The independently enumerated root/descendant tree contained **8 processes, 6 genuine `msedgewebview2.exe` children**, and a point-in-time **0 owned TCP / 0 owned UDP endpoints**. A follow-up improved observer used **12 separate live process-tree + TCP/UDP endpoint samples**, rechecked the exact original root PID/path, required real WebView2 descendants each sample, and returned `MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12 max_owned_tcp=0 max_udp_endpoints=0 NO_PACKET_LEVEL_ATTESTATION`. MXC's execution result had zero warnings, and the native GUI intentionally remained alive until the bounded test timebox.

**Critical limits:** Matching binary SHA alone is not a reproducible compiler attestation or an independent signature; no packet-level/ETW capture, remote UDP receiver, DNS trace, cold-start/restart, full child ProcessContainer token identity, production packaging, signed installer or independent security approval was performed. TCP snapshots and UDP endpoint inventories cannot prove absence of all transient network packets or DNS. The prior UDP `send_to` success ambiguity in #761 remains unresolved and no contradictory zero-egress claim is made. Actual real D1 app containment of all descendants is **promising**, not certified complete. Issue #662 remains **OPEN / D1 NETWORK NO-GO**; publication remains forbidden. Additional blockers #622, #603, #574, #673 and #676 are separate and cannot be waived by this UI test.

Hosted CI compiles **no product application** and executes **no native MXC, WFP, UIA or WebView2**: it only syntax-checks JavaScript, parses PowerShell and runs source guard tests. Host results must not be described as hosted CI. No PHI, remote targets, production traffic, tags, publication or clinical use.

## D1 native MXC captureDenials diagnostic — blocked but NO-GO (2026-10-31)

A new isolated, synthetic-only Windows MXC 1.0.1 test probes `processContainer.captureDenials` **strictly in `mode: "block"`**, `retainEtl:false`, `network.egress.default:"deny"`, `network.ingress.default:"deny"`, `hostLoopback:"deny"`. It does not relax permissions, add a proxy, change any system-wide firewall, install product dependencies or launch real clinical data. Runtime dependencies are transient, outside tracked source. It compiles and runs the **same native Rust TCP probe** already used in Draft #760, with a positive unconfined localhost listener and documentation-only reserved remote address.

**Observed actual authorized Windows 11 26H2 26300.9818 non-admin run:** `getPlatformSupport().isSupported=true`, backend `base-container`, explicit `captureDenials:{mode:"block",outputPath:<task-owned output/denials.json>,retainEtl:false}`; WinSock inside the container returned **WSA10013 for both synthetic TCP sockets** and native child exit0, `warnings:[]`. However **no JSON denial report was created at the output directory**. The experiment correctly exits **1 with `MXC_CAPTURE_NO_GO: no denial JSON generated`** rather than reporting trace or WFP attestation. An SDK 1.0.1 call accepting capture settings is NOT proof that a diagnostic trace was produced. That observation neither disproves ordinary OS-enforced TCP rejection nor certifies recorded WFP decisions. The new source-level verifier requires an actual nonempty, well-formed report and explicit WSAEACCES before reporting even a *diagnostic* report, and that hypothetical positive is explicitly labeled **not WFP or packet-level attestation**.

Microsoft's documentation says denial-capture availability depends on OS PSEC/V2 trace support and may use a guarded fallback; the supported feature set must be tested on each actual host. The experiment does not use capture mode `allow`, retains no ETL and forbids silent fallback or zero-egress claims. No interpretation of an absent denial report, no automatic SDK grant expansion, and no production integration are allowed. The attached hosted Windows CI tests only JavaScript syntax and seven fail-closed policy contracts; it never executes MXC or WFP. For issue #662, follow-up requires independently verifying actual D1/WebView2 descendant-specific WFP/packet and DNS/UDP denial through an authorized observation route, real cold-start/restart/shutdown qualification and security review. **D1 NO-GO; all release decisions remain blocked.**
