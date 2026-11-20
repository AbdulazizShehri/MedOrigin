# MedOrigin identity — Lineage

**Status:** selected by the owner on 2026-11-08 from six candidate directions. It replaces Overlap Forward v2 (PR #868) as the desktop mark candidate. Design-only: no shipped app or release uses it yet.

## Meaning

Every claim traces back to one root.

- **Orange root** — the source record.
- **Ink node** — MedOrigin's check between source and output.
- **Blue and mint leaves** — what grows from the source (Minaret blue `#A6DBFF`, Minaret mint `#C3F0BF`).

## Construction

120-unit grid, centered on x 60.

| Part | Spec |
|---|---|
| Root | circle r 16 at (60, 98), Origin Orange `#FE681B` |
| Node | circle r 9 at (60, 62), Ink `#0B0C0C` |
| Leaves | circles r 14 at (30, 28) and (90, 28), 7-unit ink ring |
| Branches | 8-unit stroke, round caps and joins, about 41° off vertical |

At 64 px and below the middle node drops and strokes thicken; at 32 px and below the leaves go solid ([favicon](svg/lineage-favicon.svg)).

## Files

| File | Use |
|---|---|
| [lineage-mark.svg](svg/lineage-mark.svg) | Full color on light surfaces |
| [lineage-mark-on-dark.svg](svg/lineage-mark-on-dark.svg) | Full color on dark surfaces |
| [lineage-mark-mono-ink.svg](svg/lineage-mark-mono-ink.svg) | One color: print, stamps, embossing |
| [lineage-mark-mono-white.svg](svg/lineage-mark-mono-white.svg) | One color reversed |
| [lineage-favicon.svg](svg/lineage-favicon.svg) | 16–32 px |
| [lineage-app-icon-dark.svg](svg/lineage-app-icon-dark.svg) | App icon, default |
| [lineage-app-icon-orange.svg](svg/lineage-app-icon-orange.svg) | App icon, alternate |
| [lineage-lockup-horizontal.svg](svg/lineage-lockup-horizontal.svg) | Mark + wordmark on light |
| [lineage-lockup-horizontal-on-dark.svg](svg/lineage-lockup-horizontal-on-dark.svg) | Mark + wordmark on dark |
| [lineage-lockup-stacked.svg](svg/lineage-lockup-stacked.svg) | Stacked lockup |

The wordmark is lowercase "medorigin" in Instrument Sans Medium (SIL Open Font License), converted to outlines, so the lockups do not need the font installed. Kerning pairs were not applied; spacing may want an optical pass.

## Rules

- Do not add "Part of Minaret" or a Minaret endorsement to current branding.
- Keep the root orange in every full-color use; it is the one element that must not change color.
- Do not recolor the leaves to orange or place the full-color mark on orange; use the orange app icon variant instead.

Verification: `python docs/design/desktop-v1/identity-lineage/test_identity.py` checks every SVG parses, has a viewBox, contains no live text, and uses only brand colors.
