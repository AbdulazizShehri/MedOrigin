# MedOrigin Desktop D1 — synthetic-only local Tauri preview

**Status: experimental / unpublished / not reviewed for release.** This standalone Tauri 2 + React/TypeScript app is a *consumer* of the sibling isolated Rust D0 fixture-hash crate. It is not a clinician-facing product, a distributable installer, or a replacement for the Python Research Core.

## What is implemented

- One fixed local window, visibly marked **SYNTHETIC / DEVELOPER PREVIEW**.
- Exactly two native commands: `preview_status` and `hash_fixture`.
- Four *fictional, static in-memory* samples with source-bound SHA-256 golden digests. UI accepts only an enumerated fixture ID; Rust validates it again and enforces a byte cap.
- No application HTTP server in the compiled preview, opener/shell/filesystem/updater plugin, remote assets, application telemetry, model weights, Python worker, application network permission, patient records or EHR interaction. Vite's localhost server is **development-only**. **WebView2 itself may contact external services** even when the app has no network plugin; this is not yet an offline/zero-egress-qualified runtime.
- Tauri capability permits core window functionality only; CSP restricts application fetch to local Tauri IPC, **not WebView2's own background network traffic**. Packaging is disabled (`bundle.active=false`), and the app version is intentionally `0.0.0`.
- Rust errors are stable non-sensitive codes. No user-controlled path, URL or file contents enters the command.
- Frontend validation now fails closed on unexpected native preview safety flags or a fixture hash response with mismatched ID, contract, digest, payload byte count or release flags. The dependency-free Node test validates all four fixed vectors and adversarial responses; it does not establish runtime network isolation, clinical validation or release readiness.

## Local developer qualification (free tooling)

```powershell
cd experiments/desktop-d1-tauri
npm ci --no-audit --no-fund
npm run build
node --experimental-strip-types --test tests/nativeContract.test.mjs
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

The UI Automation smoke test verifies all four fictional fixture IDs through **React → Tauri IPC → Rust → React** and checks exact SHA-256 goldens. The invalid-encoding and oversize samples are *expected to hash successfully*; this does **not** mean they pass FHIR validation. The egress audit inspects the root process and descendant WebView2 processes; it exits 2 on any observed non-loopback TCP state (including `SynSent`) **or any UDP endpoint owned by those processes**, and fails closed if process/socket enumeration fails. UDP endpoint existence alone does not prove packets were sent or that traffic was external; rejecting it is a conservative *qualification* gate. Its separate `tests/windows-egress-probe-selftest.ps1` uses eight mocked scenarios, including root and child UDP endpoints, external-attempt rejection, enumeration-error rejection, and TCP loopback allowance; it does **not** exercise the actual OS network boundary. A clean snapshot is **not** proof of zero network activity.

**Observed security NO-GO on Windows, 2026-10-29:** With the local D1 debug preview running, `msedgewebview2.exe` descendants established **external IPv6 TCP port 443** connections (two to three in repeated snapshots). The same problem persisted with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS='--disable-background-networking --disable-component-update'`. This is a runtime observation, not proof of what content was sent or whether the app initiated the traffic. Do **not** claim the desktop is zero-egress/offline-isolated, or allow PHI, release, or clinical use. Any future resolution requires a separately reviewed, application-scoped OS isolation policy and packet-level verification; do not disable system-wide WebView2 security updates or firewall other applications.

## Optional disconnected Windows Sandbox rehearsal (NOT app-level zero-egress qualification)

Windows Sandbox is an optional, disposable **test environment**, not the application isolation mechanism for an installed MedOrigin desktop. Its availability depends on Windows edition, virtualization, and enabled Windows Sandbox prerequisites; do not silently enable OS features.

After building the **synthetic-only local debug executable** (no installer), record its SHA-256 digest and compare that digest against an **independently approved build receipt**. A digest computed from an arbitrary downloaded executable does not establish its authenticity. The generator requires the caller-pinned 64-hex-character digest before creating the mapped directory; a mismatch fails before staging. Then generate a profile from that approved local executable on a Windows host:

```powershell
$exe = 'D:\MedOrigin-D1-target\debug\medorigin-desktop-d1-preview.exe'
$approvedSha256 = '<paste-reviewed-64-character-SHA256-digest>' # Must match independently reviewed build receipt
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/windows-offline-sandbox-profile.ps1 `
  -ExePath $exe `
  -ExpectedSha256 $approvedSha256 `
  -OutputDirectory "$env:TEMP\medorigin-d1-sandbox-rehearsal"
```

The output directory must **not** already exist, and its parent must exist. The generator verifies the binary against the **caller-pinned** SHA-256 before creating the output directory, then checks the staged copy against the same digest; its receipt prints `D1_SOURCE_SHA256`. This prevents accidental staging of an incorrectly named or different executable, but is not a substitute for binary signature/provenance verification. In addition to requiring absolute drive-rooted paths, the generator now rejects drives that Windows reports as anything other than **Fixed** (such as mapped network or removable drives) *before* reading or copying the executable. A fixed drive may still contain reparse-point ancestors and paths can race; this guard is not proof of a hermetic filesystem. Inspect `medorigin-synthetic-offline.wsb` before manually opening it with Windows Sandbox. The generated profile disables Sandbox networking, clipboard, redirection, microphone, vGPU, and printer; enables Protected Client; maps **only a SHA-256-verified copy of the one synthetic preview executable** read-only. It never automatically starts the executable or changes host firewall rules. Inside Sandbox, open `C:\MedOriginSyntheticOnly\medorigin-desktop-d1-preview.exe` manually, and run only fictional fixture checks. A separate WebView2 runtime may be unavailable in the clean Sandbox, which must be recorded as a failed/inconclusive rehearsal rather than bypassed.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/windows-offline-sandbox-profile-selftest.ps1
```

This source-only regression **does not launch Windows Sandbox** and cannot attest host runtime isolation. When finished, close Sandbox and remove the generated output directory **only after closing the mapped session**. Do not place sensitive files in the mapped directory. Windows Sandbox isolation does not prove that a normally installed MedOrigin app can prevent WebView2 background traffic; normal-host egress remains **NO-GO**, with no patient data, clinical use, publishing, release or installer authorization.

Reference: [Microsoft — Windows Sandbox configuration](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-configure-using-wsb-file).

## Known blocks

This independent D1 experiment must remain a **Draft** until a separately accepted topology/language decision (ADR-0003 + proposed ADR-0013), reviewed dependency locks/licenses/advisories, Windows/macOS/Linux app-level tests, verified zero network calls, IPC negative tests, WebView2 behavior, accessibility, process resource budgets and signed installer/uninstall lifecycle receipts. No release, tag, protected-main merge, PHI authorization or clinical-performance claim may be inferred from successful builds.
