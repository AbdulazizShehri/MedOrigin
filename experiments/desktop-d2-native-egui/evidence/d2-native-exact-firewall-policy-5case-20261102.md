# D2 — actual native Windows Firewall policy preflight at exact pinned executable (2026-11-02)

**Result: engineering qualification PASS for preflight behavior; real OS network isolation NO-GO.** No protected `main` merge, publication, installer, patient data, cloud/API access, elevation or host firewall mutation.

## Exact reproducible source

- Source: `AbdulazizShehri/MedOrigin` stacked nonpublishing Draft #858. Detached/isolated Windows worktree based on `338a075754bf5b73de91cc231d102600ef46f2f3` (app source), then read-only policy script/QA updated through `1caf67e5387a236e21695506a23493fc2b6e5e40`.
- Windows kernel version: `10.0.26300.9818`; Rust toolchain `rustc 1.97.1`.
- Native D2 debug binary built using `cargo build --offline --locked`: **PASS**, and SHA-256 of that exact local file independently measured as **`C5CB3384F883A86D8F7D61D0F696F4B64C6BC9EC65F3B4828927192F2F20397A`**. This is not an installer or signed release artifact.
- App-source Rust tests at this exact lineage: `cargo test --offline --locked --all-targets`: **12/12 PASS** (6 native app tests, 6 no-browser/network-source-boundary tests). Other bin/example targets had no tests.

## Actual native executable policy query, not PowerShell reference-only

The source-controlled `tests/windows-firewall-policy-preflight.ps1` verifies exact file SHA and additionally now **refuses an executable whose basename is not** `medorigin-desktop-d2-native-egui.exe`. Earlier preflight could be invoked with an arbitrary accurately hashed program such as PowerShell; this allowed a misleading program-specific report (though never a release PASS). The new identity guard is commit `b8876215f614d0fc2b791a3bea58dedaea1e1652`.

Actual Windows `ActiveStore` inspection for the **real compiled D2 binary named above**, using its independently supplied SHA, produced:

```json
{"schema":"medorigin-windows-offline-firewall-preflight-v1","decision":"NO_GO","reason":"EXACT_FULL_SCOPE_BLOCK_RULE_NOT_FOUND","syntactic_full_scope_block_candidates":0,"release_authorized":false,"os_enforcement_proven":false,"dns_packet_egress_proven":false,"host_policy_modified":false}
```

Preflight command **exited nonzero** (host bridge reports remote exit code 1 for a PowerShell script that invokes `exit 2`; script's own refusal is `2`). This means no *syntactically matching broad outbound block rule* was identified in the currently readable Windows ActiveStore for this binary under these conservative filters. It does not prove whether *other effective policies* deny egress. No OS policy was created/changed.

## Actual Windows regression tests

Source-controlled `tests/windows-firewall-policy-preflight-qa.ps1` now supports `-NativeExecutable` and `-NativeSha256` (commit `1caf67e5`), and evaluates:
1. Wrong SHA for PowerShell control => **refused**
2. Nonexistent executable => **refused**
3. Correct PowerShell SHA but wrong application basename => **refused**
4. Wrong SHA for actual native MedOrigin binary => **refused**
5. Correct SHA and basename for actual native MedOrigin => real ActiveStore read returns explicit **NO_GO**; no false success.

All **5/5 PASS** on Windows; last marker `WINDOWS_POLICY_PREFLIGHT_5_OF_5_PASS_NONPUBLISHING`. An initial newly added QA script had a malformed regex string; it was caught by **actual Windows execution**, repaired at `1caf67e5`, and the five-case suite reran GREEN. Do not cite the prior malformed HEAD as passing.

## Decision and required next test

**NET-02 OS-enforced per-app denial is NOT QUALIFIED.** Read-only firewall rule enumeration is not a packet/WFP-level test. Current remote terminal is not elevated, so no administrative policy alterations or privileged packet capture were performed; test host has no confirmed disposable Windows Sandbox. The remaining essential work is a separately isolated/admin-authorized, disposable test host with application-scoped denial applied **before** launching D2, DNS/TCP/UDP attempt and packet-level negative controls, all-process descendant ownership and shutdown/crash/restart measurements plus independent sign-off. Do not disable global WebView2/Edge update services. D1 WebView2 #662 is separately blocked; D2 result cannot close it. #673 Linux unmaintained transitive `zbus 5`, #676 spoken accessibility, #622 optional extras, #603 independent review and #574 owner release remain blockers.

The evidence and tools are committed to GitHub. Disposable worktree and debug binary are developer QA only, not release artifacts.
