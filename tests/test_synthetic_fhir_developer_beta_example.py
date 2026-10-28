"""Security and scope contract of the standalone synthetic CLI example."""

from __future__ import annotations

import hashlib
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


@pytest.mark.parametrize("bad_exit", [True, 1.0, "1"])
def test_preview_renderer_refuses_ambiguous_boolean_or_coerced_exit(
    bad_exit: object,
) -> None:
    renderer = _preview_module()
    row = {"structural_status": "valid", "malformed_exit": bad_exit}
    with pytest.raises(ValueError, match="only verified valid"):
        renderer.render({"runs": [row]})


@pytest.mark.parametrize("bad_exit", [True, 1, 0.0])
def test_preview_renderer_refuses_failed_or_coerced_valid_exit(
    bad_exit: object,
) -> None:
    renderer = _preview_module()
    row = {"structural_status": "valid", "malformed_exit": 1, "valid_exit": bad_exit}
    with pytest.raises(ValueError, match="only verified valid"):
        renderer.render({"runs": [row]})


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
    numeric_ready = {
        "runs": [{"structural_status": "valid", "malformed_exit": 1}],
        "workspace": {
            "application": "medscale-workspace",
            "version": "0.1.0.dev1",
            "data_class": "SYNTHETIC",
            "mode": "offline-shell",
            "ready": 1,
        },
    }
    with pytest.raises(ValueError, match="synthetic-safe contract"):
        preview.render(numeric_ready)


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


def test_static_preview_long_labels_have_narrow_viewport_wrap_contract() -> None:
    renderer = _preview_module()
    receipt = {
        "runs": [
            {
                "label": "test <img src=x onerror=window.__medoriginInjected=true>" * 12,
                "structural_status": "valid",
                "malformed_exit": 1,
            }
        ]
    }
    html = renderer.render(receipt)
    assert "&lt;img src=x onerror=window.__medoriginInjected=true&gt;" in html
    assert "<img" not in html
    assert "grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))" in html
    assert "overflow-wrap:anywhere" in html
    assert "min-width:0" in html


def _synthetic_receipt_with_report(tmp_path: Path) -> dict[str, Any]:
    report = tmp_path / "reports_run_1" / "sha" / "report.json"
    report.parent.mkdir(parents=True)
    fixture = json.loads(
        (EXAMPLE / "synthetic_structure_definition.json").read_text(encoding="utf-8")
    )
    input_hash = hashlib.sha256(
        json.dumps(fixture, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    payload = {
        "created_at": "2026-10-24T00:00:00Z",
        "errors": [],
        "format_version": "fhirkit-validation-report/v1",
        "input_hash": input_hash,
        "report_id": "",
        "status": "valid",
        "validator_name": "medscale-fhirkit-local",
        "validator_version": "0.1.0",
        "warnings": [],
    }
    report.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    return {
        "schema": "medorigin-local-synthetic-fhir-example/v1",
        "scope": "synthetic structural validation, not full HL7 conformance",
        "publication_authorized": False,
        "clinical_authorized": False,
        "independent_review_completed": False,
        "runs": [
            {
                "label": "run_1",
                "installed_version": "medscale 0.3.0",
                "fixture_sha256": hashlib.sha256(
                    (EXAMPLE / "synthetic_structure_definition.json").read_bytes()
                ).hexdigest(),
                "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                "report_path": "reports_run_1/sha/report.json",
                "structural_status": "valid",
                "valid_exit": 0,
                "malformed_exit": 1,
            }
        ],
    }


def test_preview_cli_admits_exact_synthetic_receipt(tmp_path: Path) -> None:
    preview = _preview_module()
    receipt = _synthetic_receipt_with_report(tmp_path)
    source = tmp_path / "evidence.json"
    source.write_text(json.dumps(receipt), encoding="utf-8")
    output = tmp_path / "preview.html"
    assert preview.main(["--receipt", str(source), "--out", str(output)]) == 0
    html = output.read_text(encoding="utf-8")
    assert receipt["runs"][0]["report_sha256"] in html
    assert "script-src 'none'" in html


@pytest.mark.parametrize(
    "tamper",
    [
        "publication_true",
        "review_true",
        "extra_root_field",
        "patient_field",
        "boolean_exit",
        "wrong_label",
        "incorrect_fixture",
        "invalid_report_sha",
        "wrong_report_sha",
        "relative_traversal",
        "wrong_version",
        "unexpected_workspace",
        "wrong_scope",
        "invalid_structural_status",
    ],
)
def test_preview_cli_fail_closed_on_fake_synthetic_evidence(tmp_path: Path, tamper: str) -> None:
    preview = _preview_module()
    data = _synthetic_receipt_with_report(tmp_path)
    row = data["runs"][0]
    if tamper == "publication_true":
        data["publication_authorized"] = True
    elif tamper == "review_true":
        data["independent_review_completed"] = True
    elif tamper == "extra_root_field":
        data["patient_name"] = "PRIVATE-NOT-FOR-PREVIEW"
    elif tamper == "patient_field":
        row["patient_name"] = "PRIVATE-NOT-FOR-PREVIEW"
    elif tamper == "boolean_exit":
        row["malformed_exit"] = True
    elif tamper == "wrong_label":
        row["label"] = "another user"
    elif tamper == "incorrect_fixture":
        row["fixture_sha256"] = "a" * 64
    elif tamper == "invalid_report_sha":
        row["report_sha256"] = "<img onerror=alert(1)>"
    elif tamper == "wrong_report_sha":
        row["report_sha256"] = "a" * 64
    elif tamper == "relative_traversal":
        row["report_path"] = "../private/report.json"
    elif tamper == "wrong_version":
        row["installed_version"] = "medscale 0.2.0"
    elif tamper == "unexpected_workspace":
        data["workspace"] = {"application": "medscale-workspace", "ready": 1}
    elif tamper == "wrong_scope":
        data["scope"] = "clinical"
    elif tamper == "invalid_structural_status":
        row["structural_status"] = "unknown"

    source = tmp_path / "evidence.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    output = tmp_path / "preview.html"
    with pytest.raises(SystemExit) as raised:
        preview.main(["--receipt", str(source), "--out", str(output)])
    assert raised.value.code == 1
    assert not output.exists()


@pytest.mark.parametrize(
    "source_json",
    [
        '{"schema": "ok", "schema": "changed"}',
        '{"runs": [{"malformed_exit": 1, "malformed_exit": 0}]}',
        '{"workspace": {"ready": false, "ready": true}}',
    ],
)
def test_preview_cli_refuses_duplicate_json_keys(tmp_path: Path, source_json: str) -> None:
    preview = _preview_module()
    receipt = tmp_path / "evidence.json"
    receipt.write_text(source_json, encoding="utf-8")
    destination = tmp_path / "preview.html"
    with pytest.raises(SystemExit) as raised:
        preview.main(["--receipt", str(receipt), "--out", str(destination)])
    assert raised.value.code == 1
    assert not destination.exists()


def test_preview_cli_refuses_report_bytes_changed_after_receipt(tmp_path: Path) -> None:
    preview = _preview_module()
    receipt = _synthetic_receipt_with_report(tmp_path)
    report = tmp_path / receipt["runs"][0]["report_path"]
    report.write_text('{"status":"invalid"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        preview.admit_receipt(receipt, directory=tmp_path)


def test_preview_cli_refuses_ambiguous_report_json(tmp_path: Path) -> None:
    preview = _preview_module()
    receipt = _synthetic_receipt_with_report(tmp_path)
    report = tmp_path / receipt["runs"][0]["report_path"]
    report.write_text('{"status":"invalid","status":"valid"}', encoding="utf-8")
    receipt["runs"][0]["report_sha256"] = hashlib.sha256(report.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="duplicate key"):
        preview.admit_receipt(receipt, directory=tmp_path)


@pytest.mark.parametrize(
    ("field", "tampered_value"),
    [
        ("input_hash", "0" * 64),
        ("created_at", "2026-10-27T00:00:00Z"),
        ("validator_name", "untrusted-fhir-validator"),
        ("errors", ["hidden error"]),
        ("patient_name", "FICTIONAL-SENTINEL-NOT-ALLOWED"),
    ],
)
def test_preview_rejects_rehashed_forged_report(
    tmp_path: Path, field: str, tampered_value: object
) -> None:
    """Both report and receipt digests can be forged without report-schema validation."""
    preview = _preview_module()
    receipt = _synthetic_receipt_with_report(tmp_path)
    report = tmp_path / receipt["runs"][0]["report_path"]
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload[field] = tampered_value
    report.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    receipt["runs"][0]["report_sha256"] = hashlib.sha256(report.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="synthetic report identity or content invalid"):
        preview.admit_receipt(receipt, directory=tmp_path)
