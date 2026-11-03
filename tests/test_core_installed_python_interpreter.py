"""Adversarial read-only Windows CPython venv executable identity checks."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_installed_core_python_interpreter.py"
WINDOWS = pytest.mark.skipif(sys.platform != "win32", reason="Windows pinned executable QA")


@pytest.fixture
def gate() -> Any:
    spec = importlib.util.spec_from_file_location("windows_pinned_interpreter_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _synthetic_venv(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, Path, Path, Path, Path]:
    base = tmp_path / "fake-cpython-3.11"
    original = base / "Lib" / "venv" / "scripts" / "nt" / "python.exe"
    original.parent.mkdir(parents=True)
    base_binary = base / "python.exe"
    base_binary.write_bytes(b"MZ" + b"A" * (91648 - 2))
    loader_files = {
        "python3.dll": b"FICTIONAL PYTHON3 ABI DLL",
        "python311.dll": b"FICTIONAL PYTHON311 RUNTIME DLL",
        "vcruntime140.dll": b"FICTIONAL VC RUNTIME DLL",
        "vcruntime140_1.dll": b"FICTIONAL VC RUNTIME EXTENDED DLL",
    }
    for name, content in loader_files.items():
        (base / name).write_bytes(content)
    original.write_bytes(b"MZ" + b"B" * (262144 - 2))
    venv = tmp_path / "env311"
    python = venv / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_bytes(original.read_bytes())
    cfg = venv / "pyvenv.cfg"
    cfg.write_text(
        f"home = {base}\n"
        "include-system-site-packages = false\n"
        "version = 3.11.15\n"
        f"executable = {base_binary}\n"
        f"command = {base_binary} -m venv --without-pip {venv}\n",
        encoding="utf-8",
    )
    monkeypatch.setitem(
        gate.WINDOWS_PINNED,
        11,
        {
            "version": "3.11.15",
            "venv_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
            "base_sha256": hashlib.sha256(base_binary.read_bytes()).hexdigest(),
            "runtime_dlls": {
                name: (len(content), hashlib.sha256(content).hexdigest())
                for name, content in loader_files.items()
            },
        },
    )
    return python, cfg, base_binary, original, base


@WINDOWS
def test_exact_pinned_cpython_venv_source_checks_without_running_it(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python, _cfg, _exe, _original, _base = _synthetic_venv(gate, monkeypatch, tmp_path)
    receipt = gate.qualify(python, 11)
    assert receipt["status"] == gate.STATUS
    assert receipt["installed_python_source_matches_base"] is True
    assert receipt["installed_base_executable_matches_local_pin"] is True
    assert receipt["installed_base_runtime_dlls_verified"] == 4
    assert receipt["unqualified_venv_loader_shadow_files_rejected"] is True
    assert receipt["publication_authorized"] is False
    assert receipt["clinical_use_authorized"] is False
    assert receipt["python_vendor_authenticity_verified"] is False
    assert receipt["python_code_signature_verified"] is False


@WINDOWS
@pytest.mark.parametrize(
    "tamper",
    [
        "venv_executable",
        "source_executable",
        "base_executable",
        "missing_source",
        "short_venv",
        "config_version",
        "config_home",
        "config_executable",
        "config_inherit",
        "duplicate_version",
        "duplicate_executable",
        "missing_executable_key",
        "not_python_file",
        "base_python_dll_tamper",
        "base_python3_dll_missing",
        "base_vcruntime_dll_tamper",
        "venv_scripts_shadow_dll",
        "venv_root_shadow_dll",
        "venv_scripts_extension_pyd",
        "venv_scripts_python_pth",
    ],
)
def test_synthetic_replacement_or_configuration_ambiguity_refuses_before_use(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tamper: str
) -> None:
    python, cfg, base_exe, source, base = _synthetic_venv(gate, monkeypatch, tmp_path)
    if tamper == "venv_executable":
        data = bytearray(python.read_bytes())
        data[150] ^= 1
        python.write_bytes(data)
    elif tamper == "source_executable":
        data = bytearray(source.read_bytes())
        data[150] ^= 1
        source.write_bytes(data)
    elif tamper == "base_executable":
        data = bytearray(base_exe.read_bytes())
        data[150] ^= 1
        base_exe.write_bytes(data)
    elif tamper == "missing_source":
        source.unlink()
    elif tamper == "base_python_dll_tamper":
        (base / "python311.dll").write_bytes(b"FICTIONAL CHANGED PYTHON DLL")
    elif tamper == "base_python3_dll_missing":
        (base / "python3.dll").unlink()
    elif tamper == "base_vcruntime_dll_tamper":
        (base / "vcruntime140.dll").write_bytes(b"FICTIONAL CHANGED VC RUNTIME")
    elif tamper == "venv_scripts_shadow_dll":
        (python.parent / "python311.dll").write_bytes(b"FICTIONAL SHADOW DLL")
    elif tamper == "venv_root_shadow_dll":
        (python.parent.parent / "python3.dll").write_bytes(b"FICTIONAL SHADOW DLL")
    elif tamper == "venv_scripts_extension_pyd":
        (python.parent / "fictional_extension.pyd").write_bytes(b"FICTIONAL EXTENSION")
    elif tamper == "venv_scripts_python_pth":
        (python.parent / "python311._pth").write_text("FICTIONAL PTH\n")
    elif tamper == "short_venv":
        python.write_bytes(python.read_bytes()[:-1])
    elif tamper == "config_version":
        cfg.write_text(cfg.read_text().replace("version = 3.11.15", "version = 3.12.13"))
    elif tamper == "config_home":
        cfg.write_text(cfg.read_text().replace(str(base), str(base) + "_wrong"))
    elif tamper == "config_executable":
        cfg.write_text(
            cfg.read_text().replace(f"executable = {base_exe}", f"executable = {base_exe}.wrong")
        )
    elif tamper == "config_inherit":
        cfg.write_text(cfg.read_text().replace("packages = false", "packages = true"))
    elif tamper == "duplicate_version":
        cfg.write_text(cfg.read_text() + "version = 3.11.15\n")
    elif tamper == "duplicate_executable":
        cfg.write_text(cfg.read_text() + f"executable = {base_exe}\n")
    elif tamper == "missing_executable_key":
        cfg.write_text(cfg.read_text().replace("executable =", "executable-missing ="))
    else:
        alternate = python.with_name("renamed-python.exe")
        python.rename(alternate)
        python = alternate
    with pytest.raises(gate.QualificationError):
        gate.qualify(python, 11)


@WINDOWS
def test_cross_version_redirector_is_not_trusted_as_other_python(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python, _cfg, _base, _source, _root = _synthetic_venv(gate, monkeypatch, tmp_path)
    with pytest.raises(gate.QualificationError):
        gate.qualify(python, 12)


def test_unreviewed_interpreter_version_fails_closed(gate: Any, tmp_path: Path) -> None:
    python = tmp_path / "venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python.exe"
    with pytest.raises(gate.QualificationError):
        gate.qualify(python, 14)


def test_report_never_claims_independent_python_vendor_signoff(gate: Any) -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"python_vendor_authenticity_verified": False' in text
    assert '"python_code_signature_verified": False' in text
    assert '"publication_authorized": False' in text
