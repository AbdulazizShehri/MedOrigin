# Inkling handoff — MedOrigin desktop identity

## Decision and brand hierarchy
**MedOrigin**: the current product. **Overlap Forward** is the chosen identity.
**Minaret**: future company/umbrella identity only. The official Minaret M and its pastel language inform brand consistency. There is **no current mandatory "Part of Minaret" lockup** in the desktop app.

## Exact files to consume

| Destination | Repo-relative asset |
| --- | --- |
| Windows EXE embedded app icon | `assets/brand/medorigin/windows/MedOrigin.ico` |
| Windows NSIS/MSI installer icon | `assets/brand/medorigin/windows/MedOrigin.ico` |
| Windows Start/taskbar shortcut | `assets/brand/medorigin/windows/MedOrigin.ico` |
| macOS application bundle | `assets/brand/medorigin/macos/MedOrigin.icns` |
| Splash screen / About, light | `assets/brand/medorigin/svg/medorigin-lockup-light.svg` |
| Splash screen / About, dark | `assets/brand/medorigin/svg/medorigin-lockup-dark.svg` |
| Header wordmark only | `assets/brand/medorigin/svg/medorigin-wordmark.svg` |
| Light background icon | `assets/brand/medorigin/svg/medorigin-symbol.svg` |
| Dark background icon | `assets/brand/medorigin/svg/medorigin-symbol-dark.svg` |
| Windows-like UI brand tile | `assets/brand/medorigin/svg/medorigin-app-icon-dark.svg` |
| Theme/style variables | `assets/brand/medorigin/tokens.json` and `tokens.css` |
| Actual icon raster variants | `assets/brand/medorigin/png/app-{dark,light}/` |
| Brand visual contact sheet | `assets/brand/medorigin/preview/overlap-forward.png` |

All these are actual generated files, not placeholders. There are SVG, PNG exports 16–1024 px, ICO and ICNS.

## Tech-specific mapping (use only for the actual selected runtime)

For an **Electron** app, point `win.icon` and the installer `installerIcon` to the ICO. macOS bundle icon uses the ICNS. Keep transparent SVG/PNG for renderer surfaces.

For **Tauri**, populate `bundle.icon` from the generated icon sizes appropriate for the Tauri target and avoid importing Electron-specific metadata. Preserve existing security settings.

For **Windows native / WPF**, set the application assembly `ApplicationIcon` to the ICO, then ensure the window and Start shortcut have the same embedded icon.

Do not silently rewrite desktop runtime/build configuration without identifying the actual stack.

## Required desktop interaction states

- Light and dark headers, title bar, splash/loading, About screen, installer welcome, Windows taskbar and Explorer.
- Readable at 100%, 125%, 150% and 200% Windows scaling, including dark/high-contrast modes.
- Symbol rendered without extrusion, bevel, glow, gradients or additional enclosing rings.
- Body text and interactive controls must pass WCAG AA contrast; prefer dark type on orange (`#FF6400`), not small white text on orange.
- Native platform focus and keyboard states; honor reduced motion and accessible labeling.
- User-visible naming is **MedOrigin**; the Python executable / package remains `medscale` until separately migrated with compatibility tests.
- No credentials, PHI, clinical advice, autonomous diagnosis or EHR write authorizations should be inferred from this visual handoff.
- Do not publish installers or change release distribution solely because brand assets are present.

## Implementation acceptance checklist

- [ ] Source SVG displayed unaltered on light and dark.
- [ ] Icon source contains exactly the selected two exterior black slashes, orange third chord, and origin circle.
- [ ] Icon is sharp in Windows Explorer, Start and taskbar; inspect at 16px and 32px, not only in 512px mockups.
- [ ] Packaged installer references exactly the new ICO/ICNS rather than placeholder images.
- [ ] Title and About surfaces use the **outlined wordmark SVG**, not a typed substitute.
- [ ] No visible Minaret endorsement until its future activation.
- [ ] Desktop release and clinical gating remain unchanged.

## Design provenance and status

Logo geometry: recreated as editable vectors from the owner's provided Overlap Forward reference. Its original authoring vector paths were not supplied; do not claim exact original provenance. The current version is technically prepared for Inkling and requires optical approval in its actual desktop UI.

Inter Light 300 for the wordmark outline comes from Fontsource Inter 5.3.0 under SIL Open Font License. Only vector path outputs are committed; **no font files** are redistributed.
