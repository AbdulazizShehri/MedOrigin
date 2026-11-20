# MedOrigin desktop architecture decision — November 3, 2026

## Decision: preserve current experimental tracks, add a qualification-gated UX layer

**Preferred long-term product UI:** Tauri 2 (Rust host) + React + TypeScript + **Vite** with local bundled assets. Why Vite: a desktop webview does not require Next.js SSR, API routes, or a Node server. The official Tauri frontend guide recommends Vite for SPA React and requires static export when choosing Next.js. This avoids a permanent Node/Next server in the installer.

**Not a rewrite order.** There are two existing experimental desktop tracks, and both remain valuable:

- **D1 Tauri**: bounded synthetic FHIR fixture inspection and native IPC handshakes, with explicit safeguards and Windows UIA tests.
- **D2 native Rust/egui**: browser-engine-free, local fictional JSON/FHIR inspection; independently validated with real OS accessibility harnesses. D2 is expressly *not a replacement* for D1 or Python.
- **Canonical Python**: Research Core in `src/medscale`, Clinical Workspace in `apps/workspace`. Never force-migrate or relabel their source, packages, frozen scientific records, or serialization.

The Tauri+React frontend is a **separate choice** to evaluate for product-level polish. It may replace the D1 presentation layer **only** after equivalent permissions, offline behavior, forged bridge negatives, fixture identity checks, and accessibility evidence exist. Do **not** delete or rebaseline D1/D2 to justify a preferred aesthetic.

## Proposed responsibility boundaries

```
React/Vite UI (presentation and local app preferences)
     |
     | strongly typed, allowlisted Tauri invoke commands
     v
Rust application boundary (input validation, file scope, revisions, resources)
     |                            |
     | read-only versioned APIs   | explicit optional, separate user action
     v                            v
Synthetic Workspace Python     Offline model/Python sidecar (FUTURE / gated)
     |
     X  No PHI/workspace-to-Research Core backflow
     |
Read-only Research artifact views (versioned evidence)
```

**Do not expose a generic `run-command`, arbitrary path, shell, or dynamic Python module import** to the UI. The Rust command interface must be explicit: `get_workspace_status`, `list_synthetic_encounters`, `get_fixture_provenance`, `validate_synthetic_fhir`, `get_audit_events`, etc. These are example contract names, not assertions of implemented commands.

The host must enforce independent authz/allowlists and fail closed. Frontend disabled controls are not security controls. Sidecars, if qualified, are explicitly opted in, versioned, bounded, supervised, and restricted to local/offline resources. No default model download, listener, analytics, updater, ambient recording or EHR credentials.

## Frontend and user experience

- **React + TypeScript + Vite**, with TanStack Query for bounded async queries only if it improves cache consistency.
- **Tailwind CSS + shadcn/ui** as source-controlled primitives, not a frozen external design system; wrap into MedOrigin roles and keyboard-accessible controls.
- Theme roles from `tokens.json` / `tokens.css`: Dark, Light, System; support density compact/comfortable. Never inline hex colors in feature components.
- Left sidebar 244 px; title/command bar 52 px; main center column; optional 320 px right inspector for provenance. Splitters must be keyboard-accessible if exposed.
- Global search and command palette only for **real, authorized** app routes/actions; omit disabled actions or label as blocked with reason.
- Navigation and panel state stay local; never persist medical fixture contents in frontend logs, localStorage, crash telemetry or browser caches.
- Use brand orange sparingly (active nav indicator, primary CTA, provenance selection). Don't turn every card orange.
- Typography: 13–14 px operational body, 16 px section title, 22 px page heading. Keyboard focus and minimum 44 px click targets.

## Security gates

1. No real PHI, production clinical use, autonomous diagnosis, billing or EHR writes without separately approved policies.
2. Window content restrictions: no remote URL navigation, JS injection, arbitrary popups, unapproved HTTP or automatic cloud fallback.
3. Research Core remains a read-only/versioned data source for the UI. No Workspace-derived content enters training/benchmarks.
4. Native permissions have least privilege. File picker and clipboard require purpose-bound user intent. No default filesystem broad scope.
5. Windows WebView2 runtime availability/packaging needs explicit offline validation. macOS and Linux are separately qualified, not inferred.
6. Runtime and Rust/Python dependency license/advisory policies must pass. Do not loosen D2 browser-free invariants by forcing it to host Tauri.
7. Test all desktop installers offline, including first run, backup/restore, errors, safe uninstall and upgrades. Never publish solely because the UI builds.

## Decision checkpoints

- **C0:** snapshot exact current Tauri D1 and native egui D2 heads; record tests and capability boundaries.
- **C1:** implement a *design-only* Tauri+React shell with fixtures and disabled-state labels; compare look/feel and performance against egui.
- **C2:** bind ONE versioned Rust read-only command; negative tests for spoofed result, blocked paths, timeout, malformed payload, no network.
- **C3:** migrate routes incrementally only with parity receipts for each original capability.
- **C4:** full synthetic E2E feature matrix; Windows UIA and real application package startup.
- **C5:** platform-specific security, accessibility, dependency, build reproducibility, and independent release decision.

There is no claim here that the full desktop app or clinical deployment is ready. The goal is to preserve all *authorized* functional scope while improving professional desktop UX.

## Source anchors

- `README.md` and `apps/workspace/README.md` in MedOrigin
- `specs/medscale-clinical-workspace-v1/capability_map.md`
- `docs/architecture/rust_first_desktop_transition.md` on the original Rust-first proposal branch
- `experiments/desktop-d2-native-egui/README.md` in recent D2 branch
- https://v2.tauri.app/start/frontend/
- https://v2.tauri.app/start/frontend/nextjs/
- https://v2.tauri.app/develop/sidecar/
- https://linear.app/now/how-we-redesigned-the-linear-ui
- https://linear.app/now/behind-the-latest-design-refresh
