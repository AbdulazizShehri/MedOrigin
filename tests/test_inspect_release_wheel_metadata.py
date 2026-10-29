"""Test read-only wheel METADATA attestation before any public MedOrigin release."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from email.message import Message
from pathlib import Path
from typing import Any, cast

import pytest

HOME = "https://github.com/AbdulazizShehri/MedOrigin"
EXPECTED_URLS = {
    "Homepage": HOME,
    "Repository": HOME,
    "Documentation": HOME + "/tree/main/docs",
    "Issues": HOME + "/issues",
}
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inspect_release_wheel_metadata.py"


def inspect_wheel(
    wheel: Path,
    *,
    expected_version: str | None = None,
    distribution: str = "medscale",
    require_core_only: bool = False,
) -> dict[str, Any]:
    """Exercise the operator CLI instead of importing scripts under an alias."""
    command = [
        sys.executable,
        str(SCRIPT),
        "--wheel",
        str(wheel),
        "--distribution",
        distribution,
    ]
    if expected_version is not None:
        command.extend(["--expected-version", expected_version])
    if require_core_only:
        command.append("--require-core-only")
    completed = subprocess.run(command, check=False, text=True, capture_output=True)
    assert completed.returncode in (0, 2), completed.stderr
    data = json.loads(completed.stdout)
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def _wheel(
    path: Path,
    *,
    urls: dict[str, str] | None = None,
    name: str = "medscale",
    version: str = "0.3.0",
    duplicate: bool = False,
    extras: tuple[str, ...] = (),
    requires: tuple[str, ...] = (),
) -> Path:
    message = Message()
    message["Metadata-Version"] = "2.3"
    message["Name"] = name
    message["Version"] = version
    for key, url in (EXPECTED_URLS if urls is None else urls).items():
        message["Project-URL"] = f"{key}, {url}"
    if duplicate:
        message["Project-URL"] = f"Homepage, {EXPECTED_URLS['Homepage']}"
    for extra in extras:
        message["Provides-Extra"] = extra
    for requirement in requires:
        message["Requires-Dist"] = requirement
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{name}-{version}.dist-info/METADATA", message.as_bytes())
    return path


@pytest.mark.parametrize(
    ("extras", "requires", "should_block"),
    [
        ((), (), False),
        (("training-hf-sft",), (), True),
        ((), ("pillow==12.3.0; extra == 'rq1-runtime-feasibility'",), True),
        (
            ("rq1-runtime-feasibility",),
            ("accelerate==1.14.0; extra == 'rq1-runtime-feasibility'",),
            True,
        ),
    ],
)
def test_strict_core_only_wheel_policy_is_fail_closed(
    tmp_path: Path,
    extras: tuple[str, ...],
    requires: tuple[str, ...],
    should_block: bool,
) -> None:
    wheel = _wheel(tmp_path / "synthetic-core-candidate.whl", extras=extras, requires=requires)
    result = inspect_wheel(wheel, expected_version="0.3.0", require_core_only=True)
    assert result["publication_authorized"] is False
    if should_block:
        assert result["status"] == "BLOCKED"
        assert any("core-only" in issue for issue in result["issues"])
    else:
        assert result["status"] == "METADATA_QUALIFIED_ONLY"
        assert result["issues"] == []


def test_valid_metadata_is_not_publication_authorization(tmp_path: Path) -> None:
    result = inspect_wheel(_wheel(tmp_path / "valid.whl"), expected_version="0.3.0")
    assert result["status"] == "METADATA_QUALIFIED_ONLY"
    assert result["publication_authorized"] is False
    assert not result["issues"]
    assert len(str(result["sha256"])) == 64


@pytest.mark.parametrize("label", sorted(EXPECTED_URLS))
def test_historical_owner_is_not_accepted(tmp_path: Path, label: str) -> None:
    urls = dict(EXPECTED_URLS)
    urls[label] = urls[label].replace("AbdulazizShehri", "TheHalfMoon")
    result = inspect_wheel(_wheel(tmp_path / "historic.whl", urls=urls))
    assert result["status"] == "BLOCKED"
    assert any(item.startswith(label + ":") for item in result["issues"])


@pytest.mark.parametrize("label", sorted(EXPECTED_URLS))
def test_missing_url_is_rejected(tmp_path: Path, label: str) -> None:
    urls = dict(EXPECTED_URLS)
    del urls[label]
    result = inspect_wheel(_wheel(tmp_path / "missing.whl", urls=urls))
    assert any(item.startswith(label + ":") for item in result["issues"])


def test_duplicate_label_is_rejected(tmp_path: Path) -> None:
    result = inspect_wheel(_wheel(tmp_path / "duplicate.whl", duplicate=True))
    assert "invalid or duplicate Project-URL" in result["issues"]


def test_version_and_distribution_are_binding(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "mismatch.whl", version="0.2.0", name="medorigin")
    result = inspect_wheel(wheel, expected_version="0.3.0")
    assert "distribution name must remain medscale" in result["issues"]
    assert "wheel version disagrees with expected candidate" in result["issues"]


def test_bad_and_ambiguous_wheel_are_rejected(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.whl"
    invalid.write_bytes(b"not a zip wheel")
    assert inspect_wheel(invalid)["status"] == "BLOCKED"
    duplicated = tmp_path / "multiple.whl"
    with zipfile.ZipFile(duplicated, "w") as archive:
        archive.writestr("medscale-0.3.0.dist-info/METADATA", b"Name: medscale")
        archive.writestr("fake-0.3.0.dist-info/METADATA", b"Name: fake")
    assert inspect_wheel(duplicated)["status"] == "BLOCKED"


def test_cli_output_keeps_publication_disabled(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "candidate.whl")
    report = tmp_path / "report.json"
    script = Path(__file__).resolve().parents[1] / "scripts" / "inspect_release_wheel_metadata.py"
    process = subprocess.run(
        [
            sys.executable,
            str(script),
            "--wheel",
            str(wheel),
            "--expected-version",
            "0.3.0",
            "--json-out",
            str(report),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert process.returncode == 0
    value = json.loads(report.read_text(encoding="utf8"))
    assert value["publication_authorized"] is False
    assert value["status"] == "METADATA_QUALIFIED_ONLY"


def test_cli_exits_nonzero_for_historical_owner(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / "old.whl",
        urls={
            key: val.replace("AbdulazizShehri", "TheHalfMoon") for key, val in EXPECTED_URLS.items()
        },
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "inspect_release_wheel_metadata.py"
    process = subprocess.run(
        [sys.executable, str(script), "--wheel", str(wheel)],
        check=False,
        text=True,
        capture_output=True,
    )
    assert process.returncode == 2
    assert json.loads(process.stdout)["status"] == "BLOCKED"


def test_workspace_distribution_must_be_canonical(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "workspace.whl", name="medscale-workspace", version="0.1.0.dev1")
    result = inspect_wheel(
        wheel,
        expected_version="0.1.0.dev1",
        distribution="medscale-workspace",
    )
    assert result["status"] == "METADATA_QUALIFIED_ONLY"
    assert result["publication_authorized"] is False


def test_workspace_refuses_core_distribution_name(tmp_path: Path) -> None:
    core = _wheel(tmp_path / "core.whl")
    result = inspect_wheel(core, distribution="medscale-workspace")
    assert "distribution name must remain medscale-workspace" in result["issues"]
