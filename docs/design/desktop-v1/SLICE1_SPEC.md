# Slice 1 spec — MedOrigin Desktop design system + connected synthetic fixture slice (v1.1, post-Goldfish)

**Date:** 2026-11-03 (v1.1 amended after three fresh-context Goldfish reviews; dispositions in `SLICE1_REVIEW_DISPOSITIONS.md`) · **Branch:** `feat/medorigin-desktop-v1-20261103` · **Base:** `1bd0cb58` (PR #870 head)
**Implements:** Inkling phases D1 (design system) + D2 (one bound slice) from `INKLING_HANDOFF.md`, delivered as a **new additive track** `experiments/desktop-v1-tauri/`.
**Does not implement:** D3 full matrix, D4 platform qualification, D5 release. The D1 Tauri (PR #661) and D2 egui (PR #670) experiment tracks are **not modified**.

## A. Artifact layout

```
experiments/desktop-v1-tauri/
  package.json / package-lock.json   (all deps exact-pinned via lockfile; versions set at install time and recorded in QA record)
  vite.config.ts / tsconfig.json / tsconfig.node.json / index.html
  .gitattributes                     (fixtures: *.json text eol=lf)
  src/
    main.tsx, App.tsx, app.css       (tokens only, zero hex literals outside tokens.css)
    bootstrap.js                     (external, synchronous, script-src 'self'; theme pre-paint)
    theme/ThemeProvider.tsx
    styles/tokens.css                (vendored from docs/design/desktop-v1/tokens.css; sync test §D)
    lib/ipc.ts                       (@tauri-apps/api/core invoke wrappers; mockable; non-Tauri mock fallback)
    lib/routes.tsx                   (route registry — single source of truth, table in §C-appendix)
    components/                      (Sidebar, TopBar, Inspector, CommandPalette, StatusChip, GatedState,
                                      FoundationState, ErrorBoundary, DataState)
    screens/                         (Home, FixtureInspector, GatedScreen*, AboutScreen)
  src-tauri/
    Cargo.toml / Cargo.lock / tauri.conf.json / capabilities/default.json
    fixtures/patient.min.json, allergy.min.json, observation.min.json, bundle.min.json   (committed, LF)
    src/main.rs / src/lib.rs
    tests? (unit tests inline #[cfg(test)])
  tests/windows-uia-smoke.ps1        (adapted from PR #661 `experiments/desktop-d1-tauri/tests/windows-uia-smoke.ps1`)
  e2e/ (Playwright)                  (@playwright/test + @axe-core/playwright)
  src/**/*.test.tsx                  (Vitest + RTL)
```

**Window / bundle / capability identity (pinned):**
- `productName`: `MedOrigin Synthetic Desktop v1` · `identifier`: `com.medorigin.desktop.v1` · `version`: `0.0.0` · `bundle.active`: `false`
- Window title: `MedOrigin — Synthetic Developer Preview (v1)` · `minWidth` 1280 · `minHeight` 800 · default 1440×900 · resizable · decorations · no devtools in release (devtools false)
- Icons: generated programmatic placeholder (orange dot on dark rounded square); **not** the Overlap Forward logo (PR #868 pending optical approval). Placeholder files committed under `src-tauri/icons/`.
- `withGlobalTauri`: **not set** — all IPC via `@tauri-apps/api/core` imports. Playwright must know: browser runs get a deterministic non-Tauri mock from `lib/ipc.ts` (identical contract shapes), never the real bridge; UIA is the only native/WebView2 gate.
- `capabilities/default.json`: windows `["main"]`; permissions = `["core:default"]` **or** an equivalently minimal enumerated set containing zero entries matching `fs:|shell:|http:|opener:|dialog:|clipboard:|updater:|process:|notification:|path:`; zero `remote` entries. A scripted test (§D) parses this file and asserts the allowlist. Audit valid against the pinned `Cargo.lock`; re-audit whenever the lock changes.
- `tauri.conf.json` `security.csp` is **authoritative**; no meta CSP in `index.html` (if both ever appear they must be byte-identical; CI/test asserts absence of meta).
- Vite `base: './'`.

## B. Rust command contracts (versioned, typed, fail-closed)

All commands take/return serde structs with `#[serde(deny_unknown_fields)]`. **No user-controlled path, URL, bytes, or hash ever enters a command.** Errors serialize as `{ "code": "<fixed>" }` from an exhaustive enum; the submitted string is **never** echoed; internal panics map to `internal` (fixed code, stable shape — asserted by test).

1. `get_desktop_status() -> DesktopStatus`
   `{ contract: "medorigin-desktop-status-v1", mode: "SYNTHETIC_DEVELOPER_PREVIEW", app_network_plugins_enabled: false, webview_egress_qualified: false, release_authorized: false, production_parity_qualified: false, app_version: "0.0.0", token_contract: "0.1.0-design-review" }`
   Flags are hardcoded `false` constants (no constructor that flips them); tests assert all four are false and that serialization round-trips (parsed-equality, not byte order).
2. `list_synthetic_fixtures() -> FixturesList`
   `{ contract: "medorigin-fixtures-list-v1", fixtures: [ { id, label, media_type, byte_len, sha256_hex } ] }` — metadata only, no bytes. Frontend **refuses to render** any response whose `contract` does not exactly match.
3. `verify_synthetic_fixture(req: VerifyFixtureRequest) -> FixtureVerification`
   `VerifyFixtureRequest { fixture_id: String }` — `fixture_id` length ≤ 64 else `invalid_input`; unknown id → `unknown_fixture`; internal cap constant `MAX_INPUT_BYTES = 65_536` (private, not caller-supplied — retained only for D0 parity; no caller-visible knob); if a compiled-in fixture exceeded the cap → `input_limit_exceeded` (defensive; unreachable in practice); returns `{ contract: "medorigin-fixture-verify-v1", fixture_id, byte_len, sha256_hex, synthetic_only: true, release_authorized: false }`.

**Fixtures (fictional, committed bytes, LF via `.gitattributes`; `include_bytes!`; sha256 over file bytes — never re-serialized):**
`fixture-patient-alpha.json`, `fixture-allergy-beta.json`, `fixture-observation-gamma.json`, `fixture-bundle-delta.json` — content is FICTIONAL (names like "FICTIONAL-PATI-ALPHA-001"), each carries `"note": "FICTIONAL — not clinical data"`. Golden SHA-256 + byte_len computed over the committed bytes, **cross-checked by a Python script** (`tests/verify_goldens.py`) and recorded in the QA record. D0's vectors (`patient-minimal` sha `747e1e…`, etc.) are **not** reused and their names are not reused — zero cross-track digest ambiguity; D1/D2 branches untouched.

**Golden stability:** goldens are pinned against committed byte strings; serde_json default parsing only (duplicate-key last-wins) — provenance rides on raw bytes; structural FHIR validation (incl. duplicate-key refusal, Bundle reference checks) is **out of scope** for slice 1 and stays on D0/D1 branches. UI copy for `fixture-bundle-delta`: "hash-verified only — no FHIR structural validation in slice 1".

**IPC stall:** frontend `Promise` race, constant `MO_IPC_STALL_MS = 3000`; on stall the UI enters fail-closed `error` state with copy "native verification stalled"; a post-timeout resolution is discarded and can never flip `stalled → ready` (tested). Synchronous bounded Rust, no IO — stall is defense-in-depth, not a cancellation mechanism.

**Navigation deny (Rust side):** `on_navigation` denies navigation to anything outside the app protocol; new windows/popups denied; the decision fn is factored out (`fn allow_navigation(url) -> bool { false }`) and unit-tested; no `window.open` anywhere (grep + review); clicking a crafted anchor cannot leave the app (Playwright asserts no popup/page events).

## C. Frontend behavior

- **Theme:** `data-theme="dark|light"` on `<html>`; `system` (default when `mo.theme` unset) removes the attribute; explicit choice persisted in `localStorage` key **`mo.theme`** ∈ `{light, dark, system}`; density (**`mo.density`** ∈ `{compact, comfortable}`, default `compact`) sets `data-density`. Only these two keys may ever be written (Vitest key-inventory test enumerates every `setItem`). `bootstrap.js` (external, `<script defer>`-equivalent synchronous classic script from `/bootstrap.js`) allowlists `mo.theme`/`mo.density` values and ignores everything else; no flash. Reduced motion: `prefers-reduced-motion: reduce` zeroes transitions; no animation on palette/nav shortcuts (Emil-Kowalski rule).
- **Density (exact):** `compact` (default): body 13 px, control min-height 38 px, row min-height 40 px, sidebar nav 38 px. `comfortable`: body 14 px, control/row/nav min-height 44 px. All changes via `[data-density="comfortable"]` attribute selectors in `tokens.css`-derived CSS.
- **Typography:** stack `Inter, "Segoe UI", system-ui, sans-serif` (Inter not presumed installed — falls back to Segoe UI; no webfont downloads). Sizes: body 13 (comfortable 14), subtitle 16, title 22. Weights pinned: **400 / 600 / 700 only**. Line-heights: body 1.5, subtitle 1.45, title 1.2. No other weights/sizes.
- **IA (single registry, `lib/routes.tsx`):** 28 sections of `FEATURE_COVERAGE.md`, each exactly once; full table in **Appendix R** below (path, label, group, status, reason, anchor). Groups: **Workspace**, **Research**, **Trust**. Status enum: `fixture-only | foundation | gated | deferred | experiment | designed` with mandatory reason + source anchor (module paths under `apps/workspace/src/medscale_workspace/` or `src/medscale/…`; CW-spec rows anchored to `specs/medscale-clinical-workspace-v1/capability_map.md`). Coverage→spec→chip mapping in **Appendix M**.
- **Home:** environment summary from `get_desktop_status()` with **hard-blocked state on invoke failure** ("native status unavailable — labels untrusted"); registry inventory table with filter (same data as registry); honesty banner `SYNTHETIC — NOT EGRESS-QUALIFIED` always visible.
- **FHIR fixture inspector (connected slice):** list → select → `verify_synthetic_fixture` → provenance panel (`contract`, `sha256_hex`, `byte_len`, `synthetic_only`, FICTIONAL banner). Data-state machine: `idle → loading → ready | error | stalled` (`stalled` sub-state of error with distinct copy). Contract assertion: frontend rejects any response whose `contract` ≠ expected (mismatched-contract test); hash-mismatch test (verify SHA ≠ listed golden → `error`, never renders "verified"); `synthetic_only:true` displayed but never unlocks anything. `fixture-bundle-delta` labeled "hash-verified only — no structural validation". UIA selector contract (roles/names): list `aria-label="Synthetic fixtures"`, rows `aria-label="Fixture <id>"`, verify button `aria-label="Verify fixture with native Rust"`, result region `role="status" aria-label="Verification result"`, error region `role="alert"`.
- **All other routes:** consistent `GatedState` / `FoundationState` panel: status chip, reason, source anchor, "what would be required". No active button that no-ops. StatusChip labels from Appendix M mapping.
- **Command palette (Ctrl/Cmd+K):** fuzzy filter over registry navigation + actions (`Theme: light/dark/system`, `Density: compact/comfortable`, `Toggle inspector`, `Go to …`). **ARIA: combobox + listbox + `aria-activedescendant`**; arrow keys traverse, Enter executes, Esc closes, focus returns to trigger; zero animation; tests assert focus return and roving `aria-activedescendant`.
- **Sidebar:** 244 px; brand dot + "MedOrigin" (placeholder wordmark, not Overlap Forward); "SYNTHETIC / DEVELOPER PREVIEW" ribbon; active route: 3 px brand-orange (`--mo-brand-accent`) bar + `aria-current="page"`; keyboard-focus order = DOM order; contrast per tokens.
- **Top bar (52 px):** breadcrumb; theme segmented control (Light/Dark/System, `aria-pressed`); density segmented control; palette trigger with `Ctrl K` kbd hint.
- **Inspector (right, 320 px):** route-aware context (About screen: app/build hashes; Fixture inspector: provenance notes; others: why unavailable). Toggle button `aria-expanded` + shortcut `Ctrl/Cmd+Shift+I`; focus returns to toggle on collapse; **not persisted**; hidden below 1150 px.
- **Settings:** theme, density, keyboard shortcut reference (real), storage-key inventory display (`mo.theme`, `mo.density` only). Nothing else clickable.
- **About & diagnostics:** `productName`, `app_version` from `get_desktop_status` (`0.0.0`), `token_contract`, build/identifier disclaimer; explicitly "not releasable; not clinically authorized".
- **Routing:** HashRouter (Tauri static asset protocol has no history fallback). Reload-safe.
- **Error boundary:** top-level React ErrorBoundary renders a stable honest fallback ("Something failed to render — no data was changed…") instead of a blank webview; tested.
- **Security posture:** `dangerouslySetInnerHTML` **prohibited** (grep src/+dist/ for `dangerouslySetInnerHTML|innerHTML|outerHTML|document.write|eval(|new Function` → zero); fixture JSON rendered via escaped text nodes only; **no telemetry, no app-initiated network calls** — WebView2 background traffic is unqualified and **not claimed absent** (D1 NO-GO 2026-10-29 stands verbatim); source grep (src/ and dist/) for `https://|http://|WebSocket|EventSource|sendBeacon|serviceWorker` → zero hits; `localStorage` writes restricted to `mo.theme|mo.density`; CSP as in §A; `object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; worker-src 'none'; img-src 'self'; style-src 'self'` (no `unsafe-inline` anywhere; no `data:` img).
- **Preview note (do not copy verbatim):** `preview.html` contains divergences — undefined `--mo-bg`/`--mo-brand` vars, 306 px inspector, 38/32 px targets, dead <720 px CSS. Implement to this spec and `tokens.css`, not to the preview.

## C-appendix R — Route registry (28 rows; path, label, group, status, reason, source anchor)

| # | Path | Label | Group | Status | Reason (one line) | Anchor |
|---|---|---|---|---|---|---|
| 1 | `/` | Home | Workspace | designed | Shell route; honesty banner + inventory | apps/workspace/README.md |
| 2 | `/patients` | Synthetic patients | Workspace | foundation | Identity/binding/graph modules exist; no desktop adapter yet | apps/workspace/src/medscale_workspace/identity.py; binding.py |
| 3 | `/encounters/:id` | Encounter detail | Workspace | foundation | encounter/review modules; fixtures only, no live capture | apps/workspace/src/medscale_workspace/encounter.py; review.py |
| 4 | `/audio` | Audio & transcript | Workspace | gated | Microphone + ASR capture not qualified; review-only contract | apps/workspace/src/medscale_workspace/asr.py |
| 5 | `/notes` | Clinical note drafts | Workspace | foundation | draft/review contracts; synthetic-only editing | apps/workspace/src/medscale_workspace/draft.py; review.py |
| 6 | `/orders` | Orders / tasks | Workspace | gated | No auto-submit; manual review gate; external write blocked | specs/medscale-clinical-workspace-v1/capability_map.md (4.2) |
| 7 | `/coding` | Coding suggestions | Workspace | deferred | Out of authorized scope; billing submission never allowed | specs/medscale-clinical-workspace-v1/capability_map.md |
| 8 | `/evidence` | Clinical evidence | Research | foundation | retrieval/corpus/strength modules; snapshot not connected to UI yet | apps/workspace/src/medscale_workspace/retrieval.py; corpus.py; src/medscale/evidence_strength.py |
| 9 | `/literature` | Literature screening | Research | foundation | litdb + screen; read-only first | src/medscale/litdb/; apps/workspace/src/medscale_workspace/screen.py |
| 10 | `/fhir` | FHIR workspace | Research | foundation | fhir_r4 + fhirkit; synthetic-only | apps/workspace/src/medscale_workspace/fhir_r4.py; src/medscale/fhirkit/ |
| 11 | `/fhir-inspector` | FHIR fixture inspector | Workspace | fixture-only | **Slice-1 connected route** — native Rust-verified fictional fixtures | experiments/desktop-v1-tauri (this track); D1 PR #661 |
| 12 | `/graph` | Patient graph | Workspace | foundation | patient_graph/linked_workspace; synthetic only | apps/workspace/src/medscale_workspace/patient_graph.py; linked_workspace.py |
| 13 | `/timeline` | Patient timeline | Workspace | foundation | chronological view over same graph modules | apps/workspace/src/medscale_workspace/patient_graph.py; encounter.py |
| 14 | `/documents` | Documents & canvas | Workspace | designed | Structured notes + object blocks; PARTIAL FOUNDATION/DESIGNED — not connected | apps/workspace/src/medscale_workspace/draft.py; corpus.py |
| 15 | `/tables` | Tables & structured data | Research | foundation | dataset/analytics; local only | apps/workspace/src/medscale_workspace/dataset.py; analytics.py |
| 16 | `/search` | Local search | Workspace | foundation | exact scope + provenance; offline errors | apps/workspace/src/medscale_workspace/retrieval.py; corpus.py |
| 17 | `/analytics` | Analytics | Research | foundation | Workspace-only indicators; no Research telemetry | apps/workspace/src/medscale_workspace/analytics.py |
| 18 | `/datasets` | Dataset manager | Research | foundation | Research vs Workspace staging; no cross-domain copy | apps/workspace/src/medscale_workspace/dataset.py; src/medscale/dataset/ |
| 19 | `/export` | Export quarantine | Research | gated | Quarantine manifest implemented; Research admission GATED — STOP | apps/workspace/src/medscale_workspace/nobackflow.py; lifecycle.py; dataset.py |
| 20 | `/research` | Research explorer | Research | foundation | read-only hypotheses/artifacts | apps/workspace/src/medscale_workspace/research_view.py; src/medscale/research/ |
| 21 | `/benchmarks` | Benchmark & evaluation | Research | foundation | trusted results + frozen evaluator view; training/promotion GATED | src/medscale/bench/; src/medscale/mesc/; src/medscale/modelkit/ |
| 22 | `/models` | Model catalog & runtime | Research | gated | Execution/download GATED; identity display only | src/medscale/modelkit/; apps/workspace/src/medscale_workspace/asr.py |
| 23 | `/integrations` | Integrations | Workspace | gated | EHR write GATED; read-only dry-run contract later | apps/workspace/src/medscale_workspace/connector.py; fhir_r4.py |
| 24 | `/audit` | Audit history | Trust | foundation | append-only events/provenance view (not connected in slice 1) | apps/workspace/src/medscale_workspace/audit.py; provenance.py |
| 25 | `/storage` | Storage & recovery | Trust | foundation | encrypted store/backup quarantine; key status; platform provider must qualify | apps/workspace/src/medscale_workspace/storage.py; lifecycle.py; keyprovider.py |
| 26 | `/settings` | Settings | Trust | designed | Theme/density/shortcuts/storage keys only — all implemented | docs/design/desktop-v1/tokens.json; this spec §C |
| 27 | `/about` | About & diagnostics | Trust | designed | Build identity from get_desktop_status; no PHI in logs | CITATION.cff; this spec §B |
| 28 | `/help` | Help & safety boundaries | Trust | designed | Research/synthetic-only boundaries, incident workflow (SECURITY.md) | SECURITY.md; GOVERNANCE.md |

## C-appendix M — FEATURE_COVERAGE → registry status mapping

FOUNDATION→`foundation` · EXPERIMENT→`experiment` (slice-1 fixture inspector is the only connected instance; labeled fixture-only in UI) · DESIGNED→`designed` · GATED→`gated` (incl. compound "DEFERRED/GATED"→`deferred` + gated affordance) · DEFERRED→`deferred` · REQUIRED→`designed` (Help screen is implemented; its content is mandatory copy, not an authorization) · PARTIAL FOUNDATION→`designed`. Chips: foundation=solid neutral+`available`-style dot; fixture-only=orange dot; gated/deferred=muted, no CTA; designed=outline. Never green for missing capabilities.

## D. Test plan

- **Vitest+RTL:** theme resolution/persistence roundtrip; **registry integrity — expected set derived by parsing `FEATURE_COVERAGE.md` IA-table rows (28), not hardcoded**; every route renders; every gated route shows reason + anchor and zero active CTAs (role/aria queries); palette filter/keyboard/focus-return/`aria-activedescendant`; density attribute switch; ErrorBoundary fallback; FixtureInspector: ready / mocked-invoke error / **hash-mismatch → error (never "verified")** / **contract-mismatch → error** / stall timeout (mock timers, discarded post-timeout resolution) / **get_desktop_status failure → hard-blocked Home**; `localStorage` key inventory (only `mo.theme|mo.density`); tokens sync test (repo root resolved from test file location, **fails — never skips — if file missing**; asserts ≥both themes' properties match JSON + px layout/typography tokens).
- **Playwright (Chromium vs `vite build && vite preview`, NOT dev server, for security-relevant assertions; dev runs labeled):** all 28 routes render without console/page errors; no popup/page events after clicking fixture JSON links (navigation deny is browser-irrelevant — assert no `window.open` effect); palette keyboard E2E; theme persist across reload (HashRouter); screenshots 1280×800 / 1440×900 / 1920×1080 dark+light (visual evidence only — never claimed as native); **@axe-core/playwright on Home, FHIR inspector and one gated screen (WCAG2A/2AA)**; reduced-motion emulation; bundle grep assertions on `dist/` copy of the grep list (above) + no inline `<script>` in built index.html + built index.html has no meta CSP.
- **Rust (`cargo test --locked`, clippy -D warnings, fmt --check):** goldens (computed over `include_bytes!` files); unknown id; `../` id; oversize fixture defensive path (`input_limit_exceeded`); id >64 bytes → `invalid_input`; error serialization shape matches `^{code:(unknown_fixture|invalid_input|invalid_limit|input_limit_exceeded|internal)}$` and never contains submitted input; desktop status all-false flags; round-trip parsed-equality; `allow_navigation` returns false; capabilities file parse test asserting permission array has zero forbidden prefixes and zero `remote`.
- **Supply chain:** `cargo deny` (installer recorded) — bans `reqwest|hyper|ureq|curl|isahc|tokio(net)|native-tls|openssl` + license allowlist + recorded output; `cargo audit` if DB fetchable, else explicit NOT RUN(reason). npm: lockfile committed; `npm audit --omit=dev` reported honestly.
- **Python goldens cross-check:** `tests/verify_goldens.py` recomputes sha256/byte_len for the four fixture files and asserts equality with the pinned values (output recorded).
- **Native Windows (real binary):** `npm run tauri build -- --debug --no-bundle` (flag verified against pinned tauri-cli; record version; binary at `src-tauri/target/debug/medorigin-desktop-v1.exe`); adapted `tests/windows-uia-smoke.ps1` (source: PR #661, `experiments/desktop-d1-tauri/tests/windows-uia-smoke.ps1`, base `75c8b38a`) — window found by exact title `MedOrigin — Synthetic Developer Preview (v1)`; verify flow reads the golden SHA text (aria names per §C); error region appears on forged id via typed-id field exposed only in debug builds as labeled `DEV — probe unknown fixture id` (visible, never styled as active, enumerated in registry as `experiment`); **egress snapshot adapted from PR #661 (`windows-egress-snapshot.ps1`) run and recorded — observed NO-GO is reported, not worked around**; screenshots via `CopyFromScreen` of the window rect at three sizes (smoke script sets window size via `SetWindowPos`) with a non-uniform-pixel sanity check (script fails on blank capture).
- **DPI 125–200%:** NOT RUN in slice 1 (recorded in QA record; D1/D2-style separate platform qualification track).
- **Security grep gate (src/ and dist/):** `https://|http://|WebSocket|EventSource|sendBeacon|serviceWorker|dangerouslySetInnerHTML|innerHTML|eval(|new Function` → zero (comments allowlist explicitly listed).

## E. Explicit exclusions / stop conditions

No PHI; no clinical use; no EHR read/write; no model download/execution/training; no Research Core writes/admission; no installer publication; no release claims; **no push/merge/PR without owner instruction**; no macOS/Linux claims; no "offline/zero-egress/secure/HIPAA-ready/qualified" claims anywhere — the only honest claim is "synthetic developer preview, not clinically authorized, WebView2 egress unqualified". If the WebView2 egress snapshot shows external traffic: record it, keep the NO-GO label, do **not** apply system-wide workarounds; slice still completes with the caveat documented. If any gate cannot run: mark NOT RUN with reason — never PASS.

## F. Definition of done (slice 1)

§D gates green or honestly NOT RUN (each recorded in `QA_RECORD.md` with date, tool versions, exact SHA); required visible strings verified in screenshots **and** UI: `SYNTHETIC — NOT EGRESS-QUALIFIED`, `FICTIONAL — not clinical data`, mode `SYNTHETIC_DEVELOPER_PREVIEW`; threat model & residual risks section present in QA record (unsigned binary; title spoofable; CSP ≠ WebView2 egress bound; same-domain SHA circularity accepted — real controls are the allowlist + raw-byte goldens; duplicate-JSON-key last-wins accepted under raw-byte pin; preview CSP divergence avoided by §A); docs updated; review findings dispositioned (`SLICE1_REVIEW_DISPOSITIONS.md`); exact SHA recorded; D1/D2 untouched; nothing pushed, merged, or published.
