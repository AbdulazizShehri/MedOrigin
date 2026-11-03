# MedOrigin Desktop v1 — Slice 4 | Fictional provenance links

**Source checkpoint:** Slice 3 PR #885 `b9937eb7f9d76a9245b83a34b01f14eb5a979faf`.
**Nature:** private nonpublishing synthetic-only test branch stacked on #885; no `main`, Ink, Slice 2, D1/D2 or Python Core files changed.

## New capability

The sixth typed, allowlisted native Tauri/Rust command `inspect_fictional_fixture_lineage` uses the **four fixed compile-time fictional fixtures only**. For a selected fixture, it returns direct incoming/outgoing relationships and versioned SHA-256/byte-length provenance for every directly related fixture. The graph's four pinned examples are two explicit fictional resource references and two fictional Bundle membership pointers. **No general patient graph or FHIR validation claims.**

- Every source fixture passes Slice 3 strict JSON duplicate-key, identity, Bundle and synthetic-reference checks before lineage is built. JSON Pointer locations are **static Rust constants** resolved against the committed fictional bytes; no user-provided pointers, paths, URLs, content, network or Python sidecar.
- Relationships: AllergyIntolerance → Patient (`/patient/reference`), Observation → Patient (`/subject/reference`), Bundle → Patient (`/entry/0/resource`), Bundle → Observation (`/entry/1/resource`). UI filters to only edges touching the currently selected focus.
- Each node includes its exact fixture ID/type/byte length/SHA-256. Responses advertise `scope=FOUR_PINNED_SYNTHETIC_FIXTURES`, `synthetic_only=true`, `fhir_semantics_validated=false`, `release_authorized=false`.
- React refuses unknown nodes, mismatched hashes, extra/malformed edges, changed expected pointers, duplicates, and any attempt to claim clinical authorization. It shows links only after successful native SHA verification and an **explicit** Inspect action.
- Selecting a related fictional fixture clears the previous verified state. A new explicit native verify is required before reading its source, structural subset or lineage. No network links, navigation outside the exact four fixtures, real data, EHR access, model inference, or persistence.
- The UI unambiguously labels the result `FICTIONAL PROVENANCE LINKS VERIFIED` and says it is not full patient graph coverage, not FHIR validation and not clinically authorized.

## Checks (Windows, 2026-11-03 Asia/Riyadh)

| Gate | Outcome |
| --- | --- |
| Rust `cargo test --locked` | **21/21 PASS**, including forged/nonlocal JSON pointer, nested duplicate rejection, pinned SHA and blocked unknown/oversize fixture IDs |
| Rust `cargo clippy --all-targets -- -D warnings` and `cargo fmt --check` | **PASS** |
| TypeScript, Vite production build | **PASS** |
| Vitest / React Testing Library | **55/55 PASS**, positive navigation, unauthorized flag, forged edge, wrong SHA and duplicate node negatives |
| Playwright in installed Microsoft Edge | **46/46 PASS**, including click-through/re-verification, keyboard/theme/a11y/visual browser checks |
| Four checked-in fictional byte goldens | **4/4 PASS**, no CRLF mutation |
| `npm audit --omit=dev --audit-level=high` | **PASS, zero reported production NPM vulnerabilities** in this isolated frontend dependency set |
| `cargo deny check` | **PASS** with inherited duplicate-crate/license-unused warnings; no new Rust dependency |
| Real Tauri CLI embedded-frontend debug executable + Windows UIA | **PASS** on final tree: native Rust golden verification, source viewer, strict structural subset and four-example provenance; dark/light screenshots at logical 1280×800 and 1440×900, 125% DPI |

## Hard blockers (do not weaken)

- **WebView2 native outbound network egress is still an observed NO-GO** (tracking [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662)). Frontend navigation limits/CSP do NOT imply zero egress. This work does not modify global Windows firewall, system policies, WebView2 binaries, or machine-wide rules. No PHI, EHR, patient clinical use, release or signed installer.
- The four objects are explicitly fictional. Their byte identity and four expected relationships **do not validate FHIR R4 semantics or clinical data**. No connection to MedOrigin Python Research Core, clinical Workspace, models, or external systems.
- Native macOS/Linux and additional DPI settings/1920×1080 on physical Windows, independent EGM Goldfish review and specialist security review are **NOT RUN**.
- A passing local `npm audit` or `cargo deny` does **not** override outstanding GitHub default-branch security alerts or production release gates.
- Brand PR #868 still requires founder optical approval; rejected PR #866 is not integrated.
- Draft stacked PR only. No merge, package installation/publishing, public distribution, training or clinical readiness.

**Next gate:** secure native host network confinement or qualify an alternative browserless D2 host without losing app functionality; only after separate documented review consider any general local data adapters.
