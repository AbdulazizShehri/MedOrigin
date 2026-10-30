# D1 WebView2 network boundary — adversarial threat model (developer experiment)

**Decision: D1_NETWORK_ISOLATION_NO_GO.** Evidence class: synthetic-only Windows development. This is a design and source-claim control, **not OS-enforced isolation**, a product feature, a packet capture, a clinical security review, or authorization to ship. Owner decision #662 is authoritative. The machine-readable counterpart is `experiments/desktop-d1-tauri/security/network-boundary.json`, tested with `python scripts/verify_d1_network_boundary.py`. A PASS means *claims remain appropriately unqualified*, **never** that D1 is network-safe.

## Verified observations and boundaries

The unreleased Tauri/React D1 preview has no application network/updater/opener/shell/filesystem plugins, a local IPC CSP, and fixed in-memory fictional fixtures. Its Rust `preview_status()` reports `webview_runtime_egress_qualified=false` and `release_authorized=false`. Windows process-tree observations recorded in [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662) nevertheless found **2–3 established external TCP sockets from WebView2 descendants**, including 443. `--disable-background-networking` did not eliminate those observed sockets. The developer-only MXC sandbox bound a separate invocation and tested direct TCP denial plus 4 synthetic UIA/IPC journeys, but **was not installed as an app-scoped production policy**.

Microsoft describes the WebView2 multi-process architecture, its use by unrelated applications, and its runtime/user-data-folder process grouping:
- [WebView2 process model](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/process-model)
- [WebView2 end-user FAQ](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/end-user-faq)
- [Browser flags as diagnostic/development controls](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/webview-features-flags)
- [Security-tool integration / preserve runtime permissions](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/measures)

These documents do **not** establish that any browser flag, CSP, shared-executable firewall rule, or app developer sandbox can enforce a production MedOrigin network boundary.

## Adversarial threat and evidence matrix

| Surface | Possible outbound path / failure | Existing evidence | Required before app-level GO |
| --- | --- | --- | --- |
| React/Tauri application requests | fetch, links, updater, plugin permissions, remote assets | no network plugin / local CSP; source tests | adversarial network hooks and OS enforcement, including permission expansion |
| Rust commands and local IPC | arbitrary URLs/paths, Python subprocess, loopback proxy | 4 fixed in-memory SHA fixtures, no shell | IPC success inside the SAME OS-enforced denied process tree, include negative commands |
| WebView2 browser and children | background update, media/component requests, utility/network service, orphan processes | external TCP/443 **observed** in ordinary launch | enforce deny for this app's exact browser/child identities; capture packets or equivalent OS deny receipts |
| Short-lived TCP / UDP / DNS / proxy | traffic between socket polls, IPv6, proxy/system-service attribution | socket snapshots only; do **not** prove no egress | packet-level or equivalent enforce-and-prove across both IP families and transports |
| Windows system and WebView2 updates | runtime servicing performed by other services | no payload capture, attribution not proved | explicitly identify permitted system boundary without disabling essential OS/browser updates |
| Lifecycle and distribution | cold start, steady-state, restart, shutdown, upgrade, rollback, installer | no published installer, no signed release | repeat cross-phase denied traffic / IPC / rollback on exact signed binaries, reject unexpected child or policy loss |

## Candidate architectures — *research options, not accepted fixes*

1. **Application-scoped Windows filtering** (e.g. a reviewed Windows Filtering Platform / token / app identity design). Must be demonstrably limited to MedOrigin and all its WebView2 child processes; a path rule targeting the shared `msedgewebview2.exe` is **not acceptable**. Document privilege, installation, cleanup, tamper, service/update behavior and the identity binding of each child. No such implementation is currently qualified.
2. **An explicit, independent OS process/container boundary** where the WebView2 browser process actually inherits network denial and local Tauri IPC continues functioning; requires a supported deployment path, failure-state validation and a precise child identity audit. The free MXC developer invocation is useful research evidence but not application packaging.
3. **A separate native, non-WebView desktop architecture** could remove WebView2 itself but cannot be considered release-ready while #673 (transitive maintenance) and #676 (macOS accessibility) remain open. It also requires independent networking, supply-chain, UX and signing tests.

## Non-negotiable fail-closed qualification

- Keep the source `release_authorized=false`, `webview_runtime_egress_qualified=false`, packaging disabled, core-only Tauri capabilities, prominent visible warning, and machine-readable NO-GO until independent acceptance.
- A clean **socket snapshot** is a *sampled negative observation*, not zero egress. No checker may upgrade this to OS-level proof; an actual OS enforcement receipt must be bound to the exact binary, process tree, environment and time window.
- Refuse any policy or test that requires a **machine-wide** block on shared Edge/WebView2 executables, disables WebView2 or Windows security updates, silently changes global firewall/services, or loosens IPC without evidence.
- Before any public tag, installer or clinical use: independent #603 source-to-artifact review, version/authority #574, optional-dependency risk #622, Rust and macOS parity #673/#676, and separate explicit authorization are still required.

The source-only gate deliberately returns **`D1_SOURCE_CONTRACT_PASS_NO_NETWORK_ISOLATION_PROOF`** followed by **`D1_NETWORK_ISOLATION_NO_GO`** when the code remains correctly cautious. This is *not* an approval code. If any future source configuration asserts safety or allows bundling without this process being replaced by an independently reviewed OS-enforced design, the script fails closed.


## Win32 App Isolation fallback: concrete read-only preflight

Microsoft [Win32 App Isolation release notes](https://learn.microsoft.com/en-us/windows/win32/secauthz/app-isolation-release-notes) explicitly state that packaged applications **fall back to FullTrust** on unsupported operating systems. The [overview](https://learn.microsoft.com/en-us/windows/win32/secauthz/app-isolation-overview) lists Windows 11 24H2 / build 26100 as the minimum and labels the feature **preview**. Do not infer actual process isolation from a manifest or installer checkbox. Microsoft also documents the distinction between Medium IL and AppContainer apps in its [package capability guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/app-capability-declarations).

A new, completely **read-only** feasibility preflight lives at **experiments/desktop-d1-tauri/tests/windows-d1-appcontainer-preflight.ps1**. It accepts the exact already running synthetic-only D1 root PID and expected executable path, checks Windows build number and root path identity, discovers the process tree twice to reject observed process churn, and calls the documented [GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation) / TokenIsAppContainer Win32 token API through .NET P/Invoke for the root and descendants. It fails closed if any observed process lacks AppContainer, no WebView2 child appears, token access fails, or the operating system is below the published minimum. No firewall changes, network calls, installer, process launch, injected DLLs, account changes, OS updates, or WebView2 ACL changes occur.

On an authorized Windows desktop, while the synthetic D1 binary is **already running**, run:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/desktop-d1-tauri/tests/windows-d1-appcontainer-preflight.ps1 -RootPid 12345 -ExpectedExePath 'D:\path\to\medorigin-desktop-d1-preview.exe'
~~~

- Exit **2** = observed FullTrust/unsupported/missing child/identity mismatch, NO-GO.
- Exit **1** = inconclusive token or process inspection, NO-GO.
- Exit **0** only with marker **D1_TOKEN_PRECHECK_ONLY_NETWORK_ISOLATION_NO_GO**: all *observed* tokens marked AppContainer in one bounded snapshot. This is **not GO**, not proof of denied internetClient, no guarantee against PID reuse/reparenting, DNS/UDP or OS services, and cannot remove the D1_NETWORK_ISOLATION_NO_GO marker. AppContainer may itself be granted outbound network capabilities. Require independently verified token capabilities, OS-bound policy and actual attempted/packet traffic checks through cold start, run, restart and shutdown.

The preflight's **-SelfTest** mode uses 8 synthetic scenarios without querying the host. A dedicated GitHub Windows job parses the source, runs the 8 cases, and verifies that an ordinary unrelated test-runner process is **not** qualified. This is not testing MedOrigin's actual D1 WebView2 process tree or real network isolation.

Microsoft's [WebView2 process model](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/process-model) shows that browser/renderer/helper processes change over time, and a shared user data folder can share a browser process across app instances. Microsoft [WebView2 security guidance](https://learn.microsoft.com/en-us/deployedge/webview2-security-tools) warns against modifying LowIL/AppContainer user-data-folder ACLs. A successful token snapshot would narrow feasibility only; it does not establish an enforceable long-lived app process group or that no unrelated apps share the runtime.
