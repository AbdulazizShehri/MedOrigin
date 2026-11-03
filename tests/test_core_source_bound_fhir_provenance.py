"""Fail-closed source+artifact+real-install qualification for FHIR provenance only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/qualify_core_source_bound_fhir_provenance.py"
HEAD = "a" * 40


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("source_bound_fhir_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def paths(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    checkout = tmp_path / "repo"
    checkout.mkdir()
    wheel = tmp_path / "medscale-0.3.0-py3-none-any.whl"
    wheel.write_bytes(b"fictional wheel witness")
    sdist = tmp_path / "medscale-0.3.0.tar.gz"
    sdist.write_bytes(b"fictional source witness")
    for n in ("env311", "env312"):
        bin_dir = tmp_path / n / ("Scripts" if sys.platform == "win32" else "bin")
        bin_dir.mkdir(parents=True)
        (bin_dir / ("medscale.exe" if sys.platform == "win32" else "medscale")).write_bytes(
            b"fictional CLI"
        )
        (bin_dir / ("python.exe" if sys.platform == "win32" else "python")).write_bytes(
            b"fictional interpreter"
        )
    python_name = "python.exe" if sys.platform == "win32" else "python"
    bin_name = "Scripts" if sys.platform == "win32" else "bin"
    return (
        checkout,
        wheel,
        sdist,
        tmp_path / "env311" / bin_name / python_name,
        tmp_path / "env312" / bin_name / python_name,
    )


def _accept_fake_gates(
    gate: Any,
    monkeypatch: pytest.MonkeyPatch,
    wheel: Path,
) -> None:
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    monkeypatch.setattr(
        gate.artifact_gate,
        "run",
        lambda args, **_kwargs: HEAD if "rev-parse" in args else "",
    )

    def fake_receipt(
        script: str, _args: list[str], _status: str, _checkout: Path
    ) -> dict[str, Any]:
        if script == "check_core_wheel_source_identity.py":
            return {"source_git_commit": HEAD}
        if script == "inspect_release_wheel_metadata.py":
            return {"version": "0.3.0", "sha256": digest}
        return {}

    monkeypatch.setattr(gate.artifact_gate, "tool_receipt", fake_receipt)
    monkeypatch.setattr(gate.artifact_gate, "installed_wheel_matches", lambda *_a: 250)
    monkeypatch.setattr(
        gate.fhir_gate,
        "qualify",
        lambda _clis: {
            "status": "LOCAL_FHIR_PROVENANCE_ONLY",
            "installed_cli_count": 2,
            "known_report_sha256": "a" * 64,
            "unknown_report_sha256": "b" * 64,
            "fhir_conformance_validated": False,
            "publication_authorized": False,
            "clinical_use_authorized": False,
            "independent_security_review_complete": False,
            "prepublication_rehearsal_qualified": False,
        },
    )


def test_exact_valid_receipts_are_still_explicitly_nonreleasing(
    gate: Any, paths: tuple[Path, Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _accept_fake_gates(gate, monkeypatch, paths[1])
    result = gate.qualify(*paths)
    assert result["source_git_commit"] == HEAD
    assert result["status"] == "SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY"
    assert result["installed_python_source_files_verified_per_runtime"] == 250
    assert result["runtimes"] == ["3.11", "3.12"]
    for field in (
        "fhir_conformance_validated",
        "publication_authorized",
        "clinical_use_authorized",
        "independent_security_review_complete",
        "prepublication_rehearsal_qualified",
        "merge_or_tag_authorized",
    ):
        assert result[field] is False


@pytest.mark.parametrize("bad", ["dirty", "noncanonical_commit"])
def test_source_checkout_must_match_clean_git_head(
    gate: Any, paths: tuple[Path, Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    _accept_fake_gates(gate, monkeypatch, paths[1])
    monkeypatch.setattr(
        gate.artifact_gate,
        "run",
        lambda args, **_kwargs: (
            "b" * 39 if bad == "noncanonical_commit" else HEAD
        ) if "rev-parse" in args else (" M src/medscale/__init__.py" if bad == "dirty" else ""),
    )
    with pytest.raises(gate.QualificationError, match="clean, canonical"):
        gate.qualify(*paths)


@pytest.mark.parametrize("script", [
    "check_core_wheel_source_identity.py",
    "check_sdist_publication_scope.py",
    "inspect_release_wheel_metadata.py",
])
def test_refuses_failed_source_artifact_verifier(
    gate: Any, paths: tuple[Path, Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch, script: str
) -> None:
    _accept_fake_gates(gate, monkeypatch, paths[1])
    original = gate.artifact_gate.tool_receipt
    def failing(name: str, *args: object) -> dict[str, Any]:
        if name == script:
            raise gate.artifact_gate.QualificationError("fictional private upstream payload")
        return original(name, *args)
    monkeypatch.setattr(gate.artifact_gate, "tool_receipt", failing)
    with pytest.raises(gate.QualificationError) as error:
        gate.qualify(*paths)
    assert "fictional private" not in str(error.value)


@pytest.mark.parametrize("bad", ["wheel_commit", "wheel_digest", "wheel_version"])
def test_rejects_wrong_wheel_origin_or_metadata(
    gate: Any, paths: tuple[Path, Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    _accept_fake_gates(gate, monkeypatch, paths[1])
    original = gate.artifact_gate.tool_receipt
    def fake(script: str, *args: object) -> dict[str, Any]:
        out = original(script, *args)
        if bad == "wheel_commit" and script == "check_core_wheel_source_identity.py":
            out["source_git_commit"] = "b" * 40
        if script == "inspect_release_wheel_metadata.py":
            if bad == "wheel_digest":
                out["sha256"] = "f" * 64
            if bad == "wheel_version":
                out["version"] = "9.9.9"
        return out
    monkeypatch.setattr(gate.artifact_gate, "tool_receipt", fake)
    with pytest.raises(gate.QualificationError):
        gate.qualify(*paths)


@pytest.mark.parametrize("bad", ["first_install", "second_install", "different_counts"])
def test_rejects_missing_or_divergent_installed_python_bytes(
    gate: Any, paths: tuple[Path, Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    _accept_fake_gates(gate, monkeypatch, paths[1])
    calls = 0
    def fake(*_args: object) -> int:
        nonlocal calls
        calls += 1
        if bad == "first_install" and calls == 1:
            raise gate.artifact_gate.QualificationError("fictional executable payload")
        if bad == "second_install" and calls == 2:
            raise gate.artifact_gate.QualificationError("fictional executable payload")
        if bad == "different_counts" and calls == 2:
            return 249
        return 250
    monkeypatch.setattr(gate.artifact_gate, "installed_wheel_matches", fake)
    with pytest.raises(gate.QualificationError):
        gate.qualify(*paths)


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "TECHNICAL_PREPUBLICATION_REHEARSAL_PASS"),
        ("installed_cli_count", 1),
        ("fhir_conformance_validated", True),
        ("publication_authorized", 0),
        ("clinical_use_authorized", "false"),
        ("prepublication_rehearsal_qualified", True),
        ("known_report_sha256", "not-digest"),
        ("unknown_report_sha256", "a" * 64),
    ],
)
def test_rejects_overstated_or_ambiguous_core_fhir_receipt(
    gate: Any, paths: tuple[Path, Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    _accept_fake_gates(gate, monkeypatch, paths[1])
    original = gate.fhir_gate.qualify
    def fake(clis: list[Path]) -> dict[str, Any]:
        out = original(clis)
        out[field] = value
        return out
    monkeypatch.setattr(gate.fhir_gate, "qualify", fake)
    with pytest.raises(gate.QualificationError):
        gate.qualify(*paths)


def test_missing_source_or_runtime_blocks_without_running_any_verifier(
    gate: Any, paths: tuple[Path, Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def should_not_run(*_a: object, **_kw: object) -> None:
        raise AssertionError("must reject before spawning verifiers")
    monkeypatch.setattr(gate.artifact_gate, "run", should_not_run)
    with pytest.raises(gate.QualificationError):
        gate.qualify(paths[0], paths[1], paths[2], paths[3], paths[3])
    with pytest.raises(gate.QualificationError):
        gate.qualify(paths[0], paths[1], paths[2], paths[3], paths[0] / "missing")


def test_main_does_not_echo_untrusted_paths_or_provide_positive_receipt(
    gate: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = tmp_path / "FICTIONAL-NEVER-ECHO-PATH"
    result = gate.main(
        ["--checkout", str(secret), "--wheel", str(secret), "--sdist", str(secret),
         "--python311", str(secret), "--python312", str(secret)]
    )
    assert result == 2
    captured = capsys.readouterr()
    assert "SOURCE_BOUND_LOCAL_FHIR_PROVENANCE_BLOCKED" in captured.err
    assert "FICTIONAL-NEVER-ECHO" not in captured.err
    assert not captured.out


def test_source_never_certifies_fhir_or_release_approval() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "SOURCE_BOUND_INSTALLED_FHIR_PROVENANCE_ONLY" in source
    assert '"publication_authorized": False' in source
    assert '"prepublication_rehearsal_qualified": False' in source
    assert '"merge_or_tag_authorized": False' in source
    assert "twine upload" not in source
    assert "gh release create" not in source
