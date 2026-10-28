"""Synthetic-only desktop D0 reference-vector tests; no Rust runtime involved."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts/check_desktop_d0_vectors.py"


@pytest.fixture
def d0() -> ModuleType:
    spec = importlib.util.spec_from_file_location("medorigin_desktop_d0", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_vectors_match_source_bound_raw_bytes(d0: ModuleType) -> None:
    result = d0.verify_manifest()
    assert result["status"] == "SYNTHETIC_ONLY_NOT_RELEASED"
    assert result["publication_authorized"] is False
    assert result["rust_parity_qualified"] is False
    raw_cases = d0.case_bytes()
    assert len(raw_cases) == 4
    for item in result["vectors"]:
        raw = raw_cases[item["id"]]
        assert item["bytes"] == len(raw)
        assert item["sha256"] == hashlib.sha256(raw).hexdigest()


def test_raw_sha_keeps_padding_and_invalid_utf8(d0: ModuleType) -> None:
    cases = d0.case_bytes()
    assert cases["patient-invalid-utf8"] == bytes([0xFF])
    assert len(cases["patient-exact-limit"]) == 32768
    assert len(cases["patient-over-limit"]) == 32769
    assert cases["patient-exact-limit"].startswith(cases["patient-minimal"])
    assert (
        hashlib.sha256(cases["patient-exact-limit"]).digest()
        != hashlib.sha256(cases["patient-minimal"]).digest()
    )


def test_changed_manifest_is_blocked(d0: ModuleType, tmp_path: Path) -> None:
    original = d0._MANIFEST.read_text(encoding="utf-8")
    changed = original.replace(
        "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0",
        "0" * 64,
    )
    assert changed != original
    path = tmp_path / "untrusted.json"
    path.write_text(changed, encoding="utf-8")
    with pytest.raises(d0.FixtureContractError, match="manifest has drifted"):
        d0.verify_manifest(manifest_path=path)


def test_changed_source_contract_is_blocked(d0: ModuleType, tmp_path: Path) -> None:
    source = tmp_path / "changed.py"
    source.write_text("def not_the_original_fixture(): pass\n", encoding="utf-8")
    with pytest.raises(d0.FixtureContractError, match="source fixture expressions"):
        d0.verify_manifest(source_path=source)


@pytest.mark.parametrize("mode", [[], ["--emit"]])
def test_cli_is_read_only_and_successful(mode: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), *mode],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    if mode:
        output = json.loads(result.stdout)
        assert output["schema"] == "medorigin-desktop-d0-raw-sha256-v1"
        assert output["rust_parity_qualified"] is False
    else:
        assert "DESKTOP_D0_RAW_VECTORS_VERIFIED" in result.stdout
