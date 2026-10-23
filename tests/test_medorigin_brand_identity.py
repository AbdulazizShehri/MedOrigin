"""Protect the approved MedOrigin Concept 01 reference-derived geometry."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "assets" / "brand"
SVG = "{http://www.w3.org/2000/svg}"
CIRCLE = (
    "M125 307 C138 298.5 152 293.5 164 293.5 "
    "C198 293.5 223.5 321.5 223.5 354 "
    "C223.5 387 199.3 414.5 165 414.5 Z"
)
WEDGE = "M118.8 314.3 L155.7 413.9 Q151.8 413.8 147.3 412.8 L113 322.6 Q115.1 318.4 118.8 314.3 Z"
DARK_LINES = (
    "M74.4 318.2 L107.8 407.4",
    "M94.6 318.1 L128.1 407.3",
)


@pytest.mark.parametrize(
    ("name", "stroke"),
    [
        ("medorigin-symbol.svg", "#202020"),
        ("medorigin-lockup-horizontal.svg", "#202020"),
        ("medorigin-lockup-stacked.svg", "#202020"),
        ("medorigin-app-icon.svg", "#202020"),
        ("medorigin-lockup-inverse.svg", "#FFFFFF"),
    ],
)
def test_mark_matches_approved_reference(name: str, stroke: str) -> None:
    root = ET.parse(ROOT / name).getroot()
    transformed = [
        g for g in root.iter(f"{SVG}g") if g.get("transform") == "translate(-80 -433.6) scale(1.6)"
    ]
    assert len(transformed) == 1, name
    mark = transformed[0]

    orange = [g for g in mark.findall(f"{SVG}g") if g.get("fill") == "#FF6A00"]
    assert len(orange) == 1, name
    assert [p.get("d") for p in orange[0].findall(f"{SVG}path")] == [
        CIRCLE,
        WEDGE,
    ]

    dark = [g for g in mark.findall(f"{SVG}g") if g.get("stroke") == stroke]
    assert len(dark) == 1, name
    assert dark[0].get("stroke-width") == "6.5"
    assert dark[0].get("stroke-linecap") == "round"
    assert tuple(p.get("d") for p in dark[0].findall(f"{SVG}path")) == DARK_LINES

    # No legacy clipped-circle mark, third black stroke or painted white gap.
    assert not list(mark.iter(f"{SVG}clipPath"))
    assert not list(mark.iter(f"{SVG}circle"))


def test_brand_guidance_preserves_filled_wedge() -> None:
    guidance = (ROOT / "README.md").read_text(encoding="utf8").lower()
    assert "two equal charcoal" in guidance
    assert "orange wedge" in guidance
    assert "never overlap" in guidance
