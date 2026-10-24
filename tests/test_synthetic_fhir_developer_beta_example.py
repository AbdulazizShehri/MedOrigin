"""Security and scope contract of the standalone synthetic CLI example."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "synthetic_fhir_developer_beta"


def _module():
    spec = importlib.util.spec_from_file_location(
        "medorigin_synthetic_example", EXAMPLE / "reproduce.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_is_explicitly_synthetic_and_not_a_patient_record() -> None:
    payload = json.loads(
        (EXAMPLE / "synthetic_structure_definition.json").read_text(encoding="utf-8")
    )
    assert payload == {"resourceType": "StructureDefinition", "id": "medorigin-synthetic-demo"}
    assert (EXAMPLE / "malformed.json").read_text(encoding="utf-8").startswith("{invalid")


def test_refuses_overwriting_existing_evidence(tmp_path: Path) -> None:
    module = _module()
    output = tmp_path / "keep"
    output.mkdir()
    marker = output / "report.json"
    marker.write_text("preserve exactly", encoding="utf-8")
    with pytest.raises(SystemExit) as exit_info:
        module.main(["--cli", sys.executable, "--out", str(output)])
    assert exit_info.value.code == 2
    assert marker.read_text(encoding="utf-8") == "preserve exactly"


def test_missing_installed_cli_fails_before_creating_output(tmp_path: Path) -> None:
    module = _module()
    output = tmp_path / "should-not-exist"
    with pytest.raises(SystemExit) as exit_info:
        module.main(["--cli", str(tmp_path / "does-not-exist"), "--out", str(output)])
    assert exit_info.value.code == 2
    assert not output.exists()


def test_digests_match_fixture_bytes() -> None:
    module = _module()
    assert len(module.digest(EXAMPLE / "synthetic_structure_definition.json")) == 64
    assert "publication_authorized" in (EXAMPLE / "reproduce.py").read_text(encoding="utf-8")
