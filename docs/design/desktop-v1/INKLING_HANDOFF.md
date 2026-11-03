# Inkling execution handoff — professional MedOrigin desktop

**Task:** Implement the production-quality MedOrigin app without dropping existing capabilities, contradicting the repository's research/clinical limits, or discarding qualified D1/D2 native work. **This is a design/engineering contract, not a release authorization.**

## What to read before coding
1. `ARCHITECTURE.md` — Tauri D1 / Rust egui D2 / Python trust boundaries.
2. `FEATURE_COVERAGE.md` — every product screen and its authorization status.
3. `tokens.json` and `tokens.css` — exact contrast-checked light/dark roles.
4. `preview.html` — interactive **design-only** UI color/layout study; no real engine.
5. MedOrigin `README.md`, `apps/workspace/README.md`, `specs/medscale-clinical-workspace-v1/capability_map.md`, `docs/BRAND_TRANSITION.md`.
6. Recent D1 Tauri and D2 egui PR heads: **do not overwrite or discard their existing evidence**.
7. Brand draft PR #868 (Overlap Forward v2) is still awaiting optical approval; old PR #866 is rejected. Do not treat a preview logo as automatically approved.

## UI direction

Linear-class **information architecture and interaction discipline**, not copied Linear code or distinctive visual assets:
- Dense but breathable, neutral layered panels, low-noise dividers and thin focus lines.
- 244 px left navigation, 52 px toolbar, adaptive content pane and optional right inspector (~320 px).
- Compact default layout plus a comfortable density option and system font scaling.
- Dark: charcoal foundation `#0D0F10`; surface `#181C1D`; ink `#F4F5F2`; action orange `#FF8A45`.
- Light: stone canvas `#F6F7F4`; surface `#FFFFFF`; ink `#19211C`; action orange `#C94A05`.
- Brand logo orange remains `#FE681B`. This bright orange is for identity/highlights; operational buttons use separately contrast-qualified accent tokens.
- CSS `prefers-color-scheme` when set to System, persistent local preference when explicitly changed, no theme flicker at launch.
- Command palette, keyboard-first navigation, accessible table sorting/filters, split view with provenance metadata; no decorative overanimation. Reduced motion honored.

## Implementation order

**D0 reconnaissance** — detect actual desktop runtime and current D1/D2 statuses, record exact heads and diffs. Avoid parallel editing of the existing research repository source. Preserve Python compatibility.

**D1 design system** — implement ColorProvider/ThemeProvider and 20+ semantic roles, typography, density, focus, command header, side navigation, inspector, dialogs, toasts, empty/error/blocked skeletons. Unit tests validate token values and contrast. Preview all routes with synthetic fixtures.

**D2 one real vertical slice** — versioned and typed Rust read-only call for a synthetic fixture. Render evidence, provenance, source identity and errors. Test failed IPC, forged receipt, timeout, unsupported version and no-backflow. No real PHI.

**D3 feature integration** — build all routes in `FEATURE_COVERAGE.md`, connect only authorized/qualified commands, and clearly gate unavailable features. Every route must have a data-state machine: loading, empty, ready, error, offline and policy-blocked.

**D4 qualification** — Windows 11: installer-free debug UI and Tauri WebView2 packaging; input, keyboard, focus, screen readers, scaling at 100/125/150/200%, high contrast, light/dark, offline boot, clean exit, crash recovery, no network. Run exact head tests. macOS follows after separate platform evidence.

**D5 release decision** — app identity and artifact hashes, code-signing/install contracts, dependency audits and independent release authorization. No automatically enabled telemetry, PHI, diagnosis, EHR write or auto-update.

## Engineering rules

- Use **Rust-first** trusted commands. Python is canonical for Workspace/Research, only via independently approved versioned interfaces, not arbitrary Python imports/commands.
- If using **Tauri 2 + React + Vite**, keep static assets bundled locally. Avoid Next.js unless a proven desktop-specific requirement outweighs its extra configuration. Don't start a second unrelated app while D1 candidate already exists.
- Security contract enforced in native layer, never just disabled React buttons.
- No generic shell execution, arbitrary filesystem scope, live HTTP API, remote scripts, browser navigation, or automatic model downloads.
- Optional Sidecar only with allowlisted exact binary/version, process supervision, offline controls, bounded IPC, permission scope, and audit.
- Do not delete D2 native egui experiment because the new UI looks nicer; compare as different, evidence-bearing tracks.
- Clear user labels: "Synthetic only", "Foundation available", "Preview", "Blocked — separate authorization required".
- No fabrication of patient records, model outputs, performance scores or release status.

## Acceptance criteria

- Desktop visual screenshots in **dark and light**, at 1280×800, 1440×900 and 1920×1080, with checks for overflow/overlap.
- All routes feature inventory linked to source module or explicit gate; zero misleading "ready" statuses.
- 36 token contrast checks pass; full browser and native WCAG/assistive technology passes as applicable.
- D1/D2 security regression suite remains green, and unchanged constraints are documented.
- Test all four synthetic E2E journeys defined in `FEATURE_COVERAGE.md`.
- Independent owner acceptance for finalized MedOrigin logo typography and icon in a real desktop build.
- No release/publish/clinical claims until separately authorized.

**Paper Desktop MCP:** optional for Inkling if it is installed in its environment. Import the token roles/screens and use Paper to refine frames, spacing, and component variants; keep the source implementation and security boundary in Git, and do not turn screenshots into uneditable implementation.
