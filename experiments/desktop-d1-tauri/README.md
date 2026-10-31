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
