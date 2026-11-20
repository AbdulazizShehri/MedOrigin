# MedOrigin Desktop Theme UX — verification record

**Date:** 2026-11-03 (Asia/Riyadh)
**Scope:** standalone HTML design preview + theme specification only. No MedOrigin desktop binary, Python Workspace, or native Rust source changed.

## Evidence
- `python test_tokens.py`: **36/36** dark/light foreground and background pairs >= 4.5:1 WCAG AA contrast.
- `node test_preview.cjs`: **PASS** in Microsoft Edge / Playwright-core on Windows, for 390, 768, 1024, 1280, 1440, 1920 pixel widths. Verified: initial dark theme; switching to light; System preference removes explicit override; sidebar navigation; no-match search; FHIR filter; no JS page exceptions; no horizontal overflow.
- `design-only-dark.png`, `design-only-light.png`, `design-only-mobile.png` are screen captures of **the static design preview**. They do not show a real connected MedOrigin app.
- Source inspection against `README.md`, `apps/workspace/README.md`, `specs/medscale-clinical-workspace-v1/capability_map.md` and recent D1 Tauri / D2 egui PRs informed `FEATURE_COVERAGE.md`.

## Limits
- These checks do **not** demonstrate complete backend integration, native Windows app UIA, Tauri parity, model execution, real clinical validation, PHI support, released desktop packaging, or real Paper MCP usage.
- Brand PR #868 is still under founder optical review; this preview uses a simple orange indicator, not an approved final logo.
- A future real product build needs the actual Rust/Tauri security gates, input focus and screen-reader tests, offline packaging tests and per-feature synthetic E2E receipts.
