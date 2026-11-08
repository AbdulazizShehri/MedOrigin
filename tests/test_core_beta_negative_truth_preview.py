"""Truthful Core-only Developer Beta static preview and negative assurance tests.

NOT full Beta, HL7 R4 conformance, clinical approval, or publication.
Only known fictional SHA256 evidence may reach an inert static HTML page.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples" / "synthetic_fhir_developer_beta" / "core_truth_preview.py"
QUALIFIER = ROOT / "scripts" / "qualify_medorigin_developer_beta.py"
SECRET = 'PRIVATE_FICTIONAL_PATIENT_<img src=x onerror="alert(1)">'


def _load(source: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("medorigin_core_negative_truth_test", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _proof() -> dict[str, Any]:
    return {
        "status": "LOCAL_FHIR_PROVENANCE_ONLY",
        "installed_cli_count": 2,
        "execution_mode": "source_verified_python_module",
        "known_report_sha256": "a" * 64,
        "unknown_report_sha256": "b" * 64,
        "fhir_conformance_validated": False,
        "publication_authorized": False,
        "clinical_use_authorized": False,
        "independent_security_review_complete": False,
        "prepublication_rehearsal_qualified": False,
    }


def test_exact_two_interpreter_negative_provenance_creates_safe_static_html_and_receipt(
    tmp_path: Path,
) -> None:
    renderer = _load(SOURCE)
    source = _proof()
    receipt = renderer.admit_installed_core_proof(source)
    assert receipt["status"] == "CORE_PROVENANCE_PREVIEW_ONLY_NOT_FHIR_VALIDATION"
    assert receipt["installed_cli_count"] == 2
    assert receipt["native_launcher_identity_attested"] is False
    assert receipt["negative_truth_preview_generated"] is True
    assert receipt["full_beta_preview_qualified"] is False
    output = renderer.write_negative_truth_preview(tmp_path / "truth", source)
    assert output["status"] == "SOURCE_VERIFIED_CORE_NEGATIVE_TRUTH_PREVIEW_ONLY"
    assert all(
        output[key] is False
        for key in (
            "clinical_use_authorized",
            "publication_authorized",
            "fhir_conformance_validated",
            "prepublication_rehearsal_qualified",
            "native_launcher_identity_attested",
            "full_beta_preview_qualified",
        )
    )
    assert sorted(p.name for p in (tmp_path / "truth").iterdir()) == [
        "core-negative-truth.html",
        "core-negative-truth.json",
    ]
    stored = json.loads((tmp_path / "truth/core-negative-truth.json").read_text())
    assert stored == receipt
    html = (tmp_path / "truth/core-negative-truth.html").read_text(encoding="utf-8")
    assert html == renderer.render_negative_truth_preview(stored)
    assert '<meta http-equiv="Content-Security-Policy"' in html
    for line in ("script-src 'none'", "connect-src 'none'", "img-src 'none'", "form-action 'none'"):
        assert line in html
    assert "Not validated." in html
    assert html.count("NOT VALIDATED") == 2
    assert "NOT AUTHORIZED" in html
    assert "Full Developer Beta" in html
    assert "<script" not in html
    assert "<iframe" not in html
    assert "<img" not in html
    assert "https://" not in html
    assert "http://" not in html
    assert SECRET not in html
    assert re.fullmatch(r"[0-9a-f]{64}", output["preview_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", output["record_sha256"])


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("status", "FHIR_VALID"),
        ("status", "TECHNICAL_PREPUBLICATION_REHEARSAL_PASS"),
        ("installed_cli_count", 1),
        ("installed_cli_count", True),
        ("installed_cli_count", "2"),
        ("execution_mode", "unattested_installed_console_shim"),
        ("execution_mode", "source_verified_python_module " + SECRET),
        ("known_report_sha256", "z" * 64),
        ("known_report_sha256", "a" * 65),
        ("known_report_sha256", "b" * 64),
        ("unknown_report_sha256", "0"),
        ("fhir_conformance_validated", True),
        ("fhir_conformance_validated", 0),
        ("publication_authorized", True),
        ("clinical_use_authorized", True),
        ("independent_security_review_complete", True),
        ("prepublication_rehearsal_qualified", True),
    ],
)
def test_fake_fhir_validity_untrusted_source_or_authority_refused(field: str, bad: object) -> None:
    renderer = _load(SOURCE)
    forged = _proof()
    forged[field] = bad
    with pytest.raises(renderer.NegativeTruthPreviewError) as exc:
        renderer.admit_installed_core_proof(forged)
    assert SECRET not in str(exc.value)


def test_extra_secret_or_wrong_receipt_flags_are_rejected_before_html() -> None:
    renderer = _load(SOURCE)
    forged = _proof()
    forged["patient_name"] = SECRET
    with pytest.raises(renderer.NegativeTruthPreviewError):
        renderer.admit_installed_core_proof(forged)
    safe = renderer.admit_installed_core_proof(_proof())
    for key, bad in (
        ("full_beta_preview_qualified", True),
        ("native_launcher_identity_attested", True),
        ("negative_truth_preview_generated", 1),
        ("status", "FHIR_VALID"),
        ("clinical_use_authorized", True),
    ):
        changed = {**safe, key: bad}
        with pytest.raises(renderer.NegativeTruthPreviewError):
            renderer.render_negative_truth_preview(changed)
    with pytest.raises(renderer.NegativeTruthPreviewError):
        renderer.render_negative_truth_preview({**safe, "patient_name": SECRET})


def test_reject_existing_output_without_destroying_user_file(tmp_path: Path) -> None:
    renderer = _load(SOURCE)
    output = tmp_path / "evidence"
    output.mkdir()
    preserved = output / "core-negative-truth.html"
    preserved.write_text(SECRET)
    with pytest.raises(renderer.NegativeTruthPreviewError):
        renderer.write_negative_truth_preview(output, _proof())
    assert preserved.read_text() == SECRET


def test_legacy_full_beta_remains_nonrelease_and_separate_from_new_core_mode() -> None:
    source = QUALIFIER.read_text(encoding="utf-8")
    assert "--core-negative-truth-preview" in source
    assert "core_negative_truth_preview: bool = False" in source
    assert "if core_negative_truth_preview is True:" in source
    assert "TECHNICAL_CORE_NEGATIVE_TRUTH_PREVIEW_ONLY" in source
    assert "TECHNICAL_PREPUBLICATION_REHEARSAL_PASS" in source
    assert "synthetic installed-CLI demonstration failed" in source
    assert "prepublication_rehearsal_qualified" in source
    for prohibited in ("twine upload", "gh release create", "git push", "hf upload"):
        assert prohibited not in source
