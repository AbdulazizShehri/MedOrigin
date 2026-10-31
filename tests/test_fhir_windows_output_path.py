"""Windows report output roots must not initiate UNC/device filesystem access."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale.cli import fhir as fhir_cli
from medscale.fhirkit.errors import FhirStorageError
from medscale.fhirkit.storage import load_report, store_report
from medscale.fhirkit.validate import validate_fhir


@pytest.fixture
def deny_network_root_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail before a Windows network namespace is ever probed."""
    original_is_symlink = Path.is_symlink
    original_mkdir = Path.mkdir

    def guarded_is_symlink(self: Path) -> bool:
        if str(self).startswith("\\\\"):
            raise AssertionError("UNC output path reached is_symlink")
        return original_is_symlink(self)

    def guarded_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        if str(self).startswith("\\\\"):
            raise AssertionError("UNC output path reached mkdir")
        original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "is_symlink", guarded_is_symlink)
    monkeypatch.setattr(Path, "mkdir", guarded_mkdir)


@pytest.mark.skipif(os.name != "nt", reason="Windows namespace semantics only")
@pytest.mark.parametrize(
    "root",
    [
        r"\\127.0.0.1\unreachable\reports",
        r"\\?\UNC\127.0.0.1\unreachable\reports",
        r"\\.\NUL",
    ],
)
def test_cli_rejects_unsafe_report_root_before_io(
    root: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    deny_network_root_probe: None,
) -> None:
    source = tmp_path / "fictional.json"
    source.write_text('{"resourceType":"Patient","id":"fictional"}', encoding="utf-8")
    assert fhir_cli.main([str(source), "--output-dir", root]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "report storage error:" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.skipif(os.name != "nt", reason="Windows namespace semantics only")
def test_storage_api_rejects_unc_report_root_before_io(
    deny_network_root_probe: None,
) -> None:
    report = validate_fhir({"resourceType": "Patient", "id": "fictional"})
    with pytest.raises(FhirStorageError, match="local"):
        store_report(report, root=Path(r"\\127.0.0.1\unreachable\reports"))
    with pytest.raises(FhirStorageError, match="local"):
        load_report("a" * 64, root=Path(r"\\127.0.0.1\unreachable\reports"))


@pytest.mark.parametrize(
    "raw",
    [
        r"\\127.0.0.1\share\reports",
        r"\\?\C:\reports",
        r"\\.\NUL",
        r"C:relative-reports",
        r"C:\reports:alternate",
        r"C:\safe\CON.txt",
        r"C:\safe\trailing-dot.",
    ],
)
def test_report_root_lexical_gate_cross_platform(raw: str) -> None:
    from medscale._windows_path_admission import reject_unsafe_windows_local_path

    with pytest.raises(ValueError, match="FHIR report root must be a local regular file path"):
        reject_unsafe_windows_local_path(raw, windows=True, subject="FHIR report root")


@pytest.mark.parametrize("raw", [r"C:\safe\reports", r".\reports", "reports"])
def test_report_root_local_path_accepted_cross_platform(raw: str) -> None:
    from medscale._windows_path_admission import reject_unsafe_windows_local_path

    reject_unsafe_windows_local_path(raw, windows=True, subject="FHIR report root")
