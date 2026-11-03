"""Integrity checks for MedOrigin Overlap Forward desktop brand exports."""
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
B=ROOT/"assets"/"brand"/"medorigin"
REQUIRED=[
 "svg/medorigin-symbol.svg","svg/medorigin-symbol-dark.svg",
 "svg/medorigin-lockup-light.svg","svg/medorigin-lockup-dark.svg",
 "svg/medorigin-wordmark.svg","svg/medorigin-app-icon-dark.svg",
 "svg/medorigin-app-icon-light.svg","windows/MedOrigin.ico",
 "macos/MedOrigin.icns","tokens.json","tokens.css",
 "preview/overlap-forward.png",
]
for rel in REQUIRED:
 p=B/rel
 assert p.exists() and p.stat().st_size>50, f"Missing or empty: {rel}"
for path in (B/"svg").glob("*.svg"):
 root=ET.parse(str(path)).getroot()
 assert root.attrib.get("viewBox"), path
 assert "<script" not in path.read_text(encoding="utf-8").lower()
for mode in ["dark","light"]:
 for n in [16,24,32,48,64,128,256,512,1024]:
  f=B/"png"/("app-"+mode)/f"medorigin-{n}.png"
  with Image.open(f) as im: assert im.size==(n,n) and im.format=="PNG",f
with Image.open(B/"windows"/"MedOrigin.ico") as im:
 assert im.format=="ICO"
 assert {(16,16),(32,32),(48,48),(128,128),(256,256)}.issubset(im.info.get("sizes",set()))
with Image.open(B/"macos"/"MedOrigin.icns") as im:
 assert im.format=="ICNS"
assert not list(B.rglob("*.woff*")) and not list(B.rglob("*.ttf")) and not list(B.rglob("*.otf"))
print("PASS: SVG, PNG 16–1024, Windows ICO, macOS ICNS, no font binary leakage")
