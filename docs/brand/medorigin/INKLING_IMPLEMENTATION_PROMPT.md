# Inkling implementation brief — MedOrigin desktop

Use the MedOrigin asset masters in `assets/brand/medorigin/`. These assets are a vector reconstruction of the user-approved Overlap Forward logo from the October 23 reference.

Current product: **MedOrigin**. Slogan: **Every medical AI output deserves an origin.**

Parent company **Minaret** is a future umbrella; do **not** insert the corporate mark, `Part of Minaret`, or a parent brand tagline into current app UI, installers or packaging. Visual alignment uses disciplined geometry, black/white core, and shared supporting pastel tokens.

## Technical execution

1. Discover the **actual** desktop runtime first. Do not assume Electron, Tauri, WinUI, WPF or Qt without repository evidence.
2. Source logo/wordmark from SVG (do not typeset the wordmark). Use `svg/medorigin-lockup-light.svg` and `svg/medorigin-lockup-dark.svg`.
3. Windows EXE/installer/Start/shortcut icon: `windows/MedOrigin.ico`. macOS bundle: `macos/MedOrigin.icns` only if macOS is supported. Use SVG/PNG in app UI.
4. Product accent is `#FF6400`; main ink `#0B0B0B`; dark surface `#101214`; light `#F8F8F5`. Parent Minaret supporting colors are `#FFC2EA`, `#A6DBFF`, `#C3F0BF`.
5. Preserve unmodified SVG paths, aspect ratio and clear space. No generic health cross, hospital icon, bevel, glow, or extra circular ring.
6. Test title bar, app menu/header, light/dark splash, About, taskbar, Explorer, Start, installer and desktop shortcut.
7. Run scale tests 100%, 125%, 150%, 200%. Confirm 16px and 32px icons are legible. Honor keyboard focus, contrast, reduced motion and platform conventions.
8. Keep legacy Python distribution/CLI `medscale` and reproducible science records unchanged. No mass-renames of scientific artifacts/protocols.
9. Do not add real PHI ingestion, autonomous diagnosis, clinical validation claims, EHR writes, paid cloud, or release actions as part of branding. Synthetic research only unless separately authorized.
10. Hand back actual packaged-app screenshots and test receipts. Do not claim a mocked screen is a shipped feature.

## Acceptance

Logo and wordmark render exactly as committed SVGs; taskbar/installer/EXE icons are embedded; 16–256px size tests and light/dark states pass; keyboard/accessibility checks pass; no current Minaret endorsement; no medical capability or scientific state change. A founder optical review of the reconstructed vector against the original reference is still needed before final signoff.
