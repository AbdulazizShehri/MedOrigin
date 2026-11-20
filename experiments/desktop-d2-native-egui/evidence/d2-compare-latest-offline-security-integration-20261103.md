# D2 JSON comparison + latest offline security integration — 2026-11-03

**Nonpublishing, private Draft PR #859 only. No protected main merge, installer, release, PHI, patient records, AI or clinical functionality.**

## Why integration was required

Original comparison branch `feat/medorigin-d2-fictional-compare-20261102-run11` at `5aaf289d698054a73db9de64efd5e7939f6c3d8d` had branched from the old parent `09afb839d65719159c1b0d93ac6062f69cf55aba` in Draft #858. Latest parent security/evidence fixes were at `a25dc5cc`, then two actual test/format regressions repaired on the parent to `d0226ee1b29657f8b14b851bebff8510f61ef13b`. Without integrating the parent, the comparison branch lacked the critical WSL WindowsInterop fail-closed gate and Linux zbus maintenance diagnostic.

The fresh integration used isolated Windows source worktree, fetched both **exact** branch heads, computed `git merge-base` and an independent `git merge-tree --write-tree` no-conflict check, and merged parent security into comparison without force-push, without changing Cargo.lock and without touching the protected main branch. Parent fixes were additionally merged when available.

## Actual merged-source validation on authorized Windows PC

- `cargo test --offline --locked --all-targets`: **14/14 PASS** (eight native Rust app tests including fictional side-by-side comparison and fail-closed cases; six browser/network source-boundary tests).
- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --offline --locked --all-targets -- -D warnings`: PASS.
- Windows Python 3.14 combined `unittest` suites: **24/24 PASS** (eleven offline evidence, eight exact AccessKit Linux graph, five WSL WindowsInterop boundary). The initial run failed **5/5 WSL tests** because Windows Python has no `os.uname` attribute. The tests were correctly repaired with `mock.patch.object(..., create=True)` on **parent #858** (commit `44d25f75`), re-merged, and the full Windows Python suite then passed. The actual Linux-only runtime probe remains WSL fail-closed.
- Source-controlled `windows-offline-powershell-ast-gate.ps1`: **4/4 PowerShell AST PASS**.
- `git diff --check` caught pre-existing trailing whitespace in a parent evidence Markdown file. Parent `d0226ee1` removed it; the fix was re-merged, and `git diff --check` PASS.
- `cargo build --offline --locked` for actual merged-source Windows native GUI: PASS. Test-only, unsigned executable SHA-256 **`CA9A1D2960F273C522C274B01EB3116236B7C0682B295A398B88484D13B2231D`**.
- **Real native Windows UIAutomation** with source-controlled `tests/windows-native-fictional-compare-uia.ps1` on that **same hash-pinned real executable**:
  - `D2_COMPARE_TWO_REAL_UIA_PASS`: independently verified fictional Patient and Observation raw JSON appear together with their exact SHA-256;
  - `D2_COMPARE_SAME_FIXTURE_REFUSAL_PASS`: same fixture on both sides refuses and prior second text clears;
  - `D2_COMPARE_STALE_CLEAR_PASS`: verifying a fixture clears previous comparison, no stale display.
  - Final marker **`D2_COMPARE_WINDOWS_UIA_3_OF_3_PASS_NONPUBLISHING`**, exit 0. Script cleans only the application process it launched.

## Additional actual Windows GUI regression on the identical native binary

All four source-controlled interactive UIAutomation scripts were run on **the same exact SHA-256-pinned debug executable** `CA9A1D2960F273C522C274B01EB3116236B7C0682B295A398B88484D13B2231D`, not a simulation or earlier build:

- `windows-native-fictional-compare-uia.ps1`: **3/3 PASS**, exit 0 (as above).
- `windows-native-fhir-uia-qualification.ps1`: **8/8 PASS**, independently rerun via a separate PowerShell process with verified exit 0: Observation minimal, invalid subject, Bundle valid, bad reference, duplicate, wrong type, linked, dangling.
- `windows-native-json-preview-uia.ps1`: **3/3 PASS**, exit 0: Patient raw exact source, invalid UTF-8 refusal, Bundle raw source.
- `windows-native-uia-smoke.ps1`: **4/4 PASS**, exit 0: Patient minimal and three synthetic boundary cases.

**Total: 18/18 actual Windows UIAutomation cases passed against this one merged-source executable** (3 compare + 8 advanced + 3 raw preview + 4 original Patient). One *temporary orchestration wrapper* initially produced a false failure AFTER all eight FHIR markers because it read a stale PowerShell `$LASTEXITCODE` from a prior external command; the FHIR script itself was independently rerun via `powershell -File` and reported **8/8 PASS, process exit 0**. The wrapper was test-only scratch, never committed as a qualification tool. It must not be confused with a product failure or an OS packet-confinement PASS.

## Remaining strict NO-GO

This verifies source integration, synthetic-only comparison correctness and Windows interactive UIA. It does **not** authorize offline network containment, real patient record handling, external EHR/FHIR interoperability, package/release, macOS spoken VoiceOver, Linux OS-level distribution, full OS packet/WFP/DNS attribution, or independent security review. **Issue #662 D1 WebView2 outbound TCP remains open, issue #673 zbus5 transitive maintenance remains open, issue #676 macOS spoken VoiceOver remains open, issues #622/#603/#574 also open.** In particular, WSL TCP/UDP direct socket negatives were superseded by the demonstrated WindowsInterop broker escape; WSL is rejected early by the integrated offline probe. No exact-head hosted GitHub Actions CI success is asserted; zero-cost private local tests were used and commits carry `[skip ci]`.

The merged source and this evidence are preserved in GitHub; disposable local build worktree is only scratch and must be removed after push and verification.
