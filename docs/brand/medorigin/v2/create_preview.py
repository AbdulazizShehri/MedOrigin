"""Contact sheet built from actual SVG source & exported raster icons for Inkling."""
from pathlib import Path
from PIL import Image,ImageFont,ImageDraw
import subprocess,os,io
ROOT=Path(__file__).resolve().parents[4]
B=ROOT/'assets'/'brand'/'medorigin'/'v2'
SHARP=Path(os.environ['TEMP'])/'medorigin-brand-tools'/'node_modules'/'sharp'
NAVY='#101313';INK='#0B0C0C';PAPER='#FAF9F6';GRAY='#58645D'
W,H=1400,840
out=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(out)
regular=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
bold=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',37)
mono=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',13)
d.text((52,36),'MedOrigin  /  Overlap Forward',font=bold,fill=INK)
d.text((55,94),'VISUAL IDENTITY • SVG / WINDOWS / MACOS / TOKENS',font=mono,fill=GRAY)
d.line((52,143,1340,143),fill='#D4DBD5',width=2)
def drawsvg(key, x,y,maxwidth,maxheight):
 data=(B/'masters'/key).read_bytes()
 js="const s=require(process.argv[1]),fs=require('fs');s(fs.readFileSync(0)).resize({width:Number(process.argv[2])}).png().toBuffer().then(b=>process.stdout.write(b)).catch(e=>{console.error(e);process.exit(1)})"
 raw=subprocess.run(['node','-e',js,str(SHARP),str(maxwidth*2)],input=data,capture_output=True,check=True).stdout
 image=Image.open(io.BytesIO(raw)).convert('RGBA')
 image.thumbnail((maxwidth,maxheight),Image.Resampling.LANCZOS)
 out.paste(image,(x+(maxwidth-image.width)//2,y+(maxheight-image.height)//2),image)
def card(x,y,w,h,title,bg=PAPER):
 d.rounded_rectangle((x,y,x+w,y+h),radius=13,fill=bg,outline='#D5DDD6',width=2)
 d.text((x+17,y+15),title,font=mono,fill='#DCE9E1' if bg==NAVY else INK)
card(52,174,810,291,'01 / PRIMARY LOCKUP', '#FFFFFF')
drawsvg('medorigin-lockup.svg',95,233,720,199)
card(882,174,218,291,'02 / ICON DARK',PAPER)
card(1120,174,218,291,'03 / ICON LIGHT',PAPER)
for k,x in [('dark',893),('light',1131)]:
 im=Image.open(B/'icons/png'/k/'medorigin-256.png').convert('RGBA')
 im.thumbnail((196,196))
 out.paste(im,(x,239),im)
card(52,485,810,272,'04 / REVERSED',NAVY)
drawsvg('medorigin-lockup-dark.svg',94,544,720,187)
card(882,485,456,272,'05 / SYMBOL ONLY','#ECEFEC')
drawsvg('medorigin-symbol.svg',970,540,310,200)
for i,(label,cl) in enumerate([('ORANGE','#FE681B'),('INK',INK),('PAPER',PAPER),('PINK','#FFC2EA'),('BLUE','#A6DBFF'),('MINT','#C3F0BF')]):
 x=52+i*214
 d.rounded_rectangle((x,782,x+183,809),radius=4,fill=cl,outline='#CACFC9')
 d.text((x,815),label,font=mono,fill=INK)
(B/'previews').mkdir(exist_ok=True)
out.save(B/'previews/MedOrigin_Identity_v2_Design_Board.png')
print('Exported preview board')
