"""Regression for durable *negative-truth*, source-qualified Core preview export.

These unit tests use a CONTRACT-ONLY fake provenance checker to exercise
the export boundary. They do NOT attest an installed Wheel or Windows CLI.
Actual Core source/installed Wheel validation remains a separate QA gate.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts import qualify_medorigin_developer_beta as qualifier


def _synthetic_checkout(root: Path, *, forged_success: bool = False) -> Path:
    checkout = root / "qualified-source-test-double"
    scripts = checkout / "scripts"
    example = checkout / "examples" / "synthetic_fhir_developer_beta"
    scripts.mkdir(parents=True)
    example.mkdir(parents=True)
    # Preserve the REAL in-repo inert renderer under test. The checker
    # alone is a deliberately fabricated fixture, not source verification.
    actual = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "synthetic_fhir_developer_beta"
        / "core_truth_preview.py"
    )
    shutil.copyfile(actual, example / "core_truth_preview.py")
    checker = '''
def qualify(clis, *, interpreters):
    if len(clis) != 2 or len(interpreters) != 2:
        raise ValueError("two independently selected test interpreters required")
    return {
        "status": "LOCAL_FHIR_PROVENANCE_ONLY",
        "installed_cli_count": 2,
        "execution_mode": "source_verified_python_module",
        "known_report_sha256": "a" * 64,
        "unknown_report_sha256": "b" * 64,
        "fhir_conformance_validated": False,
        "publication_authorized": False,
        "clinical_use_authorized": ''' + ("True" if forged_success else "False") + ''',
        "independent_security_review_complete": False,
        "prepublication_rehearsal_qualified": False,
    }
'''
    (scripts / "check_installed_core_fhir_provenance.py").write_text(
        checker, encoding="utf-8"
    )
    return checkout


def _execute_export(checkout: Path, destination: Path) -> dict:
    return qualifier.source_qualified_core_negative_truth_preview(
        checkout,
        Path("fictional-cli311"),
        Path("fictional-cli312"),
        Path("fictional-python311"),
        Path("fictional-python312"),
        evidence_destination=destination,
    )


def test_exact_two_inert_negative_truth_artifacts_persist_without_patient_text(
    tmp_path: Path,
) -> None:
    checkout = _synthetic_checkout(tmp_path)
    output = tmp_path / "developer-readable-not-validated"
    receipt = _execute_export(checkout, output)

    assert receipt["durable_negative_truth_preview_exported"] is True
    assert receipt["source_qualified_negative_truth_preview"] is True
    assert receipt["fhir_conformance_validated"] is False
    assert receipt["clinical_use_authorized"] is False
    assert receipt["publication_authorized"] is False
    assert receipt["full_beta_preview_qualified"] is False
    assert {p.name for p in output.iterdir()} == {
        "core-negative-truth.json",
        "core-negative-truth.html",
    }
    stored = (output / "core-negative-truth.json").read_bytes()
    html = (output / "core-negative-truth.html").read_bytes()
    assert receipt["record_sha256"] == hashlib.sha256(stored).hexdigest()
    assert receipt["preview_sha256"] == hashlib.sha256(html).hexdigest()
    details = json.loads(stored)
    assert details["status"] == "CORE_PROVENANCE_PREVIEW_ONLY_NOT_FHIR_VALIDATION"
    assert details["clinical_use_authorized"] is False
    assert details["native_launcher_identity_attested"] is False
    assert b"Not validated." in html
    assert b"NOT AUTHORIZED" in html
    assert b"script-src 'none'" in html
    assert b"connect-src 'none'" in html
    assert b"<script" not in html
    assert str(checkout).encode() not in stored + html
    assert str(output).encode() not in stored + html
    assert not list(tmp_path.glob("medorigin-core-negative-preview-*"))


def test_existing_nonempty_destination_is_never_overwritten(tmp_path: Path) -> None:
    checkout = _synthetic_checkout(tmp_path)
    output = tmp_path / "important-existing-user-files"
    output.mkdir()
    keep = output / "do-not-delete.txt"
    keep.write_bytes(b"PRIVATE ORIGINAL MUST REMAIN")
    with pytest.raises(qualifier.QualificationError, match="destination refused"):
        _execute_export(checkout, output)
    assert keep.read_bytes() == b"PRIVATE ORIGINAL MUST REMAIN"
    assert {p.name for p in output.iterdir()} == {"do-not-delete.txt"}


def test_fake_claim_of_clinical_success_has_no_persistent_output(tmp_path: Path) -> None:
    checkout = _synthetic_checkout(tmp_path, forged_success=True)
    output = tmp_path / "must-not-exist"
    with pytest.raises(qualifier.QualificationError, match="source-qualified_core"):
        _execute_export(checkout, output)
    assert not output.exists()
    assert not list(tmp_path.glob("medorigin-core-negative-preview-*"))


def test_missing_parent_or_relative_output_is_refused_before_any_write(
    tmp_path: Path,
) -> None:
    checkout = _synthetic_checkout(tmp_path)
    paths = [
        Path("relative-user-evidence"),
        tmp_path / "missing-parent" / "output",
        tmp_path,
    ]
    for path in paths:
        with pytest.raises(qualifier.QualificationError, match="destination refused"):
            _execute_export(checkout, path)
    assert not (tmp_path / "missing-parent").exists()


def test_wrong_staged_content_hash_cannot_be_promoted(
    tmp_path: Path,
) -> None:
    staged = tmp_path / "stage"
    staged.mkdir()
    (staged / "core-negative-truth.json").write_bytes(b'{"status":"not_validated"}\n')
    (staged / "core-negative-truth.html").write_bytes(b"NOT VALIDATED")
    output = tmp_path / "no-promotion"
    with pytest.raises(qualifier.QualificationError, match="staged evidence mismatch"):
        qualifier._promote_core_preview(
            staged,
            output,
            record_sha256="0" * 64,
            preview_sha256="1" * 64,
        )
    assert not output.exists()
    assert staged.is_dir()


def test_old_beta_lane_cannot_silently_export_provenance_only_evidence(
    tmp_path: Path,
) -> None:
    with pytest.raises(qualifier.QualificationError, match="explicit Core negative-truth"):
        qualifier.qualify(
            checkout=tmp_path,
            wheel=tmp_path / "not-built.whl",
            sdist=tmp_path / "not-built.tar.gz",
            python311=tmp_path / "python311",
            python312=tmp_path / "python312",
            core_negative_truth_preview=False,
            evidence_destination=tmp_path / "output",
        )
    assert not (tmp_path / "output").exists()


def test_public_cli_rejects_export_flag_without_core_negative_truth_opt_in(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    args = [
        "--checkout", str(tmp_path),
        "--wheel", str(tmp_path / "not-built.whl"),
        "--sdist", str(tmp_path / "not-built.tar.gz"),
        "--python311", str(tmp_path / "python311"),
        "--python312", str(tmp_path / "python312"),
        "--evidence-dir", str(tmp_path / "output"),
    ]
    assert qualifier.main(args) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "Core preview required" in output.err
    assert str(tmp_path) not in output.err
    assert not (tmp_path / "output").exists()


def test_optional_no_export_still_discards_ephemeral_preview(tmp_path: Path) -> None:
    checkout = _synthetic_checkout(tmp_path)
    result = qualifier.source_qualified_core_negative_truth_preview(
        checkout,
        Path("fictional-cli311"),
        Path("fictional-cli312"),
        Path("fictional-python311"),
        Path("fictional-python312"),
    )
    assert result["durable_negative_truth_preview_exported"] is False
    assert result["source_qualified_negative_truth_preview"] is True
    assert {p.name for p in tmp_path.iterdir()} == {checkout.name}
