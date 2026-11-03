"""MedOrigin Overlap Forward V2 — independently regenerable desktop assets.
No runtime, protocol, or clinical changes. Requires Pillow, fontTools and local sharp.
The user-selected raster is a design reference, not an original vector source.
"""
from pathlib import Path
from xml.etree import ElementTree as ET
import os, json, subprocess, io
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'assets'/'brand'/'medorigin'/'v2'
SVG=OUT/'masters';SVG.mkdir(parents=True,exist_ok=True)
ORANGE='#FE681B';INK='#0B0C0C';NIGHT='#101313';WHITE='#FFFFFF';PAPER='#FAF9F6'
SHARP=Path(os.environ['TEMP'])/'medorigin-brand-tools'/'node_modules'/'sharp'
FONT=Path(os.environ['TEMP'])/'medorigin-inter-font'/'package'/'files'/'inter-latin-200-normal.woff2'
assert SHARP.exists() and FONT.exists()
font=TTFont(str(FONT));cmap=font.getBestCmap(); gs=font.getGlyphSet();hmtx=font['hmtx'].metrics;upm=font['head'].unitsPerEm
def shell_svg(w,h,content,name):
 return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{name}">{content}</svg>'
def symbol(orange=ORANGE,stroke=INK,micro=False):
 wd=31 if micro else 26
 return f'''<defs><clipPath id="originDisc"><circle cx="390" cy="318" r="242"/></clipPath></defs>
 <g clip-path="url(#originDisc)" fill="{orange}"><path d="M186 -20 H700 V660 H432 Z"/><path d="M140 -20 H169 L397 660 H365 Z"/></g>
 <g fill="none" stroke="{stroke}" stroke-width="{wd}" stroke-linecap="round"><path d="M43 162 174 539 M124 162 255 539"/></g>'''
def wordmark(color=INK):
 pos=0;g=[];scale=114/upm
 for ch in 'MedOrigin':
  name=cmap[ord(ch)];pen=SVGPathPen(gs);gs[name].draw(pen);path=pen.getCommands()
  if path:g.append(f'<path d="{path}" transform="translate({pos:.2f},0)"/>')
  pos+=hmtx[name][0]+44
 return f'<g fill="{color}" transform="scale({scale:.8f},-{scale:.8f})">{"".join(g)}</g>',int(pos*scale+40)
def lock(mode):
 dark=mode=='dark';mono=mode.startswith('mono')
 mark=WHITE if mode=='mono-white' else INK if mode=='mono-ink' else ORANGE
 stroke=WHITE if dark or mode=='mono-white' else INK
 word,w=wordmark(WHITE if dark or mode=='mono-white' else INK)
 total=max(980,238+w+30)
 bg=f'<rect width="{total}" height="220" fill="{NIGHT}"/>' if dark else ''
 return shell_svg(total,220,bg+f'<g transform="translate(12,5) scale(.31)">{symbol(mark,stroke)}</g><g transform="translate(260,145)">{word}</g>','MedOrigin lockup')
def tile(mode='dark',small=False):
 bg=NIGHT if mode=='dark' else PAPER if mode=='light' else ORANGE
 mark=WHITE if mode=='orange' else ORANGE
 stroke=WHITE if mode in ['dark','orange'] else INK
 return shell_svg(512,512,f'<rect width="512" height="512" rx="108" fill="{bg}"/><g transform="translate(45,82) scale(.60)">{symbol(mark,stroke,small)}</g>',f'MedOrigin {mode} app icon')
p,w=wordmark(INK);q,_=wordmark(WHITE)
files={
 'medorigin-symbol.svg':shell_svg(700,644,symbol(),'MedOrigin Overlap Forward symbol'),
 'medorigin-symbol-on-dark.svg':shell_svg(700,644,symbol(ORANGE,WHITE),'MedOrigin reversed symbol'),
 'medorigin-symbol-mono-ink.svg':shell_svg(700,644,symbol(INK,INK),'MedOrigin monochrome ink'),
 'medorigin-symbol-mono-white.svg':shell_svg(700,644,symbol(WHITE,WHITE),'MedOrigin monochrome white'),
 'medorigin-wordmark.svg':shell_svg(w,174,f'<g transform="translate(20,146)">{p}</g>','MedOrigin outlined wordmark'),
 'medorigin-wordmark-white.svg':shell_svg(w,174,f'<g transform="translate(20,146)">{q}</g>','MedOrigin white wordmark'),
 'medorigin-lockup.svg':lock('light'),
 'medorigin-lockup-dark.svg':lock('dark'),
 'medorigin-lockup-mono-ink.svg':lock('mono-ink'),
 'medorigin-lockup-mono-white.svg':lock('mono-white'),
 'medorigin-tile-dark.svg':tile(),
 'medorigin-tile-light.svg':tile('light'),
 'medorigin-tile-orange.svg':tile('orange'),
 'medorigin-tile-dark-small.svg':tile('dark',True),
}
for name,src in files.items():
 ET.fromstring(src);(SVG/name).write_text(src,encoding='utf-8')
def render(src,size):
 js="const s=require(process.argv[1]);const fs=require('fs');s(fs.readFileSync(0)).resize({width:Number(process.argv[2]),height:Number(process.argv[3]),fit:'fill'}).png().toBuffer().then(x=>process.stdout.write(x)).catch(e=>{console.error(e);process.exit(1)})"
 return subprocess.run(['node','-e',js,str(SHARP),str(size),str(size)],input=src.encode(),capture_output=True,check=True).stdout
for mode in ['dark','light']:
 folder=OUT/'icons'/'png'/mode;folder.mkdir(parents=True,exist_ok=True)
 for n in [16,20,24,32,40,48,64,96,128,256,512,1024]:
  src=files['medorigin-tile-dark-small.svg'] if mode=='dark' and n<=24 else files[f'medorigin-tile-{mode}.svg']
  (folder/f'medorigin-{n}.png').write_bytes(render(src,n))
folder=OUT/'icons'/'png'/'transparent';folder.mkdir(parents=True,exist_ok=True)
for n in [64,128,256,512,1024]:
 (folder/f'medorigin-symbol-{n}.png').write_bytes(render(files['medorigin-symbol.svg'],n))
(OUT/'icons'/'windows').mkdir(parents=True,exist_ok=True)
(OUT/'icons'/'macos').mkdir(parents=True,exist_ok=True)
im=Image.open(OUT/'icons'/'png'/'dark'/'medorigin-1024.png').convert('RGBA')
im.save(OUT/'icons'/'windows'/'MedOrigin.ico',format='ICO',sizes=[(n,n) for n in [16,20,24,32,40,48,64,96,128,256]])
im.save(OUT/'icons'/'macos'/'MedOrigin.icns',format='ICNS')
colors={'originOrange':ORANGE,'ink':INK,'night':NIGHT,'paper':PAPER,'bone':'#F1F0ED','line':'#D8DAD5','minaretPink':'#FFC2EA','minaretBlue':'#A6DBFF','minaretMint':'#C3F0BF'}
tokens={'brand':'MedOrigin','version':'2.0.0-review','status':'candidate-requires-founder-optical-approval',
'companyRelationship':{'parent':'Minaret','activation':'future','showEndorsementNow':False},'colors':colors}
(OUT/'tokens').mkdir(exist_ok=True)
(OUT/'tokens'/'brand-tokens.json').write_text(json.dumps(tokens,indent=2)+'\n')
(OUT/'tokens'/'brand-tokens.css').write_text(':root{'+''.join(f'--mo-{k}:{v};' for k,v in colors.items())+'}\n')
assert Image.open(OUT/'icons'/'windows'/'MedOrigin.ico').format=='ICO'
assert Image.open(OUT/'icons'/'macos'/'MedOrigin.icns').format=='ICNS'
print('Generated',len(list(OUT.rglob('*'))),'brand assets')
