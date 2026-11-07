# MedOrigin Completion Ledger

Execution tool for finishing MedOrigin. Each row records evidence that you can check in the repository, in CI or in issues. A row is **complete** only after its code, tests and real-application verification all exist. Documents alone do not count.

- **Integration branch:** `integration/medorigin-product-20261108`. It merges Core tip `14e214a` (PR #939) with Desktop tip `bc48904` (PR #984). Both stacks branch from `main` `dd84bb7` and change no paths in common.
- **Readiness level reached:** none of the three levels yet. Level 1 (developer candidate) is in progress. Levels 2 (user beta) and 3 (clinical) are **not** started and need external gates.
- **Publication:** not authorized. There is no release, tag, public installer or website deploy until the founder gives the GREEN LIGHT.
- Last updated: 2026-11-08.

States: `complete` · `partial` · `missing` · `blocked` (blocked means an external or founder dependency).

| Area | Capability | State | Evidence | Remaining work (smallest next task) | Acceptance | Owner | Dependency | Release impact |
|---|---|---|---|---|---|---|---|---|
| QA | One integrated Core + Desktop branch | partial | merge commit on integration branch; draft PR CI | Retire the reverse-stacked PR chains (300 open PRs) by pointing new work at the integration branch only | Integration PR CI is green on its exact head | Claude | none | blocking |
| Desktop | Design-token system (light/dark, type, spacing, AA contrast) | partial | `experiments/desktop-d2-native-egui/src/theme.rs`; `theme::tests` WCAG checks; `evidence/design-system-20261108/*.png` | Replace about 40 remaining ad-hoc `RichText` sizes and colours in `app.rs` with tokens | `rg "Color32::from_rgb" src/app.rs` returns 0; screenshots in both modes | Claude | none | blocking |
| Desktop | Settings: appearance, privacy facts, version | partial | `settings_help_ui` in `app.rs`; real-app screenshots | Add accessibility (text scale) and import options once the import scope is defined | Settings opens with F1 or the button; theme switches live | Claude | none | blocking |
| Desktop | Report an issue (sanitized, user-initiated) | partial | `src/support.rs` and its tests; `.github/ISSUE_TEMPLATE/desktop_bug_report.yml` | Link the issue form from the failure dialogs | Diagnostics hold only allowlisted fields; nothing is sent automatically | Claude | none | non-blocking |
| Desktop | Information architecture (Home, Records, Timeline, Review, Reports, Settings) | missing | Today's home screen is a developer evidence page (`app.rs` `ui()`) | Add a navigation rail. Move developer fixtures behind a "Developer evidence" view. Make Records the default view when a bundle is loaded | Every navigation item reaches a working screen; there are no dead ends | Claude | none | blocking |
| Desktop | First-run onboarding | missing | none | Add a short first-run panel: what the app does, the fictional-only scope, and how to open a bundle | Shown once per session at most and dismissible; it never blocks the workflow | Claude | none | blocking |
| Desktop | Window title / product identity | partial | The header says "MedOrigin". The OS title is still "MedOrigin Native Rust — …" | Rename to "MedOrigin" and update about 10 UIA/AT-SPI QA scripts that match the old title | Windows UIA and Linux AT-SPI scripts pass with the new title | Claude | Windows runner | non-blocking |
| Desktop | Open and browse a fictional FHIR Bundle (drag-drop, Ctrl+O) | partial | `local_bundle_import.rs`; README; Windows OLE drop QA | Only one canonical fixture is admitted. Define the developer-candidate bundle scope | Admitted bundles open; malformed bundles fail closed (tests exist) | Claude | none | blocking |
| Core | FHIR R4 validation truthfulness | partial | #877, #882; PR #939 | Close #877 and #882 with exact-head evidence after the integration CI | The validator never reports "valid" for an unknown resourceType | Claude | none | blocking |
| Core↔Desktop | The app performs Core operations without a terminal | missing | Today Core is piped in over a one-shot stdin or HMAC session | Design a reviewed in-process or supervised-subprocess bridge. The `browser_free_boundary` guard forbids `Command::new`, so this needs a security ADR | The user imports a bundle into an encrypted workspace from the GUI | Claude + reviewer | security review | blocking |
| Security | Dependabot: 6 critical / 29 high (all `uv.lock`: Pillow, aiohttp, urllib3, certifi, filelock) | partial | security stack `feat/medorigin-security-uv-patched-dependencies-20261105`; #622 | Land the patched `uv.lock` on the integration branch and re-run Core CI | 0 open critical/high alerts that are reachable in the release configuration | Claude | none | blocking |
| Security | Rust advisories (AccessKit/zbus) | blocked | #673 | Wait for upstream fixes, or disposition the advisories for Windows-only builds | `cargo deny check advisories` passes or each advisory has a recorded disposition | Claude | upstream | blocking |
| Security | Desktop network egress proof | partial | #662 (D1 Tauri); D2 has no network crates (`browser_free_boundary.rs`) | Capture packet-level evidence for the D2 Windows build | No outbound packets during a full journey | Claude | Windows host | blocking |
| Installer | Windows per-user setup, Start Menu, uninstall | partial | PRs #997, #1008, #1009 (unsigned, private) | Rebase #1008/#1009 onto the integration branch. Fix the Windows CI failure on #1008 | Install, launch, upgrade and uninstall pass on a clean profile | Claude | none | blocking |
| Installer | Authenticode signing | blocked | none | Founder decision on buying a certificate (paid) | Signed EXE verifies with `signtool verify /pa` | Founder | paid cert | blocking for public release |
| Accessibility | macOS VoiceOver | blocked | #676 | Run a VoiceOver review on real macOS | VoiceOver reads every control | Reviewer | macOS host | blocking |
| Website | medscale.si reflects real product and screenshots | missing | none | Audit the site and prepare changes privately | Site claims match this ledger; screenshots come from qualified builds | Claude | founder approval to deploy | non-blocking for engineering |
| Clinical | Real patient data | blocked | none | External security, privacy, legal and regulatory review | Independent sign-off | External | external | blocking for level 2+ |

## Next actions (in priority order)
1. Get integration PR CI green, then confirm that Core and Desktop CI both run on the merged head.
2. Desktop information architecture: add a navigation rail and move developer evidence out of the home screen.
3. Land the patched `uv.lock` (critical/high alerts).
4. Rebase the installer PRs (#1008, #1009) onto the integration branch.
