# Slice 1 spec — Goldfish review dispositions (2026-11-03)

Three fresh-context reviewers (architecture, security, completeness) reviewed `SLICE1_SPEC.md` v1.0. All findings were verified against the repo before disposition. The spec was amended to v1.1; nothing was dismissed silently.

## Disposition summary

| Finding (reviewer) | Sev | Disposition |
|---|---|---|
| 29→28 sections (all three) | BLOCKER | **FIXED** — spec §C/§D, plan §3; registry test derives expected set from FEATURE_COVERAGE.md IA table (28 rows verified) |
| tauri.conf identity/capabilities/icons/withGlobalTauri unspecified (completeness #10) | MAJOR | **FIXED** — pinned in spec §A (productName, identifier, title, v0.0.0, bundle.active=false, min 1280×800, placeholder placeholder icons, `withGlobalTauri` unset, IPC via `@tauri-apps/api/core`, capability allowlist + scripted assertion) |
| Fixture bytes/hashes undefined; D0 name collision (architecture #4, completeness #3) | BLOCKER/MAJOR | **FIXED** — committed LF files under `src-tauri/fixtures/`, `include_bytes!`, sha256 over file bytes, Python cross-check script, new ids `fixture-*-{alpha,beta,gamma,delta}`, D0 vectors/names untouched |
| `max_input_bytes` caller cap is theater (security #9a) | MAJOR | **FIXED** — parameter deleted; private `MAX_INPUT_BYTES = 65_536`; `input_limit_exceeded` defensive code |
| Contract versioning asymmetry / unsupported version (architecture #2, security #15) | MAJOR | **FIXED** — `contract` on all three responses; frontend exact-match assertion + mismatch test |
| `input_limit_exceeded` unspecified (architecture #3) | MAJOR | **FIXED** — named code, defensive test |
| Forged-result/hash-mismatch untested (architecture #5, security #7, completeness #9) | MAJOR | **FIXED** — Vitest: hash-mismatch→error, contract-mismatch→error, stall timeout + discarded post-timeout resolution, status-fetch-failure→hard-blocked Home |
| CSP vs inline bootstrap contradiction (architecture #6/#7, security #1/#3/#30, completeness #4) | MAJOR | **FIXED** — external `bootstrap.js` (`script-src 'self'`); full directive set incl. `object-src/frame-src/base-uri/form-action/frame-ancestors/worker-src 'none'`, `img-src 'self'` (data: dropped), `style-src 'self'` (**no `unsafe-inline`**); `security.csp` in tauri.conf.json authoritative |
| Capability file never specified (security #4) | MAJOR | **FIXED** — §A pins windows/allowlist/forbidden prefixes/zero remote; scripted parse test in §D |
| No navigation deny (security #5) | MAJOR | **FIXED** — `on_navigation` deny-all via unit-tested `allow_navigation() -> false`; new windows/popups denied; Playwright asserts no popup/page events; `window.open` prohibited + grep |
| WebView2 egress evidence missing / overclaim wording (security #6/#11/#28, architecture #7) | MAJOR | **FIXED** — egress snapshot adapted as explicit gate; wording "no app-initiated network calls; WebView2 background traffic unqualified; D1 NO-GO stands"; §E stop condition; §F required visible strings; grep extended (`WebSocket|EventSource|sendBeacon|serviceWorker`) over src/ **and** dist/ |
| goldens self-referential / not cross-checked (architecture #4) | MAJOR | **FIXED** — goldens pinned against committed bytes + Python `tests/verify_goldens.py` cross-check recorded in QA record |
| UIA forged-id negative has no mechanism (completeness #2, architecture #5, security #18) | BLOCKER/MAJOR | **FIXED** — debug-build-only, visible, labeled `DEV — probe unknown fixture id` control; enumerated in registry; never styled as active; not present in release builds |
| D1 script source unlocatable from branch (completeness #25) | MINOR | **FIXED** — spec cites PR #661 + base SHA `75c8b38a` + path |
| CommandError envelope, codes, stall timeout, UI cap (completeness #9, architecture #1/#14) | MAJOR | **FIXED** — `{code}` envelope, exhaustive enum (`unknown_fixture|invalid_input|invalid_limit|input_limit_exceeded|internal`), `MO_IPC_STALL_MS = 3000`, UI passes no cap (parameter deleted) |
| Status endpoint failure unspecified (security #8) | MAJOR | **FIXED** — Home hard-blocked state, tested |
| Threat model missing (security #10) | MAJOR | **FIXED** — §F threat model & residual risks required in QA record; circularity accepted explicitly |
| Tauri CSP weaker than D1 / missing directives (architecture #7, security #1/#3) | MAJOR | **FIXED** — superset-equivalent hardened; D1 `unsafe-inline` style dropped deliberately (no inline styles permitted anywhere) |
| Golden/last-wins duplicate JSON keys (security #16) | MINOR | **FIXED** — goldens over `include_bytes!` raw bytes; duplicate-key clause restated flat (out of scope, D0 branch, raw-byte pin) |
| Token path contradiction (architecture #18) | MINOR | **FIXED** — vendored at `src/styles/tokens.css`; sync test resolves repo root from test file path; fails (never skips) on missing JSON |
| Registry enum gaps / status mapping unspecified (architecture #17, completeness #6) | MAJOR | **FIXED** — Appendix M maps coverage→spec→chip; all 28 statuses ∈ spec enum |
| Registry contents never enumerated (architecture #10, completeness #5) | MAJOR | **FIXED** — Appendix R lists all 28 routes with path/label/group/status/reason/anchor |
| Density unimplementable (completeness #7) | MAJOR | **FIXED** — exact px values pinned for compact (default, 13/38/40) and comfortable (14/44/44); bound via `data-density` attribute selectors |
| Typography weights/leading undefined; stacks disagree (architecture #20, completeness #14/#15) | MAJOR | **FIXED** — weights pinned 400/600/700; leading pinned (1.5/1.45/1.2); spec stack reconciled to `Inter, "Segoe UI", system-ui, sans-serif`, Segoe fallback documented |
| Palette ARIA pattern unspecified (completeness #16) | MINOR | **FIXED** — combobox + listbox + `aria-activedescendant` pinned, tested |
| Inspector toggle/shortcut/persistence undefined (completeness #17) | MINOR | **FIXED** — toggle + `Ctrl/Cmd+Shift+I` + `aria-expanded` + focus return; not persisted |
| Sub-1150px behavior (completeness #18) | MINOR | **FIXED** — inspector hidden <1150 px; desktop-only ≥1280 px pinned (minWidth); no mobile claims; Playwright ≥1280 only |
| Routing strategy (completeness #19) | MINOR | **FIXED** — HashRouter pinned |
| Error boundary missing (completeness #23) | MINOR | **FIXED** — top-level ErrorBoundary + test |
| First-run defaults (completeness #23) | MINOR | **FIXED** — `mo.theme` unset→system; `mo.density` unset→compact |
| About data source (completeness #20) | MINOR | **FIXED** — `DesktopStatus` extended with `app_version`/`token_contract` (constants) |
| Window size / screenshot forcing mechanism (architecture #13) | MAJOR | **FIXED** — minWidth 1280, `SetWindowPos` in UIA smoke + `CopyFromScreen` of window rect + non-uniform-pixel sanity check; native evidence split from browser Playwright evidence; UIA = only native gate |
| localStorage ungoverned (security #13) | MINOR | **FIXED** — key inventory test; bootstrap allowlist; only `mo.theme`/`mo.density` |
| `dangerouslySetInnerHTML` unprohibited (security #14) | MINOR | **FIXED** — prohibition + grep gate src/ and dist/ |
| `unsafe-inline` in style-src (security #2) | MAJOR | **FIXED** — removed; zero inline styles enforced by grep + review |
| `cargo audit/deny` demoted (security #12) | MAJOR | **FIXED** — mandatory-or-NOT-RUN(recorded); deny config bans HTTP client crates + license allowlist |
| 29 vs 28 in EXECUTION_PLAN | MAJOR | **FIXED** — plan updated |
| Plan IA subset vs spec registry (architecture #10) | MAJOR | **FIXED** — plan §4 references spec Appendix R as sole IA source |
| Token sync test scope wording "36 pairs" (architecture #17) | MINOR | **FIXED** — asserts both themes + px tokens; failure semantics pinned |
| `serde deny_unknown_fields` / error echo (architecture #1, security #9) | MAJOR | **FIXED** — structs with deny_unknown_fields; fixed-code envelope; submitted input never echoed; shape test |
| Window identity close to D1 collision (architecture #12) | MAJOR | **FIXED** — identifier `com.medorigin.desktop.v1`; title `MedOrigin — Synthetic Developer Preview (v1)` (unambiguously distinct from D1's hyphenated title); UIA takes title from §C pinned value |
| `stalled` vs `error` inconsistency; no timeout (architecture #14) | MINOR | **FIXED** — single machine `idle → loading → ready\|error`, `stalled` as distinct copy sub-state of error; 3000 ms constant |
| DPI 125–200% dropped silently (security #27) | NOTE | **RECORDED NOT RUN** in §D; QA record requirement |
| OCR provider chatgpt cloud, no owner sign-off (security #22) | NOTE | **ACCEPTED WITH RECORD** — diff contains no secrets/PHI (synthetic constants only); provider recorded in plan §5; owner explicitly directed Alibaba OCR use in mission; revisit if owner objects |
| Same-domain SHA comparison circularity (security #7/#25, architecture #5) | NOTE | **ACCEPTED** — documented as residual risk; real boundaries = allowlist + raw-byte goldens |
| Unsigned binary / title spoofing (security #24) | NOTE | **ACCEPTED** — recorded as residual risk; no signing claims |
| WebView2 browser flags not mitigation (security #28) | NOTE | **HONORED** — flags absent from spec; D1 NO-GO carried verbatim |
| preview.html broken references (completeness #30) | NOTE | **ACCEPTED** — divergence note added to spec §C (preview is PR #870 artifact; not modified here) |
| Duplicate JSON keys out of scope (security #23) | NOTE | **ACCEPTED** — raw-byte pin + D0 branch guard; leak prohibition noted |
| Per-route a11y coverage (completeness #13) | MAJOR | **FIXED** — RTL render+role/aria-disabled assertions for all 28 routes; axe on Home + inspector + one gated screen |
| Serialization stability test ambiguity (completeness #27) | MINOR | **FIXED** — round-trip parsed-equality, not byte order |
| `data:` img-src removed (security #30) | MINOR | **FIXED** — `img-src 'self'` |
| CSP authoritative location (security #3) | MAJOR | **FIXED** — `security.csp` authoritative; no meta CSP test-asserted |
| React/TS versions unpinned (architecture #16) | MINOR | **FIXED** — all versions exact-pinned via package-lock.json, recorded in QA record |
| Normative text drafting debris (architecture #16, security #26) | MINOR | **FIXED** — spec rewritten clean |
| Inkling D1/D2 vs repo D1/D2 terminology collision (architecture #11) | MAJOR | **FIXED** — spec header now reads "Inkling phases D1… delivered as new additive track"; §F spells out repo tracks untouched |

## Residual risks accepted (written into spec §F / QA record)

WebView2 background egress unqualified (D1 NO-GO verbatim); unsigned debug binary; window title spoofable by local processes; same-domain SHA comparison circularity (allowlist + raw-byte goldens are the real boundaries); duplicate-JSON-key last-wins under raw-byte pin; browser/PSI Playwright ≠ native Windows validation (UIA separate gate); macOS/Linux untested; DPI 125–200% NOT RUN; no real-patient authorization exists or can be granted here.
