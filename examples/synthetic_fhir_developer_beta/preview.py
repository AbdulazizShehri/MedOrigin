"""Standalone, script-free local HTML view of synthetic demo evidence.

Generates an untrusted-data-escaped static preview. No network, JavaScript,
external fonts, analytics, uploads, or clinical interpretation.
"""

from __future__ import annotations

from html import escape
from typing import Any


def _safe(value: object) -> str:
    return escape(str(value), quote=True)


def render(receipt: dict[str, Any]) -> str:
    """Render only a locally generated synthetic CLI receipt as inert HTML."""
    runs = receipt.get("runs")
    if not isinstance(runs, list) or not runs or len(runs) > 2:
        raise ValueError("expected one or two synthetic CLI results")
    cards: list[str] = []
    for run in runs:
        if not isinstance(run, dict):
            raise ValueError("invalid local synthetic CLI result")
        if run.get("structural_status") != "valid" or run.get("malformed_exit") != 1:
            raise ValueError("only verified valid synthetic reports may be previewed")
        label = _safe(run.get("label", "unknown"))
        digest = _safe(run.get("report_sha256", "unavailable"))
        fixture = _safe(run.get("fixture_sha256", "unavailable"))
        cards.append(
            '<article class="result">'
            '<div class="result-heading"><span class="status">PASSED</span>'
            f"<h3>{label}</h3></div>"
            "<p>Structural fixture validation and negative control succeeded.</p>"
            "<dl><dt>Report SHA-256</dt>"
            f"<dd><code>{digest}</code></dd>"
            "<dt>Fixture SHA-256</dt>"
            f"<dd><code>{fixture}</code></dd></dl>"
            "</article>"
        )
    result_cards = "\n".join(cards)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy"
 content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none';
 connect-src 'none'; script-src 'none'; form-action 'none'">
<title>MedOrigin · Synthetic FHIR evidence</title>
<style>
:root {{color-scheme:dark;
 font-family:system-ui,-apple-system,'Segoe UI',sans-serif}}
* {{box-sizing:border-box}}
body {{background:#0c1017;
color:#f0f3f6;
margin:0}}
main {{max-width:980px;
margin:0 auto;
padding:clamp(28px,6vw,76px) 24px}}
.brand {{font-weight:750;
letter-spacing:-.05em;
font-size:22px}}
.brand i {{color:#ed925f;
font-style:normal}}
.kicker {{color:#e8a076;
letter-spacing:.14em;
text-transform:uppercase;
font-size:11px;
font-weight:800;
margin-top:68px}}
h1 {{font-size:clamp(34px,5.7vw,66px);
letter-spacing:-.055em;
line-height:1.06;
max-width:770px;
margin:18px 0}}
.lead {{color:#a9b6c7;
max-width:650px;
font-size:17px;
line-height:1.65}}
.stats {{display:grid;
grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
gap:12px;
margin:42px 0 26px}}
.stat,.result {{border:1px solid #293343;
border-radius:14px;
background:#131a24;
padding:22px}}
.stat b {{display:block;
color:#f5f7fb;
font-size:27px;
letter-spacing:-.04em}}
.stat span {{color:#a9b6c7;
font-size:13px}}
.results {{display:grid;
grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
gap:16px}}
.result-heading {{display:flex;
align-items:center;
gap:12px}}
h3 {{margin:0;
font-size:18px}}
.status {{background:#1c3d35;
color:#86ddb2;
font-size:10px;
font-weight:800;
letter-spacing:.1em;
border-radius:99px;
padding:7px 10px}}
.result p {{color:#a9b6c7;
line-height:1.6;
font-size:14px}}
dl {{margin:20px 0 0}}
dt {{color:#92a4b7;
font-size:12px;
margin:14px 0 6px}}
dd {{margin:0;
overflow-wrap:anywhere}}
code {{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
color:#e7c7b3;
font-size:12px;
line-height:1.7}}
footer {{margin-top:42px;
padding-top:22px;
border-top:1px solid #293343;
color:#a9b6c7;
font-size:13px;
line-height:1.8}}
strong {{color:#f0f3f6}}
</style>
</head>
<body>
<main>
<div class="brand"><i>◉</i> MedOrigin</div>
<div class="kicker">Developer Beta Candidate · Local evidence</div>
<h1>Synthetic FHIR validation, verified offline.</h1>
<p class="lead">A reproducible demonstration of MedOrigin's local Python tooling,
using only fictional synthetic FHIR data and an installed <code>medscale 0.3.0</code> CLI.</p>
<section class="stats" aria-label="Evidence summary">
<div class="stat"><b>{len(runs)}</b><span>Installed CLI execution(s)</span></div>
<div class="stat"><b>100%</b><span>Fixture tests passed</span></div>
<div class="stat"><b>0</b><span>Network requests / patient records</span></div>
</section>
<section class="results" aria-label="Verified results">{result_cards}</section>
<footer>
<strong>Developer evidence, not clinical validation.</strong> The local
<code>valid</code> status does not establish comprehensive HL7 FHIR conformance,
diagnostic reliability, clinical safety, or production EHR compatibility.
No historical dataset migration, publisher approval or independent security
signoff is implied. This page is a standalone file and requires no server.
</footer>
</main>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    """Render a JSON evidence file into a local static HTML page."""
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.receipt.is_file() or args.receipt.stat().st_size > 100_000:
        parser.error("missing or oversized synthetic evidence receipt")
    try:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("receipt must be a JSON object")
        markup = render(receipt)
        with args.out.open("x", encoding="utf-8", newline="\n") as output:
            output.write(markup)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"LOCAL_PREVIEW_FAIL: {exc}\n")
    print(f"LOCAL_SYNTHETIC_PREVIEW_PASS: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
