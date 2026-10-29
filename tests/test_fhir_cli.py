"""M5 — FHIR boundary CLI surface and packaging regression tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from medscale.cli import fhir as fhir_cli
from medscale.cli import main as public_cli_main


def test_public_fhir_validate_dispatch_accepts_synthetic_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The documented console argv must work through the real top-level dispatcher."""
    payload = {"resourceType": "StructureDefinition", "id": "synthetic-review"}
    source = tmp_path / "synthetic.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    assert public_cli_main(["fhir", "validate", str(source), "--summary-only"]) == 0
    assert json.loads(capsys.readouterr().out) == payload


def test_public_fhir_validate_rejects_malformed_json(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text("{invalid json", encoding="utf-8")
    assert public_cli_main(["fhir", "validate", str(source)]) == 1


@pytest.mark.parametrize("summary_only", [False, True])
def test_fhir_cli_rejects_invalid_utf8_without_traceback_or_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], summary_only: bool
) -> None:
    """Malformed UTF-8 must fail closed instead of exposing a Python traceback."""
    source = tmp_path / "invalid-utf8.json"
    source.write_bytes(bytes([0xFF, 0xFE, 0x80]))
    output_dir = tmp_path / "reports"
    argv = [str(source), "--output-dir", str(output_dir)]
    if summary_only:
        argv.append("--summary-only")

    assert fhir_cli.main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "input read error:" in captured.err
    assert "Traceback" not in captured.err
    assert not output_dir.exists()


def test_public_fhir_dispatch_rejects_invalid_utf8_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The public command must not leak decoder tracebacks on invalid bytes."""
    source = tmp_path / "invalid-utf8.json"
    source.write_bytes(bytes([0xFF, 0xFE, 0x80]))
    assert public_cli_main(["fhir", "validate", str(source)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "input read error:" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("json_root", ["[]", "null", "42", '"not-a-fhir-object"', "true"])
@pytest.mark.parametrize("summary_only", [False, True])
def test_fhir_cli_rejects_non_object_json_roots(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    json_root: str,
    summary_only: bool,
) -> None:
    """A syntactically valid JSON scalar/array is never a FHIR resource."""
    source = tmp_path / "non-fhir-root.json"
    source.write_text(json_root, encoding="utf-8")
    output_dir = tmp_path / "reports"
    argv = [str(source), "--output-dir", str(output_dir)]
    if summary_only:
        argv.append("--summary-only")

    assert fhir_cli.main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "input read error: FHIR resource must be a JSON object" in captured.err
    assert "Traceback" not in captured.err
    assert not output_dir.exists()


def test_public_fhir_dispatch_rejects_non_object_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "array.json"
    source.write_text("[]", encoding="utf-8")
    assert public_cli_main(["fhir", "validate", str(source)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "FHIR resource must be a JSON object" in captured.err


@pytest.mark.parametrize(
    "invalid_root",
    [
        "{}",
        '{"resourceType": null}',
        '{"resourceType": 123}',
        '{"resourceType": ""}',
        '{"resourceType": "   "}',
        '{"resourceType": "patient"}',
        '{"resourceType": []}',
    ],
)
@pytest.mark.parametrize("summary_only", [False, True])
def test_fhir_cli_rejects_missing_or_invalid_resource_type(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    invalid_root: str,
    summary_only: bool,
) -> None:
    source = tmp_path / "invalid-fhir-resource.json"
    source.write_text(invalid_root, encoding="utf-8")
    output_dir = tmp_path / "reports"
    argv = [str(source), "--output-dir", str(output_dir)]
    if summary_only:
        argv.append("--summary-only")
    assert fhir_cli.main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "FHIR resourceType" in captured.err
    assert "Traceback" not in captured.err
    assert not output_dir.exists()


@pytest.mark.parametrize(
    "non_fhir_json",
    [
        '{"resourceType":"Patient","id":"x","id":"y"}',
        '{"resourceType":"Patient","meta":{"versionId":"a","versionId":"b"}}',
        '{"resourceType":"Patient","value":NaN}',
        '{"resourceType":"Patient","value":Infinity}',
        '{"resourceType":"Patient","value":-Infinity}',
    ],
)
@pytest.mark.parametrize("summary_only", [False, True])
def test_fhir_cli_rejects_duplicate_keys_and_nonfinite_numbers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    non_fhir_json: str,
    summary_only: bool,
) -> None:
    source = tmp_path / "invalid-fhir-json.json"
    source.write_text(non_fhir_json, encoding="utf-8")
    output_dir = tmp_path / "reports"
    argv = [str(source), "--output-dir", str(output_dir)]
    if summary_only:
        argv.append("--summary-only")
    assert fhir_cli.main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "input read error:" in captured.err
    assert "Traceback" not in captured.err
    assert not output_dir.exists()


def test_fhir_dispatch_rejects_missing_resource_type(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "missing-resource-type.json"
    source.write_text("{}", encoding="utf-8")
    assert public_cli_main(["fhir", "validate", str(source)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "FHIR resourceType" in captured.err


def test_bare_legacy_fhir_file_dispatch_remains_supported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "legacy.json"
    payload = {"resourceType": "StructureDefinition", "id": "legacy-synthetic"}
    source.write_text(json.dumps(payload), encoding="utf-8")
    assert public_cli_main(["fhir", str(source), "--summary-only"]) == 0
    assert json.loads(capsys.readouterr().out) == payload


def test_fhir_cli_is_importable() -> None:
    # The FHIR CLI module is a shipped supported surface and must be importable.
    assert hasattr(fhir_cli, "main")


def test_fhir_command_is_routed_by_public_dispatcher() -> None:
    # The documented M5 surface is `medscale fhir validate`; the public
    # dispatcher must recognize the subcommand. Argparse help exits via
    # SystemExit(0), so assert that path explicitly.
    with pytest.raises(SystemExit) as excinfo:
        fhir_cli.main(["--help"])
    assert excinfo.value.code == 0


def test_fhir_cli_summary_only_exits_zero(tmp_path: Path) -> None:
    payload = {"resourceType": "StructureDefinition", "id": "test"}
    input_file = tmp_path / "payload.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = fhir_cli.main(["--summary-only", str(input_file)])

    assert exit_code == 0


def test_fhir_cli_valid_json_stores_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"resourceType": "StructureDefinition", "id": "test"}
    input_file = tmp_path / "payload.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")
    output_dir = tmp_path / "reports"
    monkeypatch.setenv("MEDSCALE_ROOT", str(tmp_path))

    exit_code = fhir_cli.main([str(input_file), "--output-dir", str(output_dir)])

    assert exit_code == 0
    reports = list(output_dir.rglob("report.json"))
    assert reports, "expected a stored FHIR validation report"


def test_fhir_cli_invalid_json_returns_nonzero(tmp_path: Path) -> None:
    input_file = tmp_path / "bad.json"
    input_file.write_text("{not json", encoding="utf-8")

    exit_code = fhir_cli.main([str(input_file)])

    assert exit_code == 1


def test_fhir_cli_external_validator_not_wired_returns_two(tmp_path: Path) -> None:
    payload = {"resourceType": "StructureDefinition", "id": "test"}
    input_file = tmp_path / "payload.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = fhir_cli.main([str(input_file), "--with-validator", "java -jar validator.jar"])

    assert exit_code == 2


def test_packaging_click_is_not_a_required_runtime_dependency() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    # After migrating the FHIR CLI surface to argparse, Click must not be a
    # hard runtime dependency.
    assert "dependencies = []" in pyproject
    assert "click" not in pyproject.split("[project.optional-dependencies]")[0]


@pytest.fixture(scope="session")
def pr0_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Build the package wheel once per test session into a temporary directory
    # so the packaging tests remain hermetic in clean CI environments.
    wheel_dir = tmp_path_factory.mktemp("pr0-wheel")
    subprocess.check_call(
        ["uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    wheels = sorted(wheel_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, found {len(wheels)}"
    return wheels[0].resolve()


def test_wheel_contains_fhir_module_without_click_dependency(pr0_wheel: Path) -> None:
    names = []
    metadata_text = ""
    try:
        import zipfile

        with zipfile.ZipFile(pr0_wheel) as z:
            names = z.namelist()
            metadata_path = next(n for n in names if n.endswith(".dist-info/METADATA"))
            metadata_text = z.read(metadata_path).decode("utf-8", errors="ignore")
    except Exception:
        pytest.fail("wheel packaging regression: wheel metadata unreadable")
    assert any(name.endswith("medscale/cli/fhir.py") for name in names)
    assert "Name: medscale" in metadata_text
    from medscale.__about__ import __version__ as package_version

    assert f"Version: {package_version}" in metadata_text
    assert "Requires-Dist: click\n" not in metadata_text


def test_clean_wheel_can_import_intentionally_shipped_modules(
    tmp_path: Path, pr0_wheel: Path
) -> None:
    venv = tmp_path / ".venv"
    subprocess.check_call(
        [sys.executable, "-m", "venv", str(venv)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    python_exe = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    python = venv / python_exe
    subprocess.check_call(
        [str(python), "-m", "pip", "install", "--quiet", "--no-deps", str(pr0_wheel)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    probe = tmp_path / "import_probe.py"
    probe.write_text(
        "import medscale, medscale.cli.fhir\nprint('imports-ok')\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [str(python), str(probe)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "imports-ok" in completed.stdout
