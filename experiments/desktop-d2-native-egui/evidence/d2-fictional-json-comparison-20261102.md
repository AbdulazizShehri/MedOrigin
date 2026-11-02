# D2 fictional JSON comparison — real Windows native qualification

Date: 2026-11-02 (Asia/Riyadh). Source lineage: stacked on D2 Draft #858
(09afb839d65719159c1b0d93ac6062f69cf55aba), itself on Draft #857.
**Private draft only. No release, tag, protected-main merge, patient data, or
clinical/full FHIR R4 assertion.**

## Product capability

- Two distinct source-compiled fictional JSON fixtures can be inspected
  side by side in native eframe, with independent D0 SHA-256, byte-length,
  allowlisted ID, limited envelope status and synthetic-only/no-release
  verification for **both** sides before rendering either text.
- Only nine source-fixed JSON cases of at most 2,048 bytes are eligible.
  Invalid UTF-8, 32,768-byte and 32,769-byte raw boundary fixtures refuse
  comparison. Same-ID and invalid-index requests fail closed.
- No file input/output, arbitrary path, clipboard, network, IPC, persistence,
  model call, clinical interpretation or JSON normalization is introduced.
- Changing fixture, verifying or inspecting the old preview clears a previous
  comparison. Expected negative envelope statuses remain negative test cases.
- A first Windows UIA RED probe exposed an accessibility problem: egui ComboBox
  appeared as ControlType.ComboBox but did **not** implement UIA
  ExpandCollapsePattern. The source was changed to the existing accessible
  selectable-button pattern in a collapsible section; the final GUI exercises
  it with genuine Windows UIAutomation Invoke/Toggle actions.

## Actual authorized Windows results

OS: authorized Windows PC via Desktop Commander.
Rust: 1.97.1 stable; locked D2 Cargo.lock unchanged.
Exact final native debug executable SHA-256:

`4175F008C6713F0F4EBA49F352B08AD4AEC5992161EA3AF4FD40E381F97D9A65`

Source-controlled, exact-SHA-pinned interactive UIA script:
`tests/windows-native-fictional-compare-uia.ps1`

- New real UIA: **3/3 PASS** — independent Patient/Observation raw JSON
  and exact SHA nodes, same-ID fail-closed refusal, stale comparison clearing.
- Existing real UIA: **3/3 PASS** raw JSON preview; **8/8 PASS** advanced
  fictional Observation/Bundle cases; **4/4 PASS** original Patient selectors.
- Rust D2 native: **8/8 PASS** app tests (including two new comparison tests),
  **6/6 PASS** browser/network source guards, 0 test failures.
- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --locked --all-targets -- -D warnings`: PASS.
- `cargo build --locked`: PASS; PowerShell AST parse: PASS.
- `git diff --check`: PASS; D0 and D2 Cargo.lock unchanged.

The initial combo-box experiment and UIA diagnostic script were not committed.
No native macOS or Linux GUI comparison acceptance was executed for this change;
prior platform tests apply only to their earlier exact source SHAs.
GitHub hosted CI is intentionally not claimed: private Actions billing usage
could not be verified via the authorized token, so no paid-minute risk was
deliberately introduced.

## Nonclosing NO-GO

#574 founder ADR/version/signing/publication approval, #603 independent human
security review, #622 frozen optional research advisories, #662 Windows D1
WebView2 OS packet egress, #673 Linux AccessKit zbus5 maintenance, and #676
spoken macOS VoiceOver/independent hardware acceptance remain open.
Source-only browser/network guards and successful native UIA are **not**
independent OS packet-level no-egress or clinical qualification.
