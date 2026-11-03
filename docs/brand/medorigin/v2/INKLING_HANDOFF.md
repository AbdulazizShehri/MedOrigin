# MedOrigin — Overlap Forward v2 | Inkling handoff

**Status:** Candidate for visual approval; not a final released brand asset. This branch supersedes rejected PR #866; do not integrate assets from that PR.

## Start here

- [Reference comparison and visual board](../../../../assets/brand/medorigin/v2/): generated artwork plus the founder-supplied reference in the separate downloadable kit.
- Canonical editable SVG: `assets/brand/medorigin/v2/masters/`
- Windows multi-resolution ICO: `assets/brand/medorigin/v2/icons/windows/MedOrigin.ico`
- macOS ICNS: `assets/brand/medorigin/v2/icons/macos/MedOrigin.icns`
- PNGs (16/20/24/32/40/48/64/96/128/256/512/1024): `assets/brand/medorigin/v2/icons/png/`
- JSON/CSS color values: `assets/brand/medorigin/v2/tokens/`
- Regeneration source: `docs/brand/medorigin/v2/generate.py`

## Identity direction
MedOrigin has a separate orange symbol: two dark leaning strokes; a thin orange chord; a partial orange disc. The lightweight wordmark is outlined SVG vectors and is not the Minaret company wordmark. Use flat black and paper for body, orange as a primary accent. Shared Minaret pastel pink/blue/mint tokens are available for a future ecosystem system, but **not** for recoloring the MedOrigin icon.

## Immediate Inkling steps
1. Identify the actual desktop stack before editing any package manifests. Never guess Electron, Tauri or WPF.
2. Map the new Windows ICO into the executable icon, installer resource, taskbar, Start-menu shortcut and tray as applicable.
3. Use the SVG lockup in title bar / About / splash, not a system-font substitute.
4. Test 16/20/24/32px icon at 100/125/150/200% Windows scaling, including dark/high-contrast mode.
5. Show founder **actual** screenshots from the running desktop app before declaring the identity complete.
6. Respect app scientific/research gates. Keep legacy `medscale` Python distribution/CLI/serialized interfaces unchanged until separately migrated. Do not imply patient-data readiness, diagnosis or EHR write capability.
7. **Do not ship** desktop installers or publish/release solely because artwork and asset formats exist.
8. **No current 'Part of Minaret' imprint**; Minaret is a future parent company concept.

## Design precision
These are clean, editable SVG reconstructions informed by the user's selected *raster* reference, not the original authoring vectors. The vector and wordmark still require founder optical approval. The SVGs here were constructed with a thin Inter derivative under the SIL OFL; no font binaries are committed.
