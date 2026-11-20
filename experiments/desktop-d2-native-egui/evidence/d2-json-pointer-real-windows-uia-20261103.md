# D2 fictional JSON Pointer — real Windows UIA qualification (2026-11-03)

**Scope:** private, synthetic-only, nonpublishing; no clinical data, EHR, model, external files, or release authorization.

- Exact tested D2 source parent: 8cfeb954faf706d1af4926e7c9ebfa2901f29472 (Draft PR #862). This task adds a source-controlled UIA acceptance script and evidence only, not production Rust changes.
- Authorized real Windows host, native Rust eframe 0.36 application, no WebView2/Tauri browser.
- Native executable SHA-256: F53712A7AEA0FC0FF2133FAB1D879467908CA0DEE47DB3102771C5122186497C.
- cargo test --offline --locked --all-targets: D2 app **12/12 PASS**, browser/network source-boundary **6/6 PASS**.
- cargo clippy --offline --locked --all-targets -- -D warnings: **PASS**.
- cargo build --offline --locked: **PASS**.
- PowerShell AST parse of tests/windows-native-fictional-json-pointer-uia.ps1: **PASS**.
- Real native UIAutomation (pinned executable, actual process/window, Invoke/Toggle controls, exact accessible text nodes) **3/3 PASS**, exit 0:
  1. D2_JSON_POINTER_REAL_UIA_PASS: Patient versus Observation displays the exact fictional /id (value differs) structural pointer, alongside verified original JSON, digests, byte/HEX summaries.
  2. D2_JSON_POINTER_SAME_FIXTURE_REFUSAL_PASS: choosing identical fixtures refuses comparison and clears the pointer and prior source.
  3. D2_JSON_POINTER_STALE_CLEAR_PASS: re-verification clears the old pointer and comparison.
- The UIA test derives the fictional Patient and Observation raw bytes from the pinned D0 Rust source and verifies the existing source/digest/HEX receipt, rather than replacing a native GUI with a mock.
- No GitHub hosted private CI was started for this new commit because free-minute budget is unverified; **no exact-head hosted CI PASS is claimed**.

**Hard NO-GO unchanged:** #574 governance/signing/publication, #603 independent human security review, #622 optional frozen research advisories, #662 Windows D1 WebView2 packet/DNS/TCP/UDP isolation, #673 Linux AccessKit/zbus5 maintenance, #676 spoken macOS VoiceOver and independent accessibility acceptance. Real Windows UIA is not an OS packet observer, Linux/macOS qualification, or clinical FHIR R4 validation.

**Additional caution:** parallel Draft #858 documents a real WSL WindowsInterop process escape from route-less Linux netns; its WSL-specific refusal is separate and does not prove cross-platform zero egress. This test does not change WSL or Windows firewall/WFP/ETW/auditpol/pktmon.
