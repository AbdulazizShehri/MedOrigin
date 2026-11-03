# MedOrigin Desktop — Inkling design contract v1

This folder is a **design-system and architecture handoff**, not a finished application or an authorized clinical product.

**Start:** open [preview.html](preview.html) on a local machine to compare Dark/Light/System and inspect the proposed visual style. Its navigation and search are UI-only, and its data is explanatory, not actual clinical data.

- [Contrast-tested theme tokens](tokens.json) and [CSS roles](tokens.css)
- [Full feature-to-screen matrix](FEATURE_COVERAGE.md)
- [Architecture decision / existing desktop experiments](ARCHITECTURE.md)
- [Inkling implementation prompt and test gates](INKLING_HANDOFF.md)
- [Theme verification](test_tokens.py)

**Design logic:** preserve the orange Overlap Forward identity (currently a separately reviewed draft) and Minaret's shared precision; borrow Linear's usability principles, not a color-exact copy. Neutral canvas and precise visual hierarchy let medical evidence, warnings, citations and status take priority.

**Important:** `main` is a Python research foundation, and D1 Tauri + D2 native Rust egui experimental tracks exist in separate PR stacks. The delivery target is a future app with every authorized capability mapped and qualified. Do not replace or bypass those tracks without explicit, tested migration approval.

Verification:

```powershell
python docs/design/desktop-v1/test_tokens.py
```

The test asserts 36 light/dark text/surface combinations have >= 4.5:1 contrast and that CSS variables match the JSON contract. This does **not** validate native screens, real app performance, clinical workflows, or release readiness.

## Visual QA preview captures
[Dark UI](design-only-dark.png) / [Light UI](design-only-light.png) / [Mobile](design-only-mobile.png). These show a design-only prototype, not a connected desktop application. See [QA report](QA_REPORT.md).
