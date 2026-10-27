"""Standalone, script-free local HTML view of synthetic demo evidence.

Generates an untrusted-data-escaped static preview. No network, JavaScript,
external fonts, analytics, uploads, or clinical interpretation.
"""

from __future__ import annotations

import hashlib
import json
import re
from html import escape
from pathlib import Path, PurePosixPath
from typing import Any


def _safe(value: object) -> str:
    return escape(str(value), quote=True)


_HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_RECEIPT_SCHEMA = "medorigin-local-synthetic-fhir-example/v1"
_SCOPE = "synthetic structural validation, not full HL7 conformance"
_INSTALLED_VERSION = "medscale 0.3.0"
_WORKSPACE = {
    "application": "medscale-workspace",
    "version": "0.1.0.dev1",
    "data_class": "SYNTHETIC",
    "mode": "offline-shell",
    "ready": True,
}
_MAX_REPORT_BYTES = 1_000_000


def unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys at every depth; a later key may hide PHI."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key in synthetic receipt")
        result[key] = value
    return result


def admit_receipt(receipt: object, *, directory: Path) -> dict[str, Any]:
    """Fail closed on unsupported or forged synthetic-preview evidence fields.

    No cryptographic signer is implied. Recompute the report file digest and
    pin the bundled fixture, type/keys, relative path and negative control.
    """
    if not isinstance(receipt, dict):
        raise ValueError("synthetic evidence must be an object")
    required = {
        "schema",
        "scope",
        "publication_authorized",
        "clinical_authorized",
        "independent_review_completed",
        "runs",
    }
    if set(receipt) not in (required, required | {"workspace"}):
        raise ValueError("unexpected synthetic receipt fields")
    if (
        receipt["schema"] != _RECEIPT_SCHEMA
        or receipt["scope"] != _SCOPE
        or any(
            receipt[key] is not False
            for key in (
                "publication_authorized",
                "clinical_authorized",
                "independent_review_completed",
            )
        )
    ):
        raise ValueError("synthetic receipt scope not admitted")
    runs = receipt["runs"]
    if not isinstance(runs, list) or len(runs) not in (1, 2):
        raise ValueError("unexpected synthetic runs")
    fixture_file = Path(__file__).resolve().parent / "synthetic_structure_definition.json"
    fixture_bytes = fixture_file.read_bytes()
    fixture_hash = hashlib.sha256(fixture_bytes).hexdigest()
    fixture_payload = json.loads(fixture_bytes, object_pairs_hook=unique_json_object)
    expected_input_hash = hashlib.sha256(
        json.dumps(
            fixture_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    expected_report = {
        "created_at": "2026-10-24T00:00:00Z",
        "errors": [],
        "format_version": "fhirkit-validation-report/v1",
        "input_hash": expected_input_hash,
        "report_id": "",
        "status": "valid",
        "validator_name": "medscale-fhirkit-local",
        "validator_version": "0.1.0",
        "warnings": [],
    }
    expected_runs = {
        "label",
        "installed_version",
        "fixture_sha256",
        "report_sha256",
        "report_path",
        "structural_status",
        "valid_exit",
        "malformed_exit",
    }
    root = directory.resolve()
    report_hashes: list[str] = []
    for i, row in enumerate(runs, start=1):
        if not isinstance(row, dict) or set(row) != expected_runs:
            raise ValueError("unexpected synthetic run fields")
        if (
            row["label"] != f"run_{i}"
            or row["installed_version"] != _INSTALLED_VERSION
            or row["fixture_sha256"] != fixture_hash
            or row["structural_status"] != "valid"
            or type(row["valid_exit"]) is not int
            or row["valid_exit"] != 0
            or type(row["malformed_exit"]) is not int
            or row["malformed_exit"] != 1
            or not isinstance(row["report_sha256"], str)
            or _HEX_SHA256.fullmatch(row["report_sha256"]) is None
        ):
            raise ValueError("synthetic run identity or validation outcome invalid")
        path = row["report_path"]
        if not isinstance(path, str) or len(path) > 240 or "\\" in path:
            raise ValueError("unsafe synthetic report path")
        relative = PurePosixPath(path)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or len(relative.parts) < 3
            or relative.parts[0] != f"reports_run_{i}"
            or relative.name != "report.json"
            or ":" in path
        ):
            raise ValueError("unexpected synthetic report path")
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise ValueError("synthetic report file is missing or outside evidence root")
        if candidate.stat().st_size > _MAX_REPORT_BYTES:
            raise ValueError("oversized synthetic report")
        raw = candidate.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["report_sha256"]:
            raise ValueError("synthetic report content digest mismatch")
        report = json.loads(raw, object_pairs_hook=unique_json_object)
        # A matching digest alone is insufficient: an attacker could replace
        # both the report and receipt with a fabricated 'valid' record. Admit
        # only the exact, fictional fixture's known deterministic CLI report.
        if report != expected_report:
            raise ValueError("synthetic report identity or content invalid")
        report_hashes.append(row["report_sha256"])
    if len(set(report_hashes)) != 1:
        raise ValueError("cross-interpreter synthetic reports differ")
    if "workspace" in receipt and (
        not isinstance(receipt["workspace"], dict)
        or set(receipt["workspace"]) != set(_WORKSPACE)
        or any(
            type(receipt["workspace"][k]) is not type(v) or receipt["workspace"][k] != v
            for k, v in _WORKSPACE.items()
        )
    ):
        raise ValueError("optional synthetic Workspace fields not admitted")
    return receipt


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
    workspace = receipt.get("workspace")
    if workspace is not None:
        expected = {
            "application": "medscale-workspace",
            "version": "0.1.0.dev1",
            "data_class": "SYNTHETIC",
            "mode": "offline-shell",
            "ready": True,
        }
        if not isinstance(workspace, dict) or workspace != expected:
            raise ValueError("Workspace status does not match synthetic-safe contract")
        cards.append(
            '<article class="result" aria-label="Optional synthetic Workspace status">'
            '<div class="result-heading"><span class="status">READY</span>'
            "<h3>Synthetic Workspace</h3></div>"
            "<p>Installed <code>medscale-workspace 0.1.0.dev1</code>: "
            "offline-shell / SYNTHETIC. No production key-provider or clinical access.</p>"
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
grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));
gap:16px}}
.result-heading {{display:flex;
min-width:0;
align-items:center;
gap:12px}}
h3 {{margin:0;
font-size:18px;
min-width:0;
overflow-wrap:anywhere}}
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
<div class="stat"><b>LOCAL</b><span>Synthetic-only demonstration</span></div>
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

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.receipt.is_file() or args.receipt.stat().st_size > 100_000:
        parser.error("missing or oversized synthetic evidence receipt")
    try:
        receipt = json.loads(
            args.receipt.read_text(encoding="utf-8"),
            object_pairs_hook=unique_json_object,
        )
        markup = render(admit_receipt(receipt, directory=args.receipt.parent))
        with args.out.open("x", encoding="utf-8", newline="\n") as output:
            output.write(markup)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"LOCAL_PREVIEW_FAIL: {exc}\n")
    print(f"LOCAL_SYNTHETIC_PREVIEW_PASS: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
