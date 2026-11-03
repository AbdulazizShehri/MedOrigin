"""Read-only tests for the installed Core CLI's nonclinical FHIR provenance gate."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_installed_core_fhir_provenance.py"


@pytest.fixture
def gate() -> Any:
    spec = importlib.util.spec_from_file_location("core_fhir_provenance_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_report(gate: Any, payload: dict[str, Any]) -> dict[str, object]:
    return {
        "created_at": gate.TIMESTAMP,
        "errors": [],
        "format_version": "fhirkit-validation-report/v1",
        "input_hash": gate._input_hash(payload),
        "report_id": "",
        "status": "not_validated",
        "validator_name": "medscale-fhirkit-local",
        "validator_version": "0.1.0",
        "warnings": [gate.WARNING],
    }


def test_known_fictional_fixture_is_still_pinned(gate: Any) -> None:
    assert json.loads(gate.KNOWN.read_text(encoding="utf-8")) == {
        "resourceType": "StructureDefinition",
        "id": "medorigin-synthetic-demo",
    }
    assert gate.MALFORMED.read_text(encoding="utf-8").startswith("{invalid")


def test_exact_output_and_persisted_report_match_under_cli_newline_rule(
    gate: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"resourceType": "UnknownFictionalResource", "id": "fictional"}
    data = _canonical_report(gate, payload)
    blob = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()

    def fake_call(_cli: Path, args: list[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
        dest = Path(args[args.index("--output-dir") + 1])
        receipt = dest / "fhirkit/reports/fictional/report.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_bytes(blob)
        return subprocess.CompletedProcess(args, 2, blob.decode() + "\n", "")

    monkeypatch.setattr(gate, "call", fake_call)
    sha = gate._report_case(Path("fake"), tmp_path / "fictional.json", payload, tmp_path, "test")
    assert sha == gate._hash(blob)


@pytest.mark.parametrize(
    "tamper",
    [
        "valid_claim",
        "warning_removed",
        "wrong_input_hash",
        "wrong_exit",
        "unexpected_field",
        "unexpected_error",
        "stored_report_modified",
        "extra_stdout_newlines",
        "duplicate_report_status",
    ],
)
def test_rejects_unsafe_or_ambiguous_installed_cli_reports(
    gate: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    payload = {"resourceType": "UnknownFictionalResource", "id": "fictional"}
    data = _canonical_report(gate, payload)
    if tamper == "valid_claim":
        data["status"] = "valid"
    elif tamper == "warning_removed":
        data["warnings"] = []
    elif tamper == "wrong_input_hash":
        data["input_hash"] = "f" * 64
    elif tamper == "unexpected_field":
        data["patient_data"] = "FICTIONAL-SECRET-NEVER-LOG"
    elif tamper == "unexpected_error":
        data["errors"] = ["hidden validation error"]
    blob = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if tamper == "duplicate_report_status":
        raw = blob.decode().replace(
            '"status":"not_validated"', '"status":"valid","status":"not_validated"'
        )
        blob = raw.encode()
    saved = blob
    if tamper == "stored_report_modified":
        saved = b'{"status":"valid"}\n'
    stdout = blob.decode() + ("\n\n" if tamper == "extra_stdout_newlines" else "\n")
    exit_code = 0 if tamper == "wrong_exit" else 2

    def fake_call(_cli: Path, args: list[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
        dest = Path(args[args.index("--output-dir") + 1])
        receipt = dest / "fhirkit/reports/fictional/report.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_bytes(saved)
        return subprocess.CompletedProcess(args, exit_code, stdout, "")

    monkeypatch.setattr(gate, "call", fake_call)
    with pytest.raises(gate.QualificationError) as error:
        gate._report_case(Path("fake"), tmp_path / "fictional.json", payload, tmp_path, "test")
    assert "FICTIONAL-SECRET" not in str(error.value)


def test_json_parser_fails_closed_on_duplicate_keys(gate: Any) -> None:
    with pytest.raises(gate.QualificationError, match="ambiguous"):
        gate._object('{"status":"valid","status":"not_validated"}')
    with pytest.raises(gate.QualificationError):
        gate._object("[]")


def test_two_installed_receipts_match_but_never_authorize_release(
    gate: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    known = "a" * 64
    unknown = "b" * 64

    def fake_run(cli: Path, _root: Path, _label: str) -> dict[str, str]:
        assert str(cli) in {"first", "second"}
        return {"known_report_sha256": known, "unknown_report_sha256": unknown}

    monkeypatch.setattr(gate, "_run_one", fake_run)
    receipt = gate.qualify([Path("first"), Path("second")])
    assert receipt["status"] == "LOCAL_FHIR_PROVENANCE_ONLY"
    assert receipt["installed_cli_count"] == 2
    assert receipt["execution_mode"] == "unattested_installed_console_shim"
    assert receipt["known_report_sha256"] != receipt["unknown_report_sha256"]
    for field in (
        "fhir_conformance_validated",
        "publication_authorized",
        "clinical_use_authorized",
        "independent_security_review_complete",
        "prepublication_rehearsal_qualified",
    ):
        assert receipt[field] is False


def test_different_runtime_report_receipts_are_refused(
    gate: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(_cli: Path, _root: Path, label: str) -> dict[str, str]:
        return {"known_report_sha256": "a" * 64 if label == "run_1" else "b" * 64}

    monkeypatch.setattr(gate, "_run_one", fake_run)
    with pytest.raises(gate.QualificationError, match="disagree"):
        gate.qualify([Path("first"), Path("second")])


def test_same_installed_cli_cannot_claim_independent_runtimes(gate: Any) -> None:
    with pytest.raises(gate.QualificationError, match="independent"):
        gate.qualify([Path("identical"), Path("identical")])


def test_cli_refuses_missing_installed_executable_without_path_leak(
    gate: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = gate.main(["--cli", str(tmp_path / "FICTIONAL-PRIVATE-MISSING")])
    assert code == 2
    output = capsys.readouterr()
    assert "CORE_FHIR_PROVENANCE_BLOCKED" in output.err
    assert "FICTIONAL-PRIVATE" not in output.err
    assert not output.out


def test_untrusted_cli_output_never_leaks_into_error(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(*_a: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 1, "FICTIONAL-SECRET" * 5000, "")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    with pytest.raises(gate.QualificationError) as error:
        gate.call(Path("fake"), ["--version"], tmp_path)
    assert "FICTIONAL-SECRET" not in str(error.value)


def test_cli_subprocess_strips_python_startup_and_dynamic_loader_overrides(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name, value in (
        ("PYTHONPATH", "FICTIONAL-OUTSIDE-PACKAGE"),
        ("PYTHONHOME", "FICTIONAL-HOME"),
        ("PYTHONUSERBASE", "FICTIONAL-USER-SITE"),
        ("PYTHONWARNINGS", "error::Warning:FICTIONAL-UNTRUSTED"),
        ("PYTHONINSPECT", "1"),
        ("PYTHONSTARTUP", "FICTIONAL-STARTUP"),
        ("LD_PRELOAD", "FICTIONAL-SHARED-OBJECT"),
        ("LD_LIBRARY_PATH", "FICTIONAL-DYNAMIC-LIBRARY"),
        ("DYLD_INSERT_LIBRARIES", "FICTIONAL-INJECTED-LIBRARY"),
    ):
        monkeypatch.setenv(name, value)
    observed: list[dict[str, str]] = []

    def fake_run(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        env = kwargs["env"]
        assert isinstance(env, dict)
        observed.append(env)
        return subprocess.CompletedProcess([], 0, "synthetic", "")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    result = gate.call(Path("fictional-cli"), ["--version"], tmp_path)
    assert result.returncode == 0
    assert len(observed) == 1
    env = observed[0]
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONUSERBASE",
        "PYTHONWARNINGS",
        "PYTHONINSPECT",
        "PYTHONSTARTUP",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "DYLD_INSERT_LIBRARIES",
    ):
        assert key not in env
    for key in ("PYTHONNOUSERSITE", "PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE"):
        assert env[key] == "1"
    for key in ("PIP_NO_INDEX", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        assert env[key] == "1"


def test_real_python_process_does_not_execute_inherited_sitecustomize(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    external = tmp_path / "fictional-ambient-python"
    external.mkdir()
    marker = tmp_path / "must-not-exist.txt"
    (external / "sitecustomize.py").write_text(
        "import os\n"
        "from pathlib import Path\n"
        "Path(os.environ['MEDORIGIN_QA_MARKER']).write_text('ambient executed')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONPATH", str(external))
    monkeypatch.setenv("MEDORIGIN_QA_MARKER", str(marker))
    result = gate.call(
        Path(sys.executable),
        ["-c", "import sys; print('ISOLATED', sys.version_info.minor)"],
        tmp_path,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("ISOLATED ")
    assert not marker.exists(), "outside-Wheel sitecustomize must not execute"


def test_subprocess_timeout_is_a_bounded_failure(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(*_a: object, **_kw: object) -> None:
        raise subprocess.TimeoutExpired("fictional", 30)

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    with pytest.raises(gate.QualificationError, match="could not complete"):
        gate.call(Path("fake"), ["--version"], tmp_path)


def test_trusted_python_invocation_bypasses_unqualified_console_shim(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_cli = tmp_path / ("medscale.exe" if sys.platform == "win32" else "medscale")
    fake_cli.write_text("FICTIONAL-UNTRUSTED-EXECUTABLE", encoding="utf-8")
    python = tmp_path / ("python.exe" if sys.platform == "win32" else "python")
    python.write_text("FICTIONAL-PYTHON", encoding="utf-8")
    captured: list[list[str]] = []

    def spy(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        captured.append(argv)
        return subprocess.CompletedProcess(argv, 0, "synthetic", "")

    monkeypatch.setattr(gate.subprocess, "run", spy)
    result = gate.call(fake_cli, ["--version"], tmp_path, trusted_python=python)
    assert result.returncode == 0
    assert captured == [
        [
            str(python),
            "-E",
            "-s",
            "-P",
            "-c",
            "from medscale.cli import main; raise SystemExit(main())",
            "--version",
        ]
    ]
    assert str(fake_cli) not in captured[0]


@pytest.mark.parametrize("invalid", ["missing", "mismatch", "duplicate"])
def test_trusted_interpreters_must_match_each_installed_cli_venv(
    gate: Any, tmp_path: Path, invalid: str
) -> None:
    first = tmp_path / "venv1" / "bin"
    second = tmp_path / "venv2" / "bin"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    cli1 = first / "medscale"
    cli2 = second / "medscale"
    python1 = first / "python"
    python2 = second / "python"
    for path in (cli1, cli2, python1, python2):
        path.write_text("synthetic", encoding="utf-8")
    interpreters = {
        "missing": [python1],
        "mismatch": [python2, python1],
        "duplicate": [python1, python1],
    }[invalid]
    with pytest.raises(gate.QualificationError, match="interpreter"):
        gate.qualify([cli1, cli2], interpreters=interpreters)


def test_local_script_never_claims_validated_fhir_or_approved_release(gate: Any) -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "LOCAL_FHIR_PROVENANCE_ONLY" in script
    assert '"not_validated"' in script
    assert '"valid"' not in script
    assert "publication_authorized" in script
    assert "prepublication_rehearsal_qualified" in script
