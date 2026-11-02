# D1 native hash and envelope receipt runtime validation (NO RELEASE)

Date: 2026-11-02 Asia/Riyadh. Only fixed fictional FHIR-shaped fixtures; no PHI or external destinations.

## Exact source lineage and test-first finding

- Parent stacked Draft #841 head: `9574826685ea0427ad16e33a3a1fc4f41e0e70c3`.
- New regression-only RED commit: `25f108ba1b0d61982cbc9e8f665105aac56b3b60`.
- Product/UI fix GREEN commit: `314b9b88b742a676049973a51b6246a8009358df`.
- This evidence report is a subsequent docs-only commit. The final PR head must be checked separately.

The React bridge previously used TypeScript `invoke<T>` as though it were runtime validation. A mocked hash response with correct golden digest and **unexpected** `webview_runtime_egress_qualified: true`, or `synthetic_only: "true"`, could still produce a success indicator. A similarly forged structural envelope could also produce success. These are misleading UI integrity/capability assertions, not proof of an actual compromised Tauri backend, exploit, or OS egress.

Test-first real Microsoft Edge on authorized nonadmin Windows (Node 24.19.0, Python 3.14.7, Playwright 1.64.1) ran seven browser tests on the unchanged product UI with newly added malicious IPC fixtures: **5 intentional subtest failures** (hash extra/missing/type and envelope extra/type), 2 new test methods, browser test exit 1. The missing hash case failed the test-only per-run call counter because it was not reset after the previous failing subtest; the counter was corrected in the RED test commit. The extra and wrong-type cases are the actual UI acceptance bugs. Two inherited tests plus the other test cases passed. This is a test-only simulated Tauri IPC bridge; the server binds ephemeral 127.0.0.1 and browser nonlocal requests are blocked.

## Actual fix and local verification

- The React frontend now accepts native hash receipts only with the **six exact own JSON fields**, expected fixture, byte count, contract, strictly lowercase 64-hex digest, and boolean `synthetic_only === true`, `release_authorized === false`.
- Structural FHIR-shaped envelope receipts require the **seven exact own JSON fields**, exact fixture, byte count, expected fictional status, expected contract, and strictly false clinical/release flags.
- Unexpected/missing/extra/wrong-type fields reject the whole receipt before rendering success. The inherited raw SHA mismatch still displays a visible mismatch and never invokes structural inspection.
- On GREEN code SHA `314b9b88b742a676049973a51b6246a8009358df`: locked npm TypeScript/Vite build PASS; Node source contract **3/3 PASS**; actual Edge simulated IPC **7/7 PASS** (including six forged receipt variants, inherited bundle cases and bridge-status negatives); `git diff --check` PASS.
- No Rust native production code, frozen Python research root/lock, OS firewall, WFP/ETW policy, publication workflow or protected main modified.

## Nonpublishing limits

These browser tests do **not** launch actual Tauri/WebView2, authenticate an independent OS process, verify WFP/ETW DNS/IPv4/IPv6 TCP/UDP packet denial, or qualify a general FHIR R4 implementation. The positive controls are fixed fictional bytes only. Author-side CI does not count as independent human security review. Keep #662, #622, #673, #676, #603 and #574 OPEN / release NO-GO; all PRs Draft and unmerged.
