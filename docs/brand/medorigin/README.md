# MedOrigin — Overlap Forward visual identity

**Decision:** Founder selected the Overlap Forward concept (orange circular origin, two black forward-leaning strokes and an orange separated chord).

**Status:** Approved *concept*, engineering-ready vector/raster implementation, pending final optical review in Inkling. Branding does not change current medical/research authorization.

## Scope

MedOrigin remains its own product identity. Minaret is the intended future open-health umbrella, not a current software company imprint to add into installers. The two brands are aligned through restrained geometric composition, black/white core, carefully controlled pixel/motif language and a shared supporting pastel palette — not by reusing the Minaret M as MedOrigin's icon.

Current MedOrigin slogan: **Every medical AI output deserves an origin.**

Future Minaret slogan: **Open Health, Built Together.**

## Source of truth

- [Current brand assets](../../../assets/brand/medorigin/) — editable SVG master artwork, desktop ICO/ICNS, transparent and containerized PNG icons, token files
- [Inkling developer handoff](INKLING_HANDOFF.md) — implementation mapping and acceptance criteria
- [Design and compatibility decisions](../../BRAND_TRANSITION.md) — existing historical Python names are retained
- [Minaret canonical brand](https://github.com/AbdulazizShehri/Minaret/blob/main/BRAND.md) — company design system reference (the repository may require account access)

## Identity rules

1. Do not alter the approved outline of the Minaret corporate mark or wordmark.
2. Do not switch MedOrigin's orange symbol to a generic health cross or clinical bar-chart motif. The characteristic negative-space slit and forward direction are integral.
3. Render the primary product mark at full aspect ratio and maintain clear space at least **0.25× mark height**.
4. Use the black/orange mark on light backgrounds, the orange/white-strokes mark on dark backgrounds, and the contained charcoal desktop icon for Windows taskbar / Start / installer.
5. Keep wordmark in the shipped SVG paths, not user-selected fallback type.
6. Do not show **Part of Minaret** in today's app surfaces; reserve endorsement for a future explicit launch decision.
7. No assertions of clinical certification, patient-data readiness, autonomous medical decision-making, or finalized desktop implementation are permitted by this identity work.

## Color mapping

| Role | Color | Hex |
| --- | --- | --- |
| Product accent | MedOrigin Orange | `#FF6400` |
| Primary type | Minaret/MedOrigin Ink | `#0B0B0B` |
| Dark product surface | Night | `#101214` |
| Light product surface | Warm Paper | `#F8F8F5` |
| Supporting surface | Mist | `#E8ECEB` |
| Future Minaret supporting accent | Pink | `#FFC2EA` |
| Future Minaret supporting accent | Blue | `#A6DBFF` |
| Future Minaret supporting accent | Mint | `#C3F0BF` |

Orange is a product identifier; do not recolor the Minaret company M orange.

## Regeneration

The logo wordmark is exported as outlines from the SIL Open Font License family **Inter Light**. No font binaries are distributed or checked in. The committed SVGs are the primary reusable masters.

To rebuild all exported formats, run `docs/brand/medorigin/build_assets.py` with a locally available, properly licensed Inter Light font file. The initial builder used Fontsource Inter 5.3.0's 300-weight Latin WOFF2 and the available Python FontTools/Pillow plus a local SVG rasterizer.

The generator is a development utility: no network request or font asset is needed to **consume** the already checked-in SVG/PNG/ICO/ICNS output.

**Reference:** the user-supplied October 2026 Overlap Forward image. The master is a precise geometric reconstruction and should be visually approved side-by-side with that reference, not misrepresented as its original vector source.
