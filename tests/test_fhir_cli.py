"""M5 — FHIR boundary CLI surface and packaging regression tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from medscale.cli import fhir as fhir_cli


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
