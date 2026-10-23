"""Lock the founder-approved MedOrigin Concept 01 geometry in the source repo."""

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets" / "brand"
SVG = "{http://www.w3.org/2000/svg}"


def _read_asset(name: str) -> ET.Element:
    return ET.parse(ROOT / name).getroot()


def test_two_visible_strokes_and_transparent_third_slash() -> None:
    icon = _read_asset("medorigin-symbol.svg")
    strokes = [e for e in icon.iter(f"{SVG}g") if e.get("stroke") == "#202020"]
    assert len(strokes) == 1
    lines = strokes[0].findall(f"{SVG}path")
    assert [p.get("d") for p in lines] == [
        "M68 78 L110 198",
        "M99 78 L141 198",
    ]
    assert strokes[0].get("stroke-width") == "8.5"
    clips = list(icon.iter(f"{SVG}clipPath"))
    assert len(clips) == 1
    disc = clips[0].find(f"{SVG}circle")
    assert disc is not None
    assert (disc.get("cx"), disc.get("cy"), disc.get("r")) == (
        "209",
        "128",
        "79",
    )
    filled = [g for g in icon.iter(f"{SVG}g") if g.get("fill") == "#FF6A00"]
    assert len(filled) == 1
    assert filled[0].get("clip-path") == "url(#mo-disc)"
    assert len(filled[0].findall(f"{SVG}path")) == 2
    guidance = (ROOT / "README.md").read_text(encoding="utf8").lower()
    assert "two visible" in guidance
    assert "negative-space (transparent) cut" in guidance


def test_all_lockups_share_corrected_mark() -> None:
    for name in (
        "medorigin-lockup-horizontal.svg",
        "medorigin-lockup-stacked.svg",
        "medorigin-app-icon.svg",
        "medorigin-lockup-inverse.svg",
    ):
        root = _read_asset(name)
        clips = list(root.iter(f"{SVG}clipPath"))
        assert len(clips) == 1, name
        assert len(list(root.iter(f"{SVG}circle"))) == 1, name
        dark_or_white_strokes = [
            g for g in root.iter(f"{SVG}g") if g.get("stroke") in {"#202020", "#FFFFFF"}
        ]
        assert len(dark_or_white_strokes) == 1, name
        assert len(dark_or_white_strokes[0].findall(f"{SVG}path")) == 2, name
