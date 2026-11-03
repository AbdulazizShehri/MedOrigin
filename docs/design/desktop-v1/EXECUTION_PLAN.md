# MedOrigin Desktop — source-grounded execution plan (2026-11-03)

**Branch:** `feat/medorigin-desktop-v1-20261103` (worktree `C:\Users\Shehr\work\MedOrigin-desktop-v1`), based on PR #870 head `1bd0cb58` (design contract, unmerged draft), which is based on canonical `main` @ `dd84bb7b`.
**Status:** engineering plan and first-slice record. Not a release authorization. Nothing here implies clinical approval.

## 1. Reconnaissance (verified 2026-11-03)

| Track | Location | Exact head | State |
|---|---|---|---|
| Canonical Python foundation | `main` (`src/medscale`, `apps/workspace`) | `dd84bb7b` @ 2026-10-23 | Research Core + Clinical Workspace; synthetic-only authorization |
| D0 Rust fixture-hash prototype | `experiments/desktop-d0-rust` (on D1 branch) | `75c8b38a` (via PR #661) | Isolated crate, golden SHA-256 contract `medorigin-desktop-d0-raw-sha256-v1` |
| D1 Tauri 2 + React/TS preview | `experiments/desktop-d1-tauri` | PR #661 head `75c8b38a`; stack continues to #846 (`950fb1bf`, IPC timeout fail-closed) | Experimental. Two commands only (`preview_status`, `hash_fixture`). **Observed Windows security NO-GO 2026-10-29:** WebView2 descendants opened external IPv6 TCP/443; not qualified as offline/zero-egress |
| D2 native Rust/egui | `experiments/desktop-d2-native-egui` | PR #670 head `79520076`; stack to #867 | Browser-engine-free; independently validated (Windows UIA, macOS AX, Linux AT-SPI per PRs #853–#856). Explicitly not a replacement for D1 or Python |
| Design contract (this PR) | `docs/design/desktop-v1/` | PR #870 head `1bd0cb58` | Tokens (36/36 contrast PASS), feature map, handoff, toolchain |
| Brand | PR #868 (Overlap Forward v2, pending optical approval); PR #866 **rejected — do not integrate** | — | Brand orange `#FE681B` is identity-only; operational buttons use accent tokens |

**Implications honored in this plan**

1. Python Research Core / Clinical Workspace are never rewritten, re-locked, or force-migrated in this plan.
2. D1/D2 test baselines are not modified. The new track is additive: `experiments/desktop-v1-tauri/`.
3. The D1 WebView2 egress observation carries forward: the new shell is labeled `SYNTHETIC / NOT EGRESS-QUALIFIED`, and no PHI/clinical use is authorized. macOS/Linux are not inferred from Windows results.
4. PR #870 stays a draft until owner review; this work does not merge it.

## 2. Architecture decision (recap + disposition)

Preferred long-term product UI: **Tauri 2 (Rust host) + React + TypeScript + Vite**, statically bundled local assets, no Next.js server, no remote content. Rust owns the trust boundary (allowlisted, typed, versioned commands; fail-closed). Python is the canonical research/workspace engine and is reachable only through future, independently approved versioned sidecars — not in this slice.

**Disposition:** adopt for a new, additive experiment track. Do not replace D1/D2 presentation, do not re-baseline either, and do not weaken D2 invariants. Migrations (C2/C3 in `ARCHITECTURE.md`) require per-capability parity receipts and are out of scope for this slice.

## 3. Capability inventory (summary of `FEATURE_COVERAGE.md`)

28 sections (verified by counting the IA table) mapped with source-backed module references. Slice 1 surfaces all 28 in navigation/overview with honest status labels. Genuinely connected in slice 1:

- **FHIR fixture inspector** (EXPERIMENT tier): native Rust-verified fictional fixtures, SHA-256 provenance, fail-closed unknown-id handling. This is the one end-to-end IPC workflow.

Everything else renders as: `FOUNDATION — NOT CONNECTED`, `GATED — SEPARATE AUTHORIZATION REQUIRED`, `DEFERRED`, or `EXPERIMENT`, each with a reason string and source anchor. No disabled control is styled as active; no planned feature is shown as operational.

Four qualification journeys remain for later slices; slice 1 implements none of them beyond the fixture-inspector path.

## 4. Slice 1 scope — design system + one connected synthetic slice

**Deliverable:** `experiments/desktop-v1-tauri/` — Tauri 2 + React 19? (pinned; see lockfile) + TS strict + Vite.

1. **Design system:** token-driven roles (Dark/Light/System, Comfortable/Compact density), 244 px sidebar, 52 px toolbar, 320 px inspector, focus-visible rings, ≥44 px targets, reduced-motion support, no hex literals in components (tokens only), contrast test green.
2. **Shell IA:** all 28 sections of `FEATURE_COVERAGE.md`, one route each, truth-labeled. The single source of truth for paths/labels/groups/statuses/reasons/anchors is the registry table in `SLICE1_SPEC.md` Appendix R (group layout: Workspace / Research / Trust); not duplicated here.
3. **Connected vertical slice — "Synthetic FHIR fixture inspector":** Rust commands `get_desktop_status`, `list_synthetic_fixtures`, `verify_synthetic_fixture` (allowlisted, in-memory, byte-capped, stable error codes). React renders list → detail → provenance (contract id, SHA-256, synthetic-only banner). Forged-id and oversize negatives fail closed.
4. **Quality gates:** Vitest + RTL unit tests; Playwright (smoke, keyboard, themes, 1280×800/1440×900/1920×1080, axe); Rust fmt/clippy/test; real debug binary + Windows UIA smoke; Impeccable detector pass; Emil-Kowalski motion review (no animation on command-palette/nav); Alibaba `ocr` review of the diff (provider recorded); Goldfish fresh-context review of the slice spec (EGM plugin NOT installed — recorded, reviewers run as fresh subagents).
5. **Recording:** this plan, slice spec, review findings + dispositions, test outputs, screenshots (real app, dark/light), exact SHAs, blockers. Not pushed, not released, not merged.

**Explicit non-goals:** no PHI, no clinical workflows, no EHR reads/writes, no model download/execution/training, no Research Core admission, no installer publication, no telemetry, no external navigation/network plugin, no updates to D1/D2/Python baselines.

## 5. Tooling disposition (verified 2026-11-03)

| Tool | State in this environment | Use |
|---|---|---|
| Google EGM plugin | NOT INSTALLED (no `egm-*` commands; marketplace not added) | Goldfish review reproduced with fresh-context subagents — labeled as such, never as "EGM receipt" |
| PStack | No `pstack` CLI verified; pstack *skills* exist in harness | Impact analysis done inline and recorded here (§6) |
| Playwright Test | Installable via npm (registry PONG 869 ms) | Browser E2E + axe-core + visual widths |
| TesterArmy E2E | Not installed; unverified | NOT RUN (optional) |
| Impeccable | `npx impeccable` unverified; `.impeccable` config dir exists | Deterministic `detect` attempted; otherwise NOT RUN, honestly labeled |
| Emil Kowalski skills | Available in harness (`emil-design-eng`) | Motion/interaction review |
| Alibaba Open Code Review | `ocr` v1.13.4 (76ab46a), provider `chatgpt` (cloud) | Diff review against exact SHA; provider recorded; no secrets/PHI in diff |
| Paper Desktop MCP | **NOT RUNNING** (tool error: desktop not running) | Not used; no Paper assets claimed |
| Native Windows UIA | Pattern proven by D1 (`tests/windows-uia-smoke.ps1`) | Adapted for this app; real debug binary required |
| Rust gates | cargo 1.97.1 | fmt/clippy/test --locked |

## 6. Impact / regression map (PStack-style, inline)

- New files only under `experiments/desktop-v1-tauri/` + docs in `docs/design/desktop-v1/`; **zero** edits to `src/medscale`, `apps/workspace`, `pyproject.toml`, `uv.lock`, D1/D2 branches.
- Token source of truth: `docs/design/desktop-v1/tokens.json`; app vendors `src/styles/tokens.css` with a sync test (root resolved from the test file path) asserting the app's CSS custom properties match the JSON exactly (fail-closed if missing).
- New dependency surface (npm + crates) confined to the experiment; lockfiles committed in-experiment; no root lockfile changes.
- Risks: WebView2 background egress (mitigation: labeled not-qualified, no network plugin, CSP `default-src 'self'`, external-navigation deny, documented NO-GO carry-forward); token drift (sync test); misleading readiness claims (status chips + tests that assert blocked labels render); focus traps (keyboard Playwright tests); font availability (system font stack, no webfonts).

## 7. Acceptance for slice 1 (all required, none sufficient alone)

1. `cargo test --locked`, `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check` green.
2. `npm run test` (Vitest) green, incl. fail-closed IPC negatives with mocked bridge.
3. `npm run e2e` (Playwright) green at 3 widths × 2 themes + axe scan on Home and FHIR routes.
4. Real Windows debug binary: UIA smoke PASS; screenshots dark+light at 1280×800, 1440×900, 1920×1080 (overflow/overlap inspected).
5. Token sync test green; 36/36 Python contrast test still green.
6. Goldfish review findings dispositioned; Alibaba OCR findings dispositioned; Impeccable/Emil pass recorded (or explicitly NOT RUN).
7. No claim of clinical authorization, zero-egress, or release readiness anywhere in UI or docs.

## 8. Known blockers carried forward

- D1/D2 remain Draft; brand PR #868 pending optical approval; WebView2 egress unqualified on Windows; Paper MCP unavailable this session; EGM plugin unavailable (fresh-subagent Goldfish used instead); macOS/Linux untested; real-patient authorization does not exist and cannot be granted by this work.
