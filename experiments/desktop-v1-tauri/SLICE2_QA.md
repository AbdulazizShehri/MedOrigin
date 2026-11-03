# MedOrigin Desktop v1 — Slice 2: read-only fictional source viewer

**Continuation baseline:** Ink's `feat/medorigin-desktop-v1-20261103` at `01150181` (Nov 3, 2026, 20:51 Asia/Riyadh). All work developed in a separate Git worktree/child branch; no edits to the original branch, D1, D2, Python Research Core or Clinical Workspace.

## Delivered

- Native Rust `read_synthetic_fixture_source` is a fourth **allowlisted** command, not a file reader. It accepts only `{fixture_id}`, exact-matches the existing four embedded fictional fixture IDs, enforces max ID 64 bytes and max source 65,536 bytes, rejects unrecognized keys by deserialization, and parses UTF-8/JSON syntax without asserting FHIR semantics.
- Source response identifies versioned contract, SHA-256, exact byte length, MIME, `synthetic_only=true`, `release_authorized=false`, and literal source text. Errors use fixed codes and never echo the submitted ID.
- React requires successful prior Rust/native byte verification, then an *explicit* Inspect Source click. The browser independently recalculates SHA-256 from returned UTF-8 bytes; contract, fixture ID, byte count, source hash, MIME, and authorization flags must match the earlier allowlist. On any mismatch, refuses to display.
- Read-only `<pre><code>` text is safely escaped by React. No arbitrary HTML execution, remote data fetch, file picker, clipboard export or persistence.
- Selection change clears verification/source; late responses are discarded by generation guard. Disclosure says **FICTIONAL** and **NOT FHIR validation / clinical authorization**.

## Test outcomes (exact child branch before final commit)

| Check | Result |
| --- | --- |
| Rust `cargo test --locked` | **10/10 PASS**, including new source allowlist and unknown/traversal/oversize negatives |
| Rust `cargo clippy --all-targets -- -D warnings` | **PASS** |
| Rust `cargo fmt --all -- --check` | **PASS** |
| Vitest/RTL | **45/45 PASS**, including response contract, changed-byte hash mismatch and valid disclosure |
| TypeScript strict + Vite production build | **PASS** |
| Playwright real Microsoft Edge / Vite browser preview | **44/44 PASS**, including source-view workflow and previous 28-route+WCAG checks. **Browser mock is not native proof.** |
| Raw fixture SHA / byte golden verification | **4/4 PASS** |
| npm production audit | **0 reported vulnerabilities** |
| `cargo deny check` | **PASS**; inherited duplicate-dependency/license-not-encountered warnings; no new Rust packages |
| Tauri CLI debug build (`--debug --no-bundle`) | **PASS**, Vite frontend embedded into local Windows executable; unsigned, not released |
| Real Windows WebView2 + UI Automation (new source command) | **PASS**, exact golden verified, `FICTIONAL SOURCE` plus `resourceType` and `EXAMPLEPERSON` observed from Rust via native UIA; Dark/Light screenshots at 1280×800 and 1440×900 logical, DPI 125% |

## Native build note

Direct `cargo build` creates a debug executable that points to the dev server `localhost:1420`. Running that without the dev server produced `ERR_CONNECTION_REFUSED`; it was an **invalid native test setup**, not a UI feature failure. The qualified native command is `npx tauri build --debug --no-bundle` to embed Vite assets. Then execute `tests/windows-uia-source-slice2.ps1` against the resulting exact binary. If this fails or is not run, record **native UIA NO-GO / NOT RUN** explicitly, never infer success from browser Playwright.

## Known barriers and explicit non-claims

- Existing **WebView2 IPv6 TCP/443 egress NO-GO** observed in Slice 1 remains unresolved and carried forward. No zero-egress, fully offline or private-PHI readiness claim.
- Source bytes are pinned fictional fixtures only; this is neither FHIR structural validation nor semantic clinical validation.
- No real patient data, EHR writes, model inference, training, network APIs, Python sidecar, release publishing, or automatic model downloads.
- Browser mock and native Rust source responses share checked-in fictional fixture identities, but browser display alone does not qualify native Windows.
- Additional independent EGM/Goldfish and code review for Slice 2 is **NOT RUN** at this checkpoint; no unsupported review claim.
- Existing DPI 100/150/200% and macOS/Linux tests remain unqualified, do not inherit Slice 1 successes.
- Brand Overlap Forward PR #868 still awaits owner optical sign-off; rejected PR #866 is not used.

## Follow-on slice candidates (not implemented here)

A safe future vertical slice is a **structural** fictional FHIR validator with duplicate-key rejection and bounded local reference traversal, under independently reviewed Rust semantics. A real Workspace/Python sidecar is explicitly excluded until its isolation/security contract is approved. WebView2 OS-level network confinement remains a separate mandatory security gate before any PHI or release discussion.
