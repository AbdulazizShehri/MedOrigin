"""Windows FHIR input path admission: no SMB/device/ADS access before filesystem IO."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from medscale.cli import fhir as fhir_cli


@pytest.mark.parametrize(
    "raw",
    [
        r"\\server\share\fictional.json",
        r"//server/share/fictional.json",
        r"\\?\UNC\server\share\fictional.json",
        r"\\?\C:\fictional.json",
        r"\\.\NUL",
        r"\Device\HarddiskVolume1\fictional.json",
        r"C:drive-relative.json",
        r"C:\fictional.json:alternate",
        r"fictional.json:alternate",
        r"C:\safe\NUL.txt",
        r"C:\safe\COM1",
        r"C:\safe\LPT9.log",
        r"C:\safe\CONIN$",
        r"C:\safe\trailing-dot.",
    ],
)
def test_windows_unsafe_paths_rejected_before_any_file_io(raw: str) -> None:
    with pytest.raises(ValueError, match="local regular file path"):
        fhir_cli._reject_unsafe_windows_fhir_path(raw, windows=True)


@pytest.mark.parametrize(
    "raw",
    [
        r"C:\safe\fictional.json",
        r"C:/safe/fictional.json",
        r".\fictional.json",
        r"fictional.json",
        r"subdir\fictional.json",
    ],
)
def test_windows_normal_local_paths_are_allowed(raw: str) -> None:
    fhir_cli._reject_unsafe_windows_fhir_path(raw, windows=True)


@pytest.mark.skipif(os.name != "nt", reason="Windows CLI path boundary only")
@pytest.mark.parametrize(
    "raw",
    [
        r"\\127.0.0.1\nonexistent\fictional.json",
        r"\\?\C:\fictional.json",
        r"\\.\NUL",
        r"C:relative.json",
        r"C:\fictional.json:alternate",
    ],
)
@pytest.mark.parametrize("summary_only", [False, True])
def test_windows_cli_rejects_before_path_exists(
    raw: str,
    summary_only: bool,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    original_exists = Path.exists

    def forbidden_probe(self: Path) -> bool:
        if str(self) == str(Path(raw)):
            raise AssertionError("unsafe Windows path reached filesystem probing")
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", forbidden_probe)
    args = [raw, "--output-dir", str(tmp_path / "reports")]
    if summary_only:
        args.append("--summary-only")
    assert fhir_cli.main(args) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "input read error: FHIR JSON input must be a local regular file path" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.skipif(os.name != "nt", reason="Windows filesystem preflight only")
def test_windows_cli_does_not_preflight_exists_on_local_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "fictional.json"
    source.write_text('{"resourceType":"Patient","id":"fictional"}', encoding="utf-8")
    original_exists = Path.exists

    def no_source_exists(self: Path) -> bool:
        if self == source:
            raise AssertionError("Path.exists can follow a local symlink to a remote UNC")
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", no_source_exists)
    assert fhir_cli.main([str(source), "--summary-only"]) == 0
    assert '"resourceType": "Patient"' in capsys.readouterr().out


@pytest.mark.skipif(os.name != "nt", reason="Windows symlink preflight only")
def test_windows_cli_rejects_local_symlink_without_following_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "fictional-link.json"
    original_exists = Path.exists
    original_is_symlink = Path.is_symlink

    def no_source_exists(self: Path) -> bool:
        if self == source:
            raise AssertionError("symlink target must not be followed by Path.exists")
        return original_exists(self)

    def synthetic_symlink(self: Path) -> bool:
        return self == source or original_is_symlink(self)

    monkeypatch.setattr(Path, "exists", no_source_exists)
    monkeypatch.setattr(Path, "is_symlink", synthetic_symlink)
    assert fhir_cli.main([str(source), "--summary-only"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "non-symlink" in captured.err
