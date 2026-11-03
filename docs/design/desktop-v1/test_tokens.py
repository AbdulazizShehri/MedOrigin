"""WCAG contrast and token coverage validation, no external dependencies."""
from pathlib import Path
import json,re
path=Path(__file__).resolve().parent
doc=json.loads((path/"tokens.json").read_text(encoding="utf-8"))
css=(path/"tokens.css").read_text(encoding="utf-8")
roles=set(doc["light"])
assert roles == set(doc["dark"])
def linear(x):
    n=int(x,16)/255
    return n/12.92 if n<=0.04045 else ((n+.055)/1.055)**2.4
def luminance(hexval):
    return sum(w*linear(hexval[i:i+2]) for w,i in [(0.2126,1),(0.7152,3),(0.0722,5)])
def ratio(a,b):
    x,y=sorted([luminance(a),luminance(b)],reverse=True)
    return (x+.05)/(y+.05)
def token_name(s):return re.sub(r"([A-Z])",lambda m:"-"+m.group(1).lower(),s)
checks=[]
for name,t in [(x,doc[x]) for x in ["light","dark"]]:
    for key in t:
        assert f"--mo-{token_name(key)}:{t[key]}" in css,(name,key)
    for bg in ["canvas","sidebar","surface","raised"]:
        for fg in ["text","textSecondary","textMuted"]:
            checks.append((name,fg,bg,ratio(t[fg],t[bg]),4.5))
    for fg,bg in [("accentText","accent"),("accentText","accentHover"),("brandOnAccent","brandAccent")]:
        checks.append((name,fg,bg,ratio(t[fg],t[bg]),4.5))
    for state in ["success","warning","danger"]:
        checks.append((name,state,"surface",ratio(t[state],t["surface"]),4.5))
failures=[c for c in checks if c[3]<c[4]]
for item in failures:print("FAIL",item)
assert not failures, f"{len(failures)} theme pairs under 4.5 contrast"
print(f"PASS: {len(checks)} foreground/background contrast checks >= 4.5:1 across light/dark")
print("Accent pairs",[(c[0],c[1],round(c[3],2)) for c in checks if c[1]=="accentText"])
