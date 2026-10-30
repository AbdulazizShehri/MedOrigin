"""Test read-only wheel METADATA attestation before any public MedOrigin release."""

from __future__ import annotations

import hashlib
import json
import runpy
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
    metadata_dir: str | None = None,
    duplicate_identity: str | None = None,
    omit_identity: str | None = None,
) -> Path:
    message = Message()
    identity = {"Metadata-Version": "2.3", "Name": name, "Version": version}
    for field, value in identity.items():
        if field != omit_identity:
            message[field] = value
        if field == duplicate_identity:
            message[field] = value
    for key, url in (EXPECTED_URLS if urls is None else urls).items():
        message["Project-URL"] = f"{key}, {url}"
    if duplicate:
        message["Project-URL"] = f"Homepage, {EXPECTED_URLS['Homepage']}"
    for extra in extras:
        message["Provides-Extra"] = extra
    for requirement in requires:
        message["Requires-Dist"] = requirement
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"{metadata_dir or f'{name}-{version}.dist-info'}/METADATA",
            message.as_bytes(),
        )
    return path


@pytest.mark.parametrize("field", ["Metadata-Version", "Name", "Version"])
@pytest.mark.parametrize("mutation", ["duplicate", "missing"])
def test_wheel_requires_unambiguous_identity_headers(
    tmp_path: Path, field: str, mutation: str
) -> None:
    wheel = _wheel(
        tmp_path / "synthetic-identity.whl",
        duplicate_identity=field if mutation == "duplicate" else None,
        omit_identity=field if mutation == "missing" else None,
    )
    result = inspect_wheel(wheel, expected_version="0.3.0", require_core_only=True)
    assert result["publication_authorized"] is False
    assert result["status"] == "BLOCKED"
    assert f"wheel {field} must appear exactly once" in result["issues"]


@pytest.mark.parametrize(
    "metadata_dir",
    [
        "nested/medscale-0.3.0.dist-info",
        "unrelated-0.3.0.dist-info",
        "medscale-9.9.9.dist-info",
    ],
)
def test_core_wheel_rejects_unbound_metadata_location(tmp_path: Path, metadata_dir: str) -> None:
    wheel = _wheel(tmp_path / "synthetic-candidate.whl", metadata_dir=metadata_dir)
    result = inspect_wheel(wheel, expected_version="0.3.0", require_core_only=True)
    assert result["status"] == "BLOCKED"
    assert result["publication_authorized"] is False
    assert any("METADATA path" in issue for issue in result["issues"])


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


def test_inspector_streams_digest_without_loading_entire_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = _wheel(tmp_path / "streamed.whl")
    expected_sha256 = hashlib.sha256(wheel.read_bytes()).hexdigest()

    def refuse_whole_file_read(_path: Path) -> bytes:
        raise AssertionError("unbounded Path.read_bytes is prohibited")

    monkeypatch.setattr(Path, "read_bytes", refuse_whole_file_read)
    inspect = runpy.run_path(str(SCRIPT))["inspect_wheel"]
    result = inspect(wheel, expected_version="0.3.0", require_core_only=True)
    assert result["sha256"] == expected_sha256
    assert result["status"] == "METADATA_QUALIFIED_ONLY"
    assert result["publication_authorized"] is False


def test_inspector_rejects_inplace_mutation_between_digest_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = _wheel(tmp_path / "candidate.whl")
    alternate = _wheel(tmp_path / "alternate.whl")
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("synthetic.txt", b"AAAAAAAA")
    with zipfile.ZipFile(alternate, "a") as archive:
        archive.writestr("synthetic.txt", b"BBBBBBBB")
    replacement = alternate.read_bytes()
    assert len(wheel.read_bytes()) == len(replacement)

    original_digest = hashlib.file_digest
    calls = 0

    def mutate_after_first_digest(stream: Any, algorithm: str) -> Any:
        nonlocal calls
        result = original_digest(stream, algorithm)
        calls += 1
        if calls == 1:
            with wheel.open("r+b") as output:
                output.write(replacement)
                output.truncate()
        return result

    monkeypatch.setattr(hashlib, "file_digest", mutate_after_first_digest)
    inspect = runpy.run_path(str(SCRIPT))["inspect_wheel"]
    result = inspect(wheel, expected_version="0.3.0", require_core_only=True)
    assert result["status"] == "BLOCKED"
    assert "wheel changed during inspection" in result["issues"]
    assert result["sha256"] is None
    assert result["publication_authorized"] is False


def test_inspector_unreadable_artifact_fails_closed(tmp_path: Path) -> None:
    inspect = runpy.run_path(str(SCRIPT))["inspect_wheel"]
    result = inspect(tmp_path / "missing.whl", require_core_only=True)
    assert result["status"] == "BLOCKED"
    assert result["publication_authorized"] is False
    assert result["sha256"] is None
    assert "wheel unreadable: FileNotFoundError" in result["issues"]


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


@pytest.mark.parametrize("unexpected_label", ["Security", "Download"])
def test_core_only_rejects_unapproved_project_url(tmp_path: Path, unexpected_label: str) -> None:
    urls = dict(EXPECTED_URLS)
    urls[unexpected_label] = "https://untrusted.invalid/collect"
    wheel = _wheel(tmp_path / "unapproved-url.whl", urls=urls)
    result = inspect_wheel(wheel, expected_version="0.3.0", require_core_only=True)
    assert result["status"] == "BLOCKED"
    assert result["publication_authorized"] is False
    assert "unexpected Project-URL" in result["issues"]


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
