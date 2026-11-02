# D1 native preview-status handshake: fail-closed UI qualification

Date: 2026-11-02 Asia/Riyadh. Nonpublishing, synthetic-only experiment.

## Exact source lineage

- Parent Draft #840: `0997e713941f90cb2ede7366521d20b3ac153224`.
- Test-first RED commit: `456cbb5cf38cbca048678cf7d8648ebcdd82187c`.
- Product UI fix GREEN code commit: `0a969d2fbace36e188fd49033b23406edd5d3be1`.
- This report is a subsequent evidence-only commit; verify the final PR HEAD separately.

## Actual regression and change

Previously, the React preview accepted *any* resolved `preview_status` response as proof that the native bridge was ready. A mocked response claiming `release_authorized=true`, claiming `webview_runtime_egress_qualified=true`, or omitting `app_network_plugins_enabled` enabled the Verify button and displayed the bridge-active footer. This is a misleading UI capability assertion, not a demonstrated privilege escalation or real WebView2 network escape.

The D1 React UI now checks the exact six-field, synthetic-only, unreleased status contract before enabling verification. A missing, extra, wrong-type, or contradictory field fails closed with a visible refusal and disabled Verify button. The native Rust status response is unchanged and matches the pinned values.

## Windows test-first evidence

Authorized non-admin Windows PC, Node 24.19.0, Python 3.14.7, Playwright 1.64.1, installed Microsoft Edge. No external HTTP; the browser test server binds ephemeral 127.0.0.1 and rejects nonlocal browser requests.

- RED on the unchanged React source with the new mocked-IPC browser regression: 5 browser tests executed, 3 intentional failures (`release`, `egress`, `missing` status variants). Each failure showed Verify was incorrectly enabled. Two inherited tests passed. Exit code 1.
- GREEN on the fix code: `npm ci --no-audit --no-fund` and `npm run build` (TypeScript + Vite) PASS; Node source contract 3/3 PASS; real Microsoft Edge with simulated Tauri IPC 5/5 PASS, including all three startup forgery variants and inherited FHIR/Bundle/forged-envelope/hash-negative cases. Exit code 0.
- `git diff --check` PASS. The committed Rust native `preview_status` fields were inspected and agree with the strict UI contract.

## Truthful limits and release decision

These browser tests use a **test-only simulated Tauri bridge**, not a native Tauri/WebView2 launch or an OS packet capture. No actual WFP/ETW egress denial, DNS/IPv4/IPv6 UDP/TCP containment, native process identity, signing, independent security review, general FHIR R4 conformance, or release authorization is established. No patient data, external service, privileged host policy change, installer, tag, package upload, or protected-main merge was used.

Keep issues #662, #622, #673, #676, #603, and #574 OPEN / release NO-GO. All work remains in a stacked Draft PR.
