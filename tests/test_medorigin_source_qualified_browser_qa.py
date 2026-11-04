"""Isolated regressions for the nonrelease source-bound browser QA contract.

Fixtures mock external package/browser attestations; they are not installed-Wheel,
native browser, clinical, FHIR conformance or release evidence.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
QA_SCRIPT = ROOT / "scripts" / "qa_medorigin_free_browser_sentry.py"


def _load_qa() -> Any:
    spec = importlib.util.spec_from_file_location("medorigin_qa_browser_regression", QA_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _proof() -> dict[str, object]:
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


def _harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    qualified_override: dict[str, object] | None = None,
    proof_override: dict[str, object] | None = None,
) -> tuple[Any, list[tuple[object, ...]]]:
    qa = _load_qa()
    proof = _proof() if proof_override is None else proof_override
    # Only the renderer runs here. The full qualifier and installed interpreter
    # gate are mocked and MUST be exercised by the hosted Windows workflow.
    expected_proof = _proof()
    digests = qa.core_truth_preview.write_negative_truth_preview(
        tmp_path / "expected", expected_proof
    )
    qualified: dict[str, object] = {
        "status": "TECHNICAL_CORE_NEGATIVE_TRUTH_PREVIEW_ONLY",
        "installed_python_source_files_verified_per_runtime": 266,
        "known_report_sha256": "a" * 64,
        "unknown_report_sha256": "b" * 64,
        "record_sha256": digests["record_sha256"],
        "preview_sha256": digests["preview_sha256"],
        "fhir_conformance_validated": False,
        "prepublication_rehearsal_qualified": False,
        "clinical_use_authorized": False,
        "publication_authorized": False,
        "native_launcher_identity_attested": False,
        "full_beta_preview_qualified": False,
        "merge_or_tag_authorized": False,
    }
    if qualified_override:
        qualified.update(qualified_override)

    paths: dict[str, Path] = {}
    for flag, relative in (
        ("--python311", "311/Scripts/python.exe"),
        ("--python312", "312/Scripts/python.exe"),
        ("--wheel", "medscale-0.3.0-py3-none-any.whl"),
        ("--sdist", "medscale-0.3.0.tar.gz"),
        ("--edge", "msedge.exe"),
    ):
        paths[flag] = tmp_path / relative
        paths[flag].parent.mkdir(parents=True, exist_ok=True)
        paths[flag].write_bytes(b"fixture only")

    argv = ["source-only-unit-test"]
    for flag, value in paths.items():
        argv.extend([flag, str(value)])
    monkeypatch.setattr(sys, "argv", argv)

    seen: list[tuple[object, ...]] = []
    monkeypatch.setattr(qa, "qualify", lambda *a, **kw: qualified)
    monkeypatch.setattr(qa.core_gate, "qualify", lambda *a, **kw: proof)
    monkeypatch.setattr(
        qa,
        "_browser_checks",
        lambda html, edge, known, unknown: seen.append(
            ("browser", html.read_text(encoding="utf-8"), known, unknown)
        ),
    )
    monkeypatch.setattr(qa, "_sentry_offline", lambda: seen.append(("sentry",)))
    return qa, seen


def test_truthful_browser_handoff_requires_identical_attested_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qa, seen = _harness(tmp_path, monkeypatch)
    assert qa.main() == 0
    assert [part[0] for part in seen] == ["browser", "sentry"]
    assert "Not validated" in seen[0][1]
    assert "script-src 'none'" in seen[0][1]
    assert "connect-src 'none'" in seen[0][1]
    assert "word-break: break-all" in seen[0][1]
    assert "article { min-width: 0;" in seen[0][1]
    assert seen[0][2:] == ("a" * 64, "b" * 64)
    assert "PASSED" not in seen[0][1]


@pytest.mark.parametrize(
    "alteration",
    [
        {"publication_authorized": True},
        {"fhir_conformance_validated": True},
        {"full_beta_preview_qualified": True},
        {"record_sha256": "c" * 64},
        {"preview_sha256": "d" * 64},
        {"installed_python_source_files_verified_per_runtime": 0},
    ],
)
def test_forged_qualification_never_reaches_browser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    alteration: dict[str, object],
) -> None:
    qa, seen = _harness(tmp_path, monkeypatch, qualified_override=alteration)
    with pytest.raises(AssertionError):
        qa.main()
    assert seen == []


def test_patient_field_in_provenance_proof_never_reaches_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    poison = _proof() | {"patient_name": "SYNTHETIC_SENTINEL"}
    qa, seen = _harness(tmp_path, monkeypatch, proof_override=poison)
    with pytest.raises(qa.core_truth_preview.NegativeTruthPreviewError):
        qa.main()
    assert seen == []
