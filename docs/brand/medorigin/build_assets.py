"""MedOrigin approved Overlap Forward: deterministic vector / desktop asset exporter.
For the initial build use an OFL-licensed Inter Light font as input. The
wordmark is exported as SVG paths; NO font binaries are added to the repo.
Future exports use the committed SVG masters as the source of truth.
"""
from pathlib import Path
from xml.etree import ElementTree as ET
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from PIL import Image,ImageDraw,ImageFont
import io,sys,json,subprocess,os
SHARP=Path(os.environ["TEMP"])/"medorigin-brand-tools"/"node_modules"/"sharp"
def png_bytes(svg,width,height=None):
    js="const sharp=require(process.argv[1]);const fs=require('fs');const d=fs.readFileSync(0);sharp(d).resize({width:Number(process.argv[2]),height:process.argv[3]==='null'?undefined:Number(process.argv[3]),fit:'fill'}).png().toBuffer().then(x=>process.stdout.write(x)).catch(e=>{console.error(e);process.exit(1)})"
    cmd=["node","-e",js,str(SHARP),str(width),str(height) if height is not None else "null"]
    proc=subprocess.run(cmd,input=svg.encode(),capture_output=True,check=True)
    return proc.stdout

ORANGE="#FF6400";INK="#0B0B0B";WHITE="#FFFFFF";NIGHT="#101214";PAPER="#F8F8F5"
PINK="#FFC2EA";BLUE="#A6DBFF";MINT="#C3F0BF";MIST="#E8ECEB"
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"assets"/"brand"/"medorigin"
S=OUT/"svg";S.mkdir(parents=True,exist_ok=True)
font=TTFont(sys.argv[1]); cmap=font.getBestCmap(); gs=font.getGlyphSet(); hm=font["hmtx"].metrics
def sv(w,h,x):return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">{x}</svg>'
def art(o=ORANGE,b=INK):
 return f'<defs><clipPath id="disc"><circle cx="194" cy="125" r="103"/></clipPath></defs><g clip-path="url(#disc)" fill="{o}"><path d="M141,-10 H325 V261 H223 Z"/><path d="M112,-10 H130 L205,261 H188 Z"/></g><path d="M37,56 L91,208 M81,56 L135,208" fill="none" stroke="{b}" stroke-width="12" stroke-linecap="round"/>'
def word_path(color=INK):
 pos=0;glyphs=[];scale=155/font["head"].unitsPerEm
 for ch in "MedOrigin":
  name=cmap[ord(ch)]; pen=SVGPathPen(gs);gs[name].draw(pen);path=pen.getCommands()
  if path:glyphs.append(f'<path d="{path}" transform="translate({pos},0)"/>')
  pos+=hm[name][0]
 return f'<g transform="scale({scale},-{scale})" fill="{color}">{"".join(glyphs)}</g>',round(pos*scale+24)
def icon(mode):
 dark=mode=="dark";bg=NIGHT if dark else PAPER;st=WHITE if dark else INK
 edge='' if dark else '<rect x="1" y="1" width="254" height="254" rx="51" fill="none" stroke="#D0D6D3" stroke-width="2"/>'
 return sv(256,256,f'<rect width="256" height="256" rx="52" fill="{bg}"/>{edge}<g transform="translate(12,31) scale(.77)">{art(ORANGE,st)}</g>')
def lock(mode):
 p,_=word_path(WHITE if mode in ("dark","mono-white") else INK)
 orange=INK if mode=="mono-black" else WHITE if mode=="mono-white" else ORANGE
 slashes=WHITE if mode in ("dark","mono-white") else INK
 bg=f'<rect width="1210" height="270" fill="{NIGHT}"/>' if mode=="dark" else ""
 return sv(1210,270,bg+f'<g transform="translate(16,25) scale(.91)">{art(orange,slashes)}</g><g transform="translate(300,170)">{p}</g>')
wp,ww=word_path()
wpw,ww2=word_path(WHITE)
ASSETS={
 "medorigin-symbol.svg":sv(300,250,art()),
 "medorigin-symbol-dark.svg":sv(300,250,art(ORANGE,WHITE)),
 "medorigin-symbol-mono-black.svg":sv(300,250,art(INK,INK)),
 "medorigin-symbol-mono-white.svg":sv(300,250,art(WHITE,WHITE)),
 "medorigin-wordmark.svg":sv(ww,185,f'<g transform="translate(12,145)">{wp}</g>'),
 "medorigin-wordmark-white.svg":sv(ww,185,f'<g transform="translate(12,145)">{wpw}</g>'),
 "medorigin-lockup-light.svg":lock("light"),
 "medorigin-lockup-dark.svg":lock("dark"),
 "medorigin-lockup-mono-black.svg":lock("mono-black"),
 "medorigin-lockup-mono-white.svg":lock("mono-white"),
 "medorigin-app-icon-dark.svg":icon("dark"),
 "medorigin-app-icon-light.svg":icon("light")}
for filename,content in ASSETS.items():
 ET.fromstring(content);(S/filename).write_text(content,encoding="utf-8")
def png(src,path,size):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(png_bytes(src,size,size))
for size in [16,24,32,48,64,128,256,512,1024]:
 for mode in ["dark","light"]:png(icon(mode),OUT/"png"/("app-"+mode)/f"medorigin-{size}.png",size)
for size in [64,128,256,512,1024]:
 png(ASSETS["medorigin-symbol.svg"],OUT/"png"/"symbol"/f"medorigin-symbol-{size}.png",size)
(OUT/"windows").mkdir(exist_ok=True);(OUT/"macos").mkdir(exist_ok=True)
ico_sizes=[16,24,32,48,64,128,256]
ims=[Image.open(OUT/"png"/"app-dark"/f"medorigin-{n}.png").convert("RGBA") for n in ico_sizes]
ims[-1].save(OUT/"windows"/"MedOrigin.ico",format="ICO",sizes=[(n,n) for n in ico_sizes])
(OUT/"windows"/"favicon.ico").write_bytes((OUT/"windows"/"MedOrigin.ico").read_bytes())
Image.open(OUT/"png"/"app-dark"/"medorigin-1024.png").save(OUT/"macos"/"MedOrigin.icns",format="ICNS")
TOKENS={"brand":"MedOrigin","logo_direction":"Overlap Forward","umbrella":"Minaret (future only)",
 "colors":{"orange":ORANGE,"ink":INK,"night":NIGHT,"paper":PAPER,"mist":MIST,
           "minaretPink":PINK,"minaretBlue":BLUE,"minaretMint":MINT},
 "desktop":{"windows":"assets/brand/medorigin/windows/MedOrigin.ico",
 "macos":"assets/brand/medorigin/macos/MedOrigin.icns",
 "iconDark":"assets/brand/medorigin/svg/medorigin-app-icon-dark.svg",
 "iconLight":"assets/brand/medorigin/svg/medorigin-app-icon-light.svg"}}
(OUT/"tokens.json").write_text(json.dumps(TOKENS,indent=2)+"\n",encoding="utf-8")
(OUT/"tokens.css").write_text(":root{--medorigin-orange:#FF6400;--medorigin-ink:#0B0B0B;--medorigin-night:#101214;--medorigin-paper:#F8F8F5;--medorigin-mist:#E8ECEB;--minaret-pink:#FFC2EA;--minaret-blue:#A6DBFF;--minaret-mint:#C3F0BF}\n",encoding="utf-8")
# Automatically generated small contact-sheet preview from the actual masters.
W,H=1350,760;board=Image.new("RGB",(W,H),PAPER);draw=ImageDraw.Draw(board)
sf=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",24)
bf=ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf",62)
draw.text((55,35),"MedOrigin",font=bf,fill=INK)
draw.text((58,121),"OVERLAP FORWARD  /  DESKTOP IDENTITY",font=sf,fill="#536057")
draw.line((55,163,1280,163),fill="#C4CEC6",width=2)
def card(title,name,box,background=PAPER):
 x0,y0,x1,y1=box
 draw.text((x0,y0-32),title,font=sf,fill=INK)
 draw.rounded_rectangle(box,15,fill=background,outline="#CBD4CC",width=2)
 tmp=png_bytes(ASSETS[name],(x1-x0)*2)
 item=Image.open(io.BytesIO(tmp)).convert("RGBA")
 item.thumbnail((x1-x0-25,y1-y0-25),Image.Resampling.LANCZOS)
 board.paste(item,(x0+(x1-x0-item.width)//2,y0+(y1-y0-item.height)//2),item)
card("01 / PRIMARY LOCKUP","medorigin-lockup-light.svg",(58,239,811,434))
card("02 / DARK ICON","medorigin-app-icon-dark.svg",(845,239,1045,438))
card("03 / LIGHT ICON","medorigin-app-icon-light.svg",(1065,239,1266,438))
card("04 / DARK LOCKUP","medorigin-lockup-dark.svg",(58,519,845,711),NIGHT)
card("05 / STANDALONE","medorigin-symbol.svg",(915,519,1265,711))
(OUT/"preview").mkdir(exist_ok=True)
board.save(OUT/"preview"/"overlap-forward.png")
for p in S.glob("*.svg"):ET.parse(str(p))
assert Image.open(OUT/"windows"/"MedOrigin.ico").format=="ICO"
assert (OUT/"macos"/"MedOrigin.icns").stat().st_size>10000
print("Brand assets generated:",len(list(OUT.rglob("*"))),"entries")
