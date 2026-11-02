# MedOrigin D1 fictional FHIR browser UI behavior — Edge E2E evidence

Date: 2026-11-02, Asia/Riyadh. Nonpublishing, synthetic-only, stacked over Draft #836, not a product/security approval.

## What actually ran locally

On the authorized Windows development PC, built the exact checked-out Vite/React source using npm ci --no-audit --no-fund and npm run build. A Python standard-library ThreadingHTTPServer serves only these generated static files on a random 127.0.0.1 port. The installed real Microsoft Edge browser (headless) navigates to that local port using Playwright 1.64.1. Requests to any nonlocal destination are intercepted and blocked and the test verifies that no such requests were attempted.

A test-only in-page replacement for window.__TAURI_INTERNALS__.invoke simulates the deterministic Rust command responses for six *fictional* fixtures. This deliberately **does not launch Tauri or WebView2**. Exact source tests and native Rust unit tests in parent #836 separately test actual command code and built-in fixture hashes.

Three real browser interaction tests all PASSED:
1. At 375px viewport, select the fictional valid Observation, verify via the visible button and see a narrow structural success result. Then select the broken fictional Observation reference and observe INVALID REFERENCE. Six sample buttons rendered.
2. Forge an Observation native envelope response with the wrong status after a matching hash. The UI must show a command refusal and must NOT display SHA MATCHES or a structural result.
3. Forge an incorrect SHA digest. The UI shows MISMATCH and never calls the structural command.

Local Python unittest output: Ran 3 tests in ~5 seconds, OK. A new source-exact GitHub-hosted Windows Edge job rebuilds the exact candidate and repeats these tests; its outcome must be checked at the exact PR head before calling CI green.

## Not an OS isolation test

The local HTTP loopback test server and Playwright route checks are test infrastructure only, **not** a Tauri runtime egress policy. Browser background traffic, host WebView2 broker/network descendants, DNS, WFP policy, IPv4/IPv6 and packet-level process attribution remain untested by this script. Issue #662/G3 BLOCKED, G4/G5 NOT_RUN, G7 BLOCKED. No PHI, patient/EHR data, public releases, installers, model execution, elevated firewall/ETW/WFP/pktmon changes or protected main merges. #574/#603/#622/#673/#676 remain separate release blockers.
