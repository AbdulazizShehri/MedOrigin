# D1 Windows WebView2 snapshot report consistency gate — 2026-11-03

**Decision: release NO-GO. This work validates the *integrity of evidence formatting and arithmetic*, not the truth of packet/OS measurements. It does not demonstrate that WebView2 stopped communicating externally.**

## Code and source-control scope

Private, unmerged Draft PR #661, branch `experiment/medorigin-desktop-d1-tauri-20261029`:
- `experiments/desktop-d1-tauri/tests/validate_d1_egress_series.py` — Python 3 standard library only, deterministic post-processor for a JSON report from the existing source-controlled Windows `windows-attributed-egress-lifecycle.ps1`. No network calls, application launch, Windows firewall mutation or patient data.
- `experiments/desktop-d1-tauri/tests/test_validate_d1_egress_series.py` — 17 synthetic adversarial consistency cases.
- `.github/workflows/desktop-d1-preview.yml` now parses three additional Windows D1 PowerShell scripts and, **on an eligible future CI run**, checks the 9 legacy mocked PowerShell cases, 14 pinned-identity mocked PowerShell cases and new 17-case Python consistency suite. **No hosted run at exact new HEAD is claimed**: private Draft #661 is stacked against the D0 experimental branch, and commits use `[skip ci]`.

## Actually run

In a separate non-Windows local sandbox, executed `python -m unittest -v test_validate_d1_egress_series.py` against the authored Python checker and its test data. **17/17 PASS**, zero network and zero application launches.

Scenarios: zero TCP still NO-GO; observed TCP still NO-GO; fake `release_authorized=true` refused; missing root shutdown refused; fabricated app launch refused; wrong executable SHA refused; missing sample; duplicate sample index; wrong summary maximum; hidden external TCP in purportedly clean sample; observed marker with impossible TCP count; negative UDP count; Boolean-as-integer count; unrecognized error marker; incomplete series; missing/invalid executable digest; CLI never returns zero (well-formed reports exit **2**; malformed JSON exits **4**). The test script is now saved alongside the checker for reproducible Windows/Linux future runs.

The standalone source checker requires `--input` and `--expected-sha256`; accepts at most 128 KiB of JSON; validates exact expected D1 schema, process launch, SHA-256, app-root stopped flag, strictly false release/isolation claims, ordered complete samples, nonnegative integer counters, total/external/established TCP relations, summary maxima and supported reason codes. The output **always** has `decision=NO_GO`, `release_authorized=false`, and `os_packet_egress_denial_proven=false`. If internal arithmetic is coherent it sets `internal_consistency_checked=true`, not a security pass; contradictions set that flag false. This post-processor **cannot independently check whether the reported Windows observations actually happened**.

## Why not run the actual D1 binary now

Remote Desktop Commander returned an explicit **monthly usage limit reached / device calls paused / do not retry or reconnect** message on the last actual Windows run. Its connected/online status does not lift that quota. Therefore the actual state of the previously started offline Windows Rust D1 build and the temporary worktree at `D:\MedOrigin-D1-RealEgress-20261103` remain **unverified**, as does cleanup. This change did **not** use Desktop Commander again or access the user's Windows filesystem.

The previous known actual Windows D1 WebView2 observation in issue #662 included external TCP/443 descendants. No new OS-enforced WFP, DNS, UDP or descendant-lifecycle negative-control proof has been produced. Source-only mock tests must NEVER be counted as real Windows egress measurements.

## Microsoft-sourced hard limits

- Microsoft `WebResourceRequested` customizes requests handled by WebView2 and can intercept page resource traffic; it is not equivalent to OS-enforced process-tree egress denial. Its virtual-host-mapping limitations are documented: https://learn.microsoft.com/en-us/microsoft-edge/webview2/how-to/webresourcerequested
- Microsoft documents WebView2's LowIL/AppContainer processes and warns against modifying default ACLs on user data folders in a way that breaks runtime sandboxing: https://learn.microsoft.com/en-us/deployedge/webview2-security-tools
- Microsoft advises against DLL injection and forcibly interfering with WebView2 renderer/GPU/network/Crashpad processes for general operation: https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/measures

Do not call browser resource interception, `--disable-background-networking`, a zero-socket snapshot, or simply shutting down the D1 app root a cross-process zero-egress proof. A separately authorized, app-scoped OS enforcement boundary with real packet/DNS observation, WebView2 descendant accounting (including shutdown), and independent security review is still needed; do not deploy global rules against shared `msedgewebview2.exe` or disable Windows/Edge updates.

**No protected main merge, PHI, clinical use, installer, signed or public release, tag or security-blocker closure.** Existing #662, #673, #676, #622, #603 and #574 remain release blockers.
