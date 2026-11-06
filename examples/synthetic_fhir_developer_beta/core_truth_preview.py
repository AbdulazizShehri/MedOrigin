"""Static truthful Core FHIR provenance preview, NOT HL7 validation.

Accepts only the exact two-installed-interpreter source-verified
negative-truth receipt from check_installed_core_fhir_provenance.
No patient input, network, JavaScript, uploads, full Beta, or release claim.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_PROOF_KEYS = frozenset(
    {
        "status",
        "installed_cli_count",
        "execution_mode",
        "known_report_sha256",
        "unknown_report_sha256",
        "fhir_conformance_validated",
        "publication_authorized",
        "clinical_use_authorized",
        "independent_security_review_complete",
        "prepublication_rehearsal_qualified",
    }
)
_RECEIPT_KEYS = frozenset(
    {
        "schema",
        "status",
        "installed_cli_count",
        "execution_mode",
        "known_report_sha256",
        "unknown_report_sha256",
        "fhir_conformance_validated",
        "publication_authorized",
        "clinical_use_authorized",
        "independent_security_review_complete",
        "prepublication_rehearsal_qualified",
        "native_launcher_identity_attested",
        "negative_truth_preview_generated",
        "full_beta_preview_qualified",
    }
)


class NegativeTruthPreviewError(ValueError):
    """Redacted fixed refusal; never interpolates untrusted evidence."""


def admit_installed_core_proof(proof: object) -> dict[str, object]:
    """Reject forged success, arbitrary fields, wrong executor or missing gates."""
    if not isinstance(proof, dict) or set(proof) != _PROOF_KEYS:
        raise NegativeTruthPreviewError("unqualified_provenance_schema")
    if (
        proof["status"] != "LOCAL_FHIR_PROVENANCE_ONLY"
        or type(proof["installed_cli_count"]) is not int
        or proof["installed_cli_count"] != 2
        or proof["execution_mode"] != "source_verified_python_module"
        or any(
            proof[field] is not False
            for field in (
                "fhir_conformance_validated",
                "publication_authorized",
                "clinical_use_authorized",
                "independent_security_review_complete",
                "prepublication_rehearsal_qualified",
            )
        )
    ):
        raise NegativeTruthPreviewError("unqualified_provenance_status")
    for field in ("known_report_sha256", "unknown_report_sha256"):
        if type(proof[field]) is not str or _SHA.fullmatch(proof[field]) is None:
            raise NegativeTruthPreviewError("unqualified_provenance_digest")
    if proof["known_report_sha256"] == proof["unknown_report_sha256"]:
        raise NegativeTruthPreviewError("indistinguishable_fictional_cases")
    return {
        "schema": "medorigin-source-verified-core-negative-truth-preview/v1",
        "status": "CORE_PROVENANCE_PREVIEW_ONLY_NOT_FHIR_VALIDATION",
        "installed_cli_count": 2,
        "execution_mode": "source_verified_python_module",
        "known_report_sha256": proof["known_report_sha256"],
        "unknown_report_sha256": proof["unknown_report_sha256"],
        "fhir_conformance_validated": False,
        "publication_authorized": False,
        "clinical_use_authorized": False,
        "independent_security_review_complete": False,
        "prepublication_rehearsal_qualified": False,
        "native_launcher_identity_attested": False,
        "negative_truth_preview_generated": True,
        "full_beta_preview_qualified": False,
    }


def _admit_receipt(receipt: object) -> dict[str, Any]:
    if not isinstance(receipt, dict) or set(receipt) != _RECEIPT_KEYS:
        raise NegativeTruthPreviewError("unqualified_negative_truth_receipt")
    expected = admit_installed_core_proof(
        {key: receipt[key] for key in _PROOF_KEYS}
        | {
            "status": "LOCAL_FHIR_PROVENANCE_ONLY",
        }
    )
    if type(receipt["negative_truth_preview_generated"]) is not bool:
        raise NegativeTruthPreviewError("unqualified_negative_truth_receipt")
    if receipt != expected:
        raise NegativeTruthPreviewError("unqualified_negative_truth_receipt")
    return receipt


def render_negative_truth_preview(receipt: object) -> str:
    """Inert HTML built only from fixed words and admitted SHA-256 digests."""
    safe = _admit_receipt(receipt)
    known = safe["known_report_sha256"]
    unknown = safe["unknown_report_sha256"]
    # SHA regex + exact schema keys guarantee no attacker-controlled markup.
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy"
 content="default-src 'none'; style-src 'unsafe-inline';
 script-src 'none'; connect-src 'none'; img-src 'none';
 form-action 'none'; base-uri 'none'">
<title>MedOrigin | Local FHIR provenance — Not validated</title>
<style>
:root {{ color-scheme: dark; font-family: system-ui, sans-serif; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #0d121a; color: #f2f5fa; }}
main {{ max-width: 840px; margin: auto; padding: 56px 24px; }}
h1 {{ font-size: clamp(30px, 5vw, 52px); letter-spacing: -.04em; }}
p {{ color: #c2cad7; line-height: 1.6; }}
.grid {{ display: grid; min-width: 0;
 grid-template-columns: repeat(auto-fit,minmax(min(100%,260px),1fr));
 gap: 16px; }}
article {{ min-width: 0; max-width: 100%; padding: 20px;
 border: 1px solid #3b4453; border-radius: 14px; }}
strong {{ color: #ffbe8f; }}
code {{ display: block; max-width: 100%; font-size: 12px;
 overflow-wrap: anywhere; word-break: break-all; white-space: normal; }}
footer {{ margin-top: 36px; border-top: 1px solid #3b4453; padding-top: 16px; }}
</style>
</head>
<body>
<main>
<p>MedOrigin / Developer Beta / Offline fictional records</p>
<h1>FHIR provenance verified. <strong>Not validated.</strong></h1>
<p>Two independently installed Python interpreters reproduced deterministic
local FHIR reports. No official HL7 R4 schema, terminology, profile,
FHIRPath, clinical safety or full conformance validation was performed.
This preview is NOT an approved release or patient-data workflow.</p>
<section class="grid" aria-label="Fictional FHIR proof">
<article><h2>Known fictional resource</h2><p>Status: <strong>NOT VALIDATED</strong></p>
<p>Deterministic report SHA-256:</p><code>{known}</code></article>
<article><h2>Unknown fictional resource</h2><p>Status: <strong>NOT VALIDATED</strong></p>
<p>Deterministic report SHA-256:</p><code>{unknown}</code></article>
</section>
<footer><p>Source-qualified Python module, not a source-attested native executable
launcher. Clinical use: NOT AUTHORIZED. Publication: NOT AUTHORIZED.
Full Developer Beta preview/rehearsal: NOT QUALIFIED.
No network, JavaScript, external images or uploads.</p></footer>
</main>
</body>
</html>
"""


def write_negative_truth_preview(destination: Path, proof: object) -> dict[str, object]:
    """Create exactly two local fictional evidence files, fail closed on reuse."""
    safe = admit_installed_core_proof(proof)
    markup = render_negative_truth_preview(safe)
    if destination.exists() or destination.is_symlink():
        raise NegativeTruthPreviewError("negative_truth_evidence_output_exists")
    destination.mkdir(parents=True, exist_ok=False)
    record = destination / "core-negative-truth.json"
    html = destination / "core-negative-truth.html"
    record.write_text(
        json.dumps(safe, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with html.open("x", encoding="utf-8", newline="\n") as output:
        output.write(markup)
    return {
        "status": "SOURCE_VERIFIED_CORE_NEGATIVE_TRUTH_PREVIEW_ONLY",
        "record_sha256": hashlib.sha256(record.read_bytes()).hexdigest(),
        "preview_sha256": hashlib.sha256(html.read_bytes()).hexdigest(),
        "installed_cli_count": 2,
        "fhir_conformance_validated": False,
        "prepublication_rehearsal_qualified": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
        "native_launcher_identity_attested": False,
        "full_beta_preview_qualified": False,
    }
