# MedOrigin desktop — Ink engineering toolkit and quality gates
**Updated:** 2026-11-03. **Scope:** planning/build tooling for Ink, not evidence any tool has been installed, connected, or run inside Ink. All tools must remain free/local by default.

## Mandatory toolchain by engineering stage

| Stage | Tool/source | Intended work | Acceptance evidence / important limit |
| --- | --- | --- | --- |
| Spec and threat modeling | **Google Elephant-Goldfish Model (EGM)** — https://github.com/google/elephant-goldfish-model | Elephant reads existing MedOrigin architecture + D1/D2 and writes implementation-ready specification; independent zero-context Goldfish reviews it before coding | Save design draft, reviewers' findings, resolved items, readiness disposition. Goldfish requires **fresh separate agents**, never same-context self-review. If unavailable, mark review **NOT RUN** and do not mislabel it |
| Impact/dependency planning | **PStack** — inspect exact source/license/version before use; user's known reference https://github.com/cursor/plugins/tree/main/pstack | Review change impact, upstream/downstream callers, tests to update, fail-before/fix/pass-after plan | File:line impact matrix, actual test outputs. A planning tool isn't a security signoff |
| Source review | **Alibaba Open Code Review** — https://github.com/alibaba/open-code-review | Independent code-diff review, security and quality, using locally configured provider if available | Record provider/model, exact reviewed SHA, findings and resolution. Do not upload protected data or assume a paid cloud provider is free; tool-only review is not a human audit |
| User experience/design | **Impeccable** — https://impeccable.style / https://github.com/pbakaus/impeccable | Design critique, accessibility/theme audit, visual polish, responsive adaptation, heuristic/AI-slop detector | Run deterministic source and rendered-page checks; save reported findings/waivers and screenshot comparisons. Passing a detector does **not** mean visual acceptance |
| Motion restraint | **Emil Kowalski skills** — https://github.com/emilkowalski/skills | Polish transitions without slowing the professional desktop | No animation on command palette/navigation shortcuts; honor reduced motion, accessibility. Apply only compatible reviewed skills |
| Optional visual editing | **Paper Desktop MCP** if connected to Ink | Editable components/layout explorations, side-by-side UI critique; may import current tokens | Must verify the MCP actually exists; don't claim assets were created in Paper if not connected |
| Web/React unit tests | **Vitest + React Testing Library** | Component logic, accessibility state transitions, command palette, data-state machines | Real passing tests and verified mocks. Install only if adopting React/Vite frontend |
| Browser E2E | **Playwright Test** — https://playwright.dev/docs/intro | Smoke routes, responsive screenshots, keyboard, dialogs, themes, offline/error and deterministic synthetic workflows | Traces/screenshots, explicit checks at multiple widths. Browser E2E alone is **not** proof of packaged Windows native behavior |
| Agentic/deterministic E2E | **TesterArmy E2E** — https://github.com/tester-army/e2e | Optional complementary web E2E. Prefer deterministic no-model mode and isolate from real data | Disable telemetry with `E2E_TELEMETRY_DISABLED=1` and `DO_NOT_TRACK=1`; verify CLI from pinned source/installed docs; do not enable paid hosted browsers/models |
| Native Tauri E2E | **Tauri WebDriver/WebdriverIO + Windows UI Automation** — https://v2.tauri.app/develop/tests/ | Real installed/debug WebView2 app on Windows: focus, keyboard, native window state, WebView security and resources | OS-specific native test receipts. Tauri's mock runtime, browser Playwright and Rust unit tests don't substitute for a real Windows binary |
| Native Rust D2 verification | **cargo test/clippy/fmt + AccessKit/Windows UIA; Linux AT-SPI; macOS NSAccessibility** | Preserve existing D2 native egui accessibility/security and cross-platform tests | Exact-head OS-specific qualification; don't delete egui or misstate it is the Tauri shell |
| Accessibility | **axe-core/@axe-core/playwright**, Accessibility Insights (manual), screen reader | WCAG AA, labels, keyboard, focus, contrast, Windows scaling, high-contrast mode | Automated + manual checks; at least light/dark and 100/125/150/200% DPI. Audits don't replace screen readers |
| Runtime security | **cargo deny, cargo audit, OS egress checks, Rust/Tauri capability audits** | Supply-chain advisories, licenses, CSP/capability permissions, symlink/path escape, IPC negative tests, no telemetry | Pin tool revisions; independently inspect native network behavior. No generic shell bridge, network listener, PHI path or silent remote fallback |
| Cross-language safety | **mypy, Ruff, pytest, uv lock/check** on Python foundation + **serde** typed Rust contracts | Preserve Python Research Core/Workspace versioning, imports, frozen scientific receipts | No Workspace-to-Research backflow, no compatibility regression, no unapproved Python rewrites |
| Visual regression | **Playwright snapshots** for UI + manually compared images | Light/dark at 1280×800, 1440×900, 1920×1080, 125–200% UI scaling; detect overlap/clipping | Screenshot artifacts attached to PR with human/owner inspection; update baselines only for intentional reviewed changes |

### Actual installation / setup (in Ink's own environment only)

First identify Ink's supported agent harness, installed plugins, native build stack and exact repo HEAD. Install only the minimum compatible package set. Pin verified versions/revisions, record SPDX, NOTICE and supply-chain verification. **Do not install directly into the protected Python/Research Core lockfile.**

**Google EGM official entry points:** For Claude Code, `claude plugin marketplace add google/elephant-goldfish-model` followed by `claude plugin install egm@egm`; for Codex `codex plugin marketplace add google/elephant-goldfish-model` then `codex plugin add egm@egm`. For other tools follow the repository's documented harness instructions. EGM's actual commands include `egm-brainstorm`, `egm-draft`, `egm-review`, and `egm-drift-report`. The Goldfish review must be performed by a fresh-context agent/subagent. Never simulate reviewers inside the same drafting context.

**Impeccable:** Its documented installer is `npx impeccable install`, followed by project init and commands such as `/impeccable critique`, `/impeccable audit`, `/impeccable polish` (command syntax depends on harness). The no-model detector is `npx impeccable detect src/` and the rendered-page audit is `npx impeccable detect http://localhost:5173` when that local server is actually running. Do not silently auto-approve AI-driven design changes. Source: https://github.com/pbakaus/impeccable.

**TesterArmy E2E:** Read the version-pinned `e2e` package's local `node_modules/e2e/docs` or https://github.com/tester-army/e2e for exact commands. Enable `E2E_TELEMETRY_DISABLED=1` and `DO_NOT_TRACK=1` in its runner environment, and prefer model-free deterministic tests. A package version or hosted device/model shouldn't be installed merely because it appears in a prompt. For Windows Tauri, supplement with actual Windows UIA/WebDriver; a web agent cannot certify native confinement.

**Playwright:** Use `@playwright/test` plus `@axe-core/playwright` and an isolated synthetic-only dev server. Capture traces on test failure and audit both semantic DOM and full user journeys. Playwright browser coverage and native UIA are separate gates.

**Review and additional tools:** PStack, Alibaba Open Code Review, and Emil Kowalski skills are optional quality assistants; validate source and licensing before installation. Recommended supporting utilities: TypeScript strict, ESLint/Biome as appropriate, Rust `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test --locked`, `cargo deny`, Python pytest/ruff/mypy, GitHub exact-head CI, and OS-level Windows Event Log/UIA traces. Avoid paid services, uploading source or telemetry by default.

## Suggested nonpublishing order

1. **Audit** current branches/PRs D1 Tauri and D2 native egui, Python boundary and the rejected branding #866 / review-candidate #868.
2. **EGM** design draft → fresh Goldfish critique → resolve material findings → explicit ready/not-ready decision.
3. **PStack/impact map**: change surfaces, dependency risks, typed commands, capability gates, truth-in-UI.
4. **Implement one vertical slice** at a time, with Vitest/unit, Rust/Python parity, Playwright, native Windows UIA and TesterArmy E2E when suitable.
5. **Impeccable/Emil** pass on actual UI components; axe, keyboard, high contrast, display scaling, manual screenshot comparisons.
6. **Alibaba OCR + CI + cargo deny** source/security/compatibility review against exact HEAD; resolve findings.
7. **Demo** actual installed app on Windows (not a mockup); get visual signoff and a separate release-governance decision. Remain private/nonpublishing until authorized.

## Mandatory artifacts for each vertical slice

- Versioned specification + fresh independent reviewer report (or explicit NOT RUN)
- Exact commit SHA / dependency lock / tool versions / architecture diff
- Source-backed capability and route-state mapping
- Synthetic-fixture E2E / unit / IPC negative / platform UIA receipts, video/screenshots/traces where supported
- Accessibility + light/dark + DPI results and visual comparison
- Security supply-chain scan and no-telemetry/network boundary evidence; known blockers
- Honest disposition: **DESIGN ONLY**, **EXPERIMENT**, **INTEGRATED SYNTHETIC**, **BLOCKED**, **NO-GO**, never inferred **CLINICALLY APPROVED**

No automated agents, plugins or tests grant consent to process real health data, access patients, train models, enable EHR writes or ship installers.
