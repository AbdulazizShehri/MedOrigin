"""Security and scope contract of the standalone synthetic CLI example."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "synthetic_fhir_developer_beta"


def _module() -> Any:
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


def _preview_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "medorigin_synthetic_preview", EXAMPLE / "preview.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_static_preview_escapes_untrusted_receipt_fields() -> None:
    renderer = _preview_module()
    receipt = {
        "runs": [
            {
                "label": '<img src=x onerror="alert(1)">',
                "report_sha256": "</code><script>alert(2)</script>",
                "fixture_sha256": '"><iframe src="https://example.org/">',
                "structural_status": "valid",
                "malformed_exit": 1,
            }
        ]
    }
    html = renderer.render(receipt)
    assert "<script" not in html and "<iframe" not in html and "<img" not in html
    assert "&lt;script&gt;" in html and "&lt;img " in html
    assert "script-src 'none'" in html and "connect-src 'none'" in html
    assert "<link " not in html and "fetch(" not in html


def test_preview_refuses_failed_validation_and_rejected_negative_control() -> None:
    renderer = _preview_module()
    with pytest.raises(ValueError):
        renderer.render({"runs": [{"structural_status": "invalid", "malformed_exit": 1}]})
    with pytest.raises(ValueError):
        renderer.render({"runs": [{"structural_status": "valid", "malformed_exit": 0}]})


def test_preview_never_overwrites_existing_html(tmp_path: Path) -> None:
    renderer = _preview_module()
    receipt = tmp_path / "evidence.json"
    receipt.write_text(
        json.dumps(
            {"runs": [{"label": "synthetic", "structural_status": "valid", "malformed_exit": 1}]}
        ),
        encoding="utf-8",
    )
    output = tmp_path / "preview.html"
    output.write_text("existing unchanged", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        renderer.main(["--receipt", str(receipt), "--out", str(output)])
    assert error.value.code == 1
    assert output.read_text(encoding="utf-8") == "existing unchanged"


def test_optional_workspace_accepts_exact_synthetic_offline_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    module = _module()

    def fake_call(_python: Path, args: list[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
        if "-c" in args:
            return subprocess.CompletedProcess(args, 0, "0.1.0.dev1\n", "")
        return subprocess.CompletedProcess(
            args,
            0,
            json.dumps(
                {
                    "application": "medscale-workspace",
                    "data_class": "SYNTHETIC",
                    "mode": "offline-shell",
                    "ready": True,
                }
            ),
            "",
        )

    monkeypatch.setattr(module, "call", fake_call)
    status = module.verify_workspace_shell(Path(sys.executable), tmp_path)
    assert status == {
        "application": "medscale-workspace",
        "version": "0.1.0.dev1",
        "data_class": "SYNTHETIC",
        "mode": "offline-shell",
        "ready": True,
    }


def test_optional_workspace_rejects_extra_fields_without_echoing_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    module = _module()

    def fake_call(_python: Path, args: list[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
        if "-c" in args:
            return subprocess.CompletedProcess(args, 0, "0.1.0.dev1\n", "")
        return subprocess.CompletedProcess(
            args,
            0,
            json.dumps(
                {
                    "application": "medscale-workspace",
                    "data_class": "SYNTHETIC",
                    "mode": "offline-shell",
                    "ready": True,
                    "patient_name": "PRIVATE-SENTINEL-NEVER-LOG",
                }
            ),
            "",
        )

    monkeypatch.setattr(module, "call", fake_call)
    with pytest.raises(ValueError) as raised:
        module.verify_workspace_shell(Path(sys.executable), tmp_path)
    assert "PRIVATE-SENTINEL" not in str(raised.value)


@pytest.mark.parametrize(
    "payload",
    [
        '{"application":"medscale-workspace","data_class":"SYNTHETIC","mode":"offline-shell","ready":1}',
        '{"application":"medscale-workspace","data_class":"SYNTHETIC","mode":"offline-shell","ready":false,"ready":true}',
        '{"application":"medscale-workspace","data_class":"SYNTHETIC","mode":"offline-shell","patient_name":"PRIVATE-SENTINEL","patient_name":"removed","ready":true}',
    ],
)
def test_workspace_shell_rejects_ambiguous_json_types_and_duplicate_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: str
) -> None:
    import subprocess

    module = _module()

    def fake_call(_python: Path, args: list[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
        if "-c" in args:
            return subprocess.CompletedProcess(args, 0, "0.1.0.dev1\n", "")
        return subprocess.CompletedProcess(args, 0, payload, "")

    monkeypatch.setattr(module, "call", fake_call)
    with pytest.raises(ValueError) as raised:
        module.verify_workspace_shell(Path(sys.executable), tmp_path)
    assert "PRIVATE-SENTINEL" not in str(raised.value)


def test_workspace_version_mismatch_fails_closed_before_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    module = _module()

    def fake_call(_python: Path, args: list[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
        assert "-c" in args
        return subprocess.CompletedProcess(args, 0, "0.0.1\n", "")

    monkeypatch.setattr(module, "call", fake_call)
    with pytest.raises(ValueError, match=r"0\.1\.0\.dev1"):
        module.verify_workspace_shell(Path(sys.executable), tmp_path)


def test_static_preview_optional_workspace_card_has_no_extra_fields() -> None:
    preview = _preview_module()
    receipt = {
        "runs": [
            {
                "structural_status": "valid",
                "malformed_exit": 1,
                "label": "run_1",
            }
        ],
        "workspace": {
            "application": "medscale-workspace",
            "version": "0.1.0.dev1",
            "data_class": "SYNTHETIC",
            "mode": "offline-shell",
            "ready": True,
        },
    }
    page = preview.render(receipt)
    assert "Synthetic Workspace" in page
    assert "offline-shell / SYNTHETIC" in page
    assert "Synthetic-only demonstration" in page
    assert "clinical access" in page

    receipt["workspace"]["patient_name"] = "PRIVATE-SENTINEL"  # type: ignore[index]
    with pytest.raises(ValueError):
        preview.render(receipt)


def test_missing_workspace_python_rejected_without_making_output(tmp_path: Path) -> None:
    example = _module()
    out = tmp_path / "missing-output"
    with pytest.raises(SystemExit) as raised:
        example.main(
            [
                "--cli",
                str(Path(sys.executable)),
                "--workspace-python",
                str(tmp_path / "missing-python.exe"),
                "--out",
                str(out),
            ]
        )
    assert raised.value.code == 2
    assert not out.exists()
