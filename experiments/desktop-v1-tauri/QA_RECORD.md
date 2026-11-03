# QA record — MedOrigin Desktop v1, Slice 1 (2026-11-03)

**Branch:** `feat/medorigin-desktop-v1-20261103` · **Base:** PR #870 head `1bd0cb58` · **Exact reviewed SHA:** see §10 (filled at final commit)
**Environment:** Windows 11 Home build 26300 · primary display 1920×1200 @125% DPI (logical bounds 1536×960) · WebView2 runtime 156.0.4314.58 · Intel UHD Graphics
**Toolchain:** node v24.19.0 · npm 11.17.0 · cargo/rustc 1.97.1 · python 3.14.7 · @tauri-apps/cli 2.12.4 · vite 8.3.5 · react 19.3.1 · vitest 5.1.0 · playwright 1.64.1 · @axe-core/playwright 4.14.0 · cargo-deny 0.20.2 · cargo-audit 0.22.2

**Disposition ceiling for this slice:** `INTEGRATED SYNTHETIC` only. This is **not** clinical software, not releasable, not offline-qualified, not reviewed for any medical use, and implies no outcome in any other track.

## 1. Gate results

| Gate | Result | Evidence |
|---|---|---|
| `cargo test --locked` | **PASS 8/8** | fixture goldens; unknown/traversal/oversize ids; `deny_unknown_fields`; error envelope never echoes input; status flags false; navigation allow/deny lists; round-trip parsed-equality |
| `cargo clippy --all-targets -- -D warnings` | **PASS** | clean |
| `cargo fmt --all -- --check` | **PASS** | clean |
| `cargo deny check` | **PASS** (exit 0): advisories ok, bans ok, licenses ok, sources ok | own crate license added (Apache-2.0); HTTP-client bans recorded; license allowlist |
| `cargo audit` | **exit 0** | 2 allowed warnings (RUSTSEC-2024-0370, RUSTSEC-2024-0429) — `glib 0.18.5`, reachable only via Linux `webkit2gtk`/`gtk` chains of `wry`; **not reachable on Windows target**; unsound-class warnings, no patched release compatible with pinned wry |
| npm dependencies | **prod: 0 vulnerabilities** · dev: 3 findings **WE FIXED** — `vitest` upgraded 3.2.7 → 5.1.0 (advisories GHSA-82fw-gwwq-j7x9, GHSA-qxg6-89mg-rqv8, GHSA-5gmw-xhrv-c9v3, GHSA-85c8-ppgw-ccpr); after upgrade `found 0 vulnerabilities` | lockfile committed |
| Vitest + RTL | **PASS 41/41** (8 files) | incl. contract-mismatch, hash-mismatch (never "verified"), list-contract-mismatch, stall/timeout discard, status-failure hard-block, registry 28/28 derived from FEATURE_COVERAGE.md, token sync light/dark/system vs PR #870 JSON, gated-route no-CTA, storage-key inventory, Tab trap |
| tsc strict | **PASS** | no errors |
| Vite build | **PASS** (rolldown minifier, target es2022) | `dist/` untracked; no inline `<script>`; no meta CSP (tauri.conf.json is authoritative) |
| Token contract | **PASS** (`docs/design/desktop-v1/test_tokens.py`) 36/36 ≥ 4.5:1 · `test_handoff.py` PASS | PR #870 scripts unmodified |
| Vitest goldens = Python goldens | **PASS 4/4** (`tests/verify_goldens.py`, LF-only, sha256 of committed bytes) | identical values pinned in Rust tests, `src/lib/ipc.ts` (browser mock), `tests/verify_goldens.py` |
| Playwright (Chromium vs `vite build` + preview, WCAG2A/2AA axe) | **PASS 43/43** | all 28 routes render console/page-error-free; theme persist + 2-key storage inventory; palette Ctrl+K/fuzzy/Escape; no popup from crafted link; **axe: `/`, `/fhir-inspector`, `/export`, `/settings` — 0 violations**; screenshots 1280×800, 1440×900, 1920×1080 × {dark, light} |
| Native Windows UIA (real WebView2 binary) | **PASS** — `V1_UIA_SMOKE_PASS` | window found by exact title `MedOrigin — Synthetic Developer Preview (v1)`; honesty banner readable; golden SHA-256 verified **via real Rust→React round-trip**; forged-id probe rejected (`unknown_fixture`); 6 native screenshots with non-blank diversity check |
| WebView2 egress snapshot (adapted from PR #661) | **NO-GO (external sockets observed — twice, 8s and 33s)** | `V1_NETWORK_ISOLATION_NO_GO`: 2× `Established` IPv6 TCP/443 from a WebView2 descendant to the same remote (2603:1046:c0c:c0c::2:443) at both checks; UDP endpoints 0; process tree 8. **Same D1 NO-GO pattern as PR #661. System-wide mitigations were not attempted. This build is not offline/egress-qualified.** |
| Impeccable (`detect`, src + rendered page) | **PASS with 1 waiver** | Fixed: border-tact side-tabs, low-contrast placeholder (3.7:1), heading-level skip (h1→h3), 10–11px functional text, straggler | straggler advisory remains; **WAIVER:** `overused-font` on Inter — Inter is the typeface mandated by the PR #870 token contract (`Inter / Instrument Sans / system UI`, Segoe UI fallback, no webfont download) |
| Emil Kowalski motion review | **PASS** | zero animation on palette/navigation shortcuts; `prefers-reduced-motion` honored in CSS; skeleton pulse disabled under reduced motion; no decorative motion added |
| Alibaba Open Code Review | **host-agent delegated review** (`ocr v1.13.4`, `ocr delegate`; **no code left the machine**; cloud provider NOT used) | findings in §4; all dispositioned |
| EGM / Goldfish independent review | EGM plugin **NOT INSTALLED** (recorded); **three fresh-context Goldfish subagents ran** (architecture, security, completeness) before implementation | all BLOCKER/MAJOR findings dispositioned — see `SLICE1_REVIEW_DISPOSITIONS.md`; spec amended v1.0 → v1.1; FEATURE_COVERAGE anchor paths pinned |
| TesterArmy E2E | **NOT RUN** — not installed, unverified; Playwright covers its would-be role | do not represent otherwise |
| Paper Desktop MCP | **NOT RUN / unavailable** — desktop not running at session start (tool error) | no Paper assets created or referenced |
| DPI 100/125/150/200% | **PARTIAL** | 125% DPI native run (scale 1.25, logical sizes forced); 100/150/200% **NOT RUN** (requires separate display/sign-out settings — out of bounds for this session) |
| 1920×1080 native window | **NOT RUN** — primary logical screen bounds 1536×960 @125% DPI; window cannot exceed it | browser Playwright 1920×1080 captures recorded as **browser evidence only**, not native |
| macOS / Linux | **NOT RUN / NOT CLAIMED** | separate platform qualification track |
| PStack | **NOT RUN as a tool** — impact analysis done inline (EXECUTION_PLAN §6); no `pstack` CLI verified | interactive pstack skills exist in harness but were not forced onto a non-pstack repo layout |

## 2. Connected capability boundary (exact)

Only three native commands exist and are reachable from the UI:

- `get_desktop_status` — flags hardcoded false; `mode=SYNTHETIC_DEVELOPER_PREVIEW`; `app_version=0.0.0`; `token_contract=0.1.0-design-review`
- `list_synthetic_fixtures` — metadata only (id, label, media_type, byte_len, sha256_hex); contract `medorigin-fixtures-list-v1`
- `verify_synthetic_fixture` — id allowlist; `len ≤ 64`; private cap `MAX_INPUT_BYTES = 65_536` (caller-supplied cap deleted); contract `medorigin-fixture-verify-v1`

Everything else in the UI is an honest label (`Foundation` / `Gated` / `Deferred` / `Designed` / `Fixture-only`) with a reason string and a source anchor. **No route other than `/fhir-inspector` invokes a native command.**

## 3. Required visible strings (verified in native screenshots + UIA)

- `SYNTHETIC / DEVELOPER PREVIEW` (sidebar ribbon) ✓
- `SYNTHETIC — NOT EGRESS-QUALIFIED` (Home honesty banner) ✓
- `SYNTHETIC_DEVELOPER_PREVIEW` (Home environment, via `get_desktop_status`) ✓
- `FICTIONAL — NOT CLINICAL DATA` (inspector banner) ✓
- `FICTIONAL` in every fixture label; `Synthetic only` workspace line ✓

## 4. Alibaba Open Code Review — host-agent findings and dispositions

Diff reviewed: `1bd0cb58..HEAD` (my commits only) with `ocr delegate` rules applied. No findings were fabricated; nothing was sent to a cloud LLM.

| # | File | Finding | Sev | Disposition |
|---|---|---|---|---|
| 1 | src/components/CommandPalette.tsx | Tab could move focus out of the modal combobox (focus-order leak) | MINOR | **FIXED** — Tab trapped in input; test added (41/41 green) |
| 2 | src/screens/HomeScreen.tsx | ARIA `role="table"` without `role="rowgroup"` wrappers | MINOR | **FIXED** — header/body rowgroups added |
| 3 | src/screens/FixtureInspectorScreen.tsx | Fixture count `4` hardcoded in heading | MINOR | **FIXED** — bound to loaded list length |
| 4 | src/components/Inspector.tsx / Home / Inspector screens | icon components missing consistent class | NIT | **FIXED** — `.brand-icon` accent on honesty banners |
| 5 | src/components/TopBar.tsx | audience check: `aria-expanded` static `false` on palette trigger | MINOR | **FIXED earlier** — now bound to `paletteOpen` |
| 6 | src/App.tsx | dev toggle: none present | NOTE | none — no hidden dev affordances in production paths |
| 7 | src-tauri/src/lib.rs | commands private vs pub hygiene | NOTE | kept **private**, matching D1 pattern; window entry only `pub` |
| 8 | src-tauri/deny.toml | `tokio` ban would fail vs tauri; `glib` advisories Linux-only | NOTE | tokio ban removed (HTTP clients only); glib tolerated, Linux-only, recorded in §1 |
| 9 | package-lock.json | vitest dev advisories | MAJOR | **FIXED** — upgraded to vitest 5.1.0; 0 vulnerabilities; tests re-run green |
| 10 | vite.config.ts | `minify: 'esbuild'` without esbuild in lock → build crash | MAJOR | **FIXED** — default (rolldown/oxc) minifier |
| 11 | e2e chrome | playwright install to custom browsers path | NOTE | documented; CI would use default path |
| 12 | windows-uia-smoke | em-dash `.ps1` saves as UTF-8 BOM; UIA text is caps-transformed | NOTE | script saved with BOM; predicates case-insensitive where text-transform applies |

## 5. Threat model & residual risks (accepted, recorded)

1. **WebView2 background traffic is outside app control** — empirically external IPv6 TCP/443 observed on this machine (§1). `security.csp` and navigation-deny do not bind it. Accepted for this synthetic experiment; **no offline/egress claim is made anywhere**. Resolution would require application-scoped OS isolation + packet capture (D1 NO-GO remains in force).
2. **Unsigned debug binary** — no publisher authenticity; any local process can spoof the window title. No release/signing claims.
3. **Same-domain SHA comparison circularity** — verifying Rust's reply against Rust's list detects inconsistency, not Rust compromise. Real boundaries: the compiled-in allowlist + raw-byte goldens + `include_bytes!`.
4. **Duplicate-JSON-key last-wins** (serde_json default) — accepted under raw-byte golden pin; D0 duplicate refusal remains its own branch.
5. **Browser Playwright ≠ native validation** — UIA is the separate native gate; browser results are labeled browser evidence everywhere.
6. **DEV probe control** — present only when `VITE_DEV_PROBE=true` or dev-mode build; visible, labeled, dashed, warning-colored, `role="status"` feedback; not an active control; excluded from default UIA/production claims. A release would cut it outright.
7. **macOS/Linux, DPI 100/150/200%, 1920×1080 native** — NOT RUN (§1); no platform claims inferred.
8. **console `--withGlobalTauri`** not used; IPC via `@tauri-apps/api/core` only.

## 6. What is deliberately NOT claimed

Not clinical. Not regulatory-ready. Not HIPAA-anything. Not offline. Not zero-egress. Not signed. Not reviewed by a human QA engineer. Not qualified on macOS/Linux. Not an authorization for real patients, models, EHR access, or Research Core admission. Not a merge of PR #870. Not a release, installer, or tag.

## 7. Screenshots / evidence files

- Browser (NOT native proof): `tests/screenshots/mo-v1-{dark,light}-{1280x800,1440x900,1920x1080}-{home,inspector}.png`
- Native Windows (UIA run, probe-enabled debug binary): `tests/screenshots/native/mo-v1-native-{dark,light}-{1280x800,1440x900}.png` (logical sizes; physical captures 1600×1000 / 1800×1125 at 125% DPI; non-blank verified by diversity check ≥ 500 distinct colors)
- `tests/verify_goldens.py` output; `windows-uia-smoke.ps1` output; `windows-egress-snapshot.ps1` output (×2, NO-GO); `tests/screenshots/uia-debug-flow.log` (element dump)

## 8. Exact identities

- Base (PR #870 head): `1bd0cb58`
- Canonical `main`: `dd84bb7b`
- D1 (referenced, untouched): PR #661 head `75c8b38a`; D1 stack to #846 `950fb1bf`
- D2 (referenced, untouched): PR #670 head `79520076`
- This slice — docs commit: `dc3bd725` · implementation commit (gates green): `9365fc55` · verification commit: see §10
- Review/report commits on this branch sit on top; the branch HEAD at the time of the final verification run is recorded in §10.

## 9. Unresolved blockers / future work

1. WebView2 egress NO-GO (§1) — unresolved by design; needs OS-level isolation study, owner decision.
2. 1920×1080 native capture impossible on this display — needs a ≥1920×1080 session.
3. macOS/Linux qualification — separate tracks.
4. Real sidecar wiring to Python (versioned, allowlisted, supervised) — unauthorized until security review; deliberately absent.
5. Brand identity — Overlap Forward v2 (PR #868) pending optical approval; no logo used.
6. D4/D5 (platform qualification, release) — not started; no artifacts published anywhere.

## 10. Final verification identity

- **Code/evidence tree verified:** `e4f3f7bc` (implementation `9365fc55`; docs/evidence `dc3bd725` + `e4f3f7bc`) — every screenshot, gate output and UIA/egress result cited in §1 was produced from this tree or on its direct ancestors with no source edits afterwards (the subsequent commit only fills in this section).
- Windows 11 Home build 26300 · 125% DPI · WebView2 156.0.4314.58.
- Review identity for the whole slice: branch `feat/medorigin-desktop-v1-20261103` (worktree `C:\Users\Shehr\work\MedOrigin-desktop-v1`), based on PR #870 head `1bd0cb58`.
- Known open items carried into the next slice: see §9. No claim in this record exceeds `INTEGRATED SYNTHETIC`.

