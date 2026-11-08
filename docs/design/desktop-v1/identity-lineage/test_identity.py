"""Static, dependency-free verification of the Lineage identity SVG set."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
svg_dir = root / "svg"
SVG = "{http://www.w3.org/2000/svg}"
BRAND = {"#FE681B", "#0B0C0C", "#101313", "#FAF9F6", "#FFFFFF", "#A6DBFF", "#C3F0BF", "NONE"}
expected = {
    "lineage-mark.svg", "lineage-mark-on-dark.svg", "lineage-mark-mono-ink.svg",
    "lineage-mark-mono-white.svg", "lineage-favicon.svg", "lineage-app-icon-dark.svg",
    "lineage-app-icon-orange.svg", "lineage-lockup-horizontal.svg",
    "lineage-lockup-horizontal-on-dark.svg", "lineage-lockup-stacked.svg",
}
found = {p.name for p in svg_dir.glob("*.svg")}
assert found == expected, f"SVG set mismatch: missing {expected - found}, extra {found - expected}"

for name in sorted(expected):
    tree = ET.parse(svg_dir / name).getroot()
    assert tree.tag == SVG + "svg", f"{name}: root is not <svg>"
    assert re.fullmatch(r"0 0 \d+ \d+", tree.get("viewBox", "")), f"{name}: missing viewBox"
    assert tree.find(f".//{SVG}text") is None, f"{name}: live <text> found; wordmark must be outlined"
    for el in tree.iter():
        for attr in ("fill", "stroke"):
            value = el.get(attr)
            if value and value.upper() not in BRAND:
                raise AssertionError(f"{name}: off-brand {attr} {value}")
    if name.startswith("lineage-mark") or name.startswith("lineage-app-icon-dark") or name.startswith("lineage-lockup"):
        if "mono" not in name:
            assert any(el.get("fill", "").upper() == "#FE681B" for el in tree.iter()), f"{name}: orange root missing"

readme = (root / "README.md").read_text(encoding="utf-8")
for relative in re.findall(r"\]\(([^)]+)\)", readme):
    assert (root / relative).is_file(), f"README.md: missing local link {relative}"

print(f"PASS: {len(expected)} Lineage SVGs parse, outlined, on-brand; README links resolve")
