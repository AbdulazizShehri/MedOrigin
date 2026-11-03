"""Offline, read-only installed console-launcher template adversarial checks."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_installed_core_console_launcher.py"


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> Any:
    spec = importlib.util.spec_from_file_location("pinned_launcher_gate_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sample_windows(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, Path, bytes]:
    base = tmp_path / "venv" / "Scripts"
    base.mkdir(parents=True)
    python = base / "python.exe"
    python.write_bytes(b"FICTIONAL INTERPRETER FILE")
    stub = b"MZ" + b"0" * (gate.WIN64_PE_PREFIX_LENGTH - 2)
    monkeypatch.setattr(gate, "WIN64_PE_PREFIX_SHA256", hashlib.sha256(stub).hexdigest())
    payload = io.BytesIO()
    member = zipfile.ZipInfo("__main__.py", date_time=(2026, 11, 4, 1, 0, 0))
    member.compress_type = zipfile.ZIP_STORED
    member.create_system = 0
    member.external_attr = 25_165_824
    with zipfile.ZipFile(payload, mode="w") as archive:
        archive.writestr(member, gate.WINDOWS_MAIN)
    assert len(payload.getvalue()) == 260
    wrapper = stub + b"#!" + str(python).encode("utf-8") + b"\n" + payload.getvalue()
    cli = base / "medscale.exe"
    cli.write_bytes(wrapper)
    return cli, python, wrapper


def test_exact_synthetic_windows_template_passes_without_execution(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cli, python, contents = _sample_windows(gate, monkeypatch, tmp_path)
    gate._check_windows_launcher(contents, python)
    assert cli.read_bytes() == contents
    assert b"FICTIONAL INTERPRETER FILE" not in contents


@pytest.mark.parametrize(
    "mutation",
    [
        "pe_prefix",
        "shebang",
        "target_path",
        "embedded_code",
        "central_header",
        "local_header",
        "zip_trailer",
        "suffix",
        "prefix",
        "double",
        "truncated",
    ],
)
def test_windows_template_rejects_unqualified_bytes(
    gate: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutation: str
) -> None:
    _cli, python, wrapper = _sample_windows(gate, monkeypatch, tmp_path)
    data = bytearray(wrapper)
    shebang_start = gate.WIN64_PE_PREFIX_LENGTH
    zip_start = shebang_start + len(b"#!" + str(python).encode("utf-8") + b"\n")
    if mutation == "pe_prefix":
        data[100] ^= 1
    elif mutation == "shebang":
        data[shebang_start + 2] ^= 1
    elif mutation == "target_path":
        data[shebang_start + 8] ^= 1
    elif mutation == "embedded_code":
        data[zip_start + 55] ^= 1
    elif mutation == "central_header":
        data[zip_start + 181] ^= 1
    elif mutation == "local_header":
        data[zip_start] ^= 1
    elif mutation == "zip_trailer":
        data[-22] ^= 1
    elif mutation == "suffix":
        data += b"FICTIONAL-EXTRA-CODE"
    elif mutation == "prefix":
        data = bytearray(b"FICTIONAL-PREFIX") + data
    elif mutation == "double":
        data = data + data
    else:
        data = data[:-1]
    with pytest.raises(gate.QualificationError, match="Windows console launcher"):
        gate._check_windows_launcher(bytes(data), python)


def test_posix_pinned_script_accepts_exact_known_template(gate: Any, tmp_path: Path) -> None:
    python = tmp_path / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    expected = b"#!" + str(python).encode() + b"\n" + gate.UNIX_MAIN
    gate._check_unix_launcher(expected, python)


@pytest.mark.parametrize("mutation", ["shebang", "body", "suffix", "prefix"])
def test_posix_pinned_script_rejects_modified_code_or_target(
    gate: Any, tmp_path: Path, mutation: str
) -> None:
    python = tmp_path / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    original = b"#!" + str(python).encode() + b"\n" + gate.UNIX_MAIN
    if mutation == "shebang":
        altered = original.replace(b"python\n", b"pytbon\n", 1)
    elif mutation == "body":
        altered = original.replace(
            b"from medscale.cli import main", b"from fictional.cli import main", 1
        )
    elif mutation == "suffix":
        altered = original + b"\nimport fictional_code\n"
    else:
        altered = b"FICTIONAL START" + original
    assert altered != original
    with pytest.raises(gate.QualificationError, match="Linux console launcher"):
        gate._check_unix_launcher(altered, python)


def test_fictional_unqualified_launcher_refused_before_any_runtime(
    gate: Any, tmp_path: Path
) -> None:
    root = tmp_path / "venv" / ("Scripts" if sys.platform == "win32" else "bin")
    root.mkdir(parents=True)
    cli = root / ("medscale.exe" if sys.platform == "win32" else "medscale")
    python = root / ("python.exe" if sys.platform == "win32" else "python")
    cli.write_bytes(b"FICTIONAL-UNQUALIFIED-LAUNCHER")
    python.write_bytes(b"FICTIONAL-PYTHON")
    with pytest.raises(gate.QualificationError):
        gate.qualify(cli, python)


def test_pinned_launcher_receipt_is_never_a_release_approval(gate: Any) -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'STATUS = "PINNED_CONSOLE_LAUNCHER_TEMPLATE_ONLY"' in text
    assert '"publication_authorized": False' in text
    assert '"independent_security_review_complete": False' in text
    assert '"clinical_use_authorized": False' in text
