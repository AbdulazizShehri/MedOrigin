"""Offline, fail-closed Developer Beta publication rehearsal controls."""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qualify_medorigin_developer_beta.py"


@pytest.fixture
def rehearsal() -> Any:
    spec = importlib.util.spec_from_file_location("medorigin_release_rehearsal", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rehearsal_rejects_failed_subprocess_without_echoing_payload(rehearsal: Any) -> None:
    with pytest.raises(rehearsal.QualificationError) as exc:
        rehearsal.run([sys.executable, "-c", "import sys; print('PATIENT-SECRET'); sys.exit(5)"])
    assert "PATIENT-SECRET" not in str(exc.value)


@pytest.mark.parametrize(
    "tamper",
    [
        {"status": "METADATA_QUALIFIED_ONLY", "issues": ["security"]},
        {"status": "METADATA_QUALIFIED_ONLY", "publication_authorized": True},
        {"status": "WRONG_STATUS"},
        {"status": "METADATA_QUALIFIED_ONLY", "issues": None},
        {"status": "METADATA_QUALIFIED_ONLY", "publication_authorized": 0},
        {"status": "METADATA_QUALIFIED_ONLY", "publication_authorized": "false"},
    ],
)
def test_rehearsal_rejects_incomplete_or_false_verifier_receipts(
    rehearsal: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tamper: dict[str, Any]
) -> None:
    receipt = {
        "status": "METADATA_QUALIFIED_ONLY",
        "issues": [],
        "publication_authorized": False,
    }
    receipt.update(tamper)
    monkeypatch.setattr(rehearsal, "run", lambda *_a, **_k: json.dumps(receipt))
    with pytest.raises(rehearsal.QualificationError):
        rehearsal.tool_receipt(
            "inspect_release_wheel_metadata.py", [], "METADATA_QUALIFIED_ONLY", tmp_path
        )


def test_rehearsal_accepts_only_explicit_nonpublishing_receipt(
    rehearsal: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "status": "SDIST_SCOPE_QUALIFIED_ONLY",
        "issues": [],
        "publication_authorized": False,
    }
    monkeypatch.setattr(rehearsal, "run", lambda *_a, **_k: json.dumps(payload))
    observed = rehearsal.tool_receipt(
        "check_sdist_publication_scope.py", [], "SDIST_SCOPE_QUALIFIED_ONLY", tmp_path
    )
    assert observed == payload


def test_rehearsal_refuses_empty_or_truncated_wheel_inventory(
    rehearsal: Any, tmp_path: Path
) -> None:
    wheel = tmp_path / "candidate.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("medscale/__init__.py", "# not enough source\n")
    with pytest.raises(rehearsal.QualificationError):
        rehearsal.installed_wheel_matches(wheel, Path(sys.executable), 11)


def test_rehearsal_fails_missing_inputs_without_creating_artifacts(
    rehearsal: Any, tmp_path: Path
) -> None:
    assert (
        rehearsal.main(
            [
                "--checkout",
                str(tmp_path / "missing-checkout"),
                "--wheel",
                str(tmp_path / "missing.whl"),
                "--sdist",
                str(tmp_path / "missing.tar.gz"),
                "--python311",
                sys.executable,
                "--python312",
                sys.executable,
            ]
        )
        == 2
    )
    assert list(tmp_path.iterdir()) == []


def test_rehearsal_diagnostic_identifies_verifier_without_echoing_tool_output(
    rehearsal: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def reject(*_args: object, **_kwargs: object) -> str:
        raise rehearsal.QualificationError("local qualification command failed; PATIENT-SECRET")

    monkeypatch.setattr(rehearsal, "run", reject)
    with pytest.raises(rehearsal.QualificationError) as exc:
        rehearsal.tool_receipt(
            "check_core_wheel_source_identity.py",
            [],
            "SOURCE_BOUND_WHEEL_QUALIFIED_ONLY",
            tmp_path,
        )
    assert str(exc.value) == ("local artifact verifier failed: check_core_wheel_source_identity.py")
    assert "PATIENT-SECRET" not in str(exc.value)


def test_rehearsal_preserves_virtualenv_python_symlink(
    rehearsal: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    base = tmp_path / "base-python"
    base.write_text("synthetic interpreter placeholder", encoding="utf-8")
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    launcher = bin_dir / "python"
    try:
        launcher.symlink_to(base)
    except (OSError, NotImplementedError):
        pytest.skip("host does not permit creating symlinks")
    captured: list[Path] = []

    def fake_qualify(
        _checkout: Path, _wheel: Path, _sdist: Path, python311: Path, python312: Path
    ) -> dict[str, object]:
        captured.extend((python311, python312))
        return {"status": "SYNTHETIC_TEST_ONLY", "publication_authorized": False}

    monkeypatch.setattr(rehearsal, "qualify", fake_qualify)
    assert (
        rehearsal.main(
            [
                "--checkout",
                str(tmp_path),
                "--wheel",
                str(tmp_path / "wheel.whl"),
                "--sdist",
                str(tmp_path / "archive.tar.gz"),
                "--python311",
                str(launcher),
                "--python312",
                str(launcher),
            ]
        )
        == 0
    )
    assert captured == [launcher.absolute(), launcher.absolute()]
    assert launcher.resolve() == base.resolve()


def test_rehearsal_has_no_publish_paths_or_credentials() -> None:
    content = SCRIPT.read_text(encoding="utf-8")
    for command in ("twine upload", "gh release create", "git push", "hf upload", "pip install -U"):
        assert command not in content
    assert '"publication_authorized": False' in content
    assert '"merge_or_tag_authorized": False' in content
