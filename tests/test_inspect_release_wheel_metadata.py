"""Test read-only wheel METADATA attestation before any public MedOrigin release."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
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
    expected_sha256: str | None = None,
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
    if expected_sha256 is not None:
        command.extend(["--expected-sha256", expected_sha256])
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
    requirements: tuple[str, ...] = (),
    extras: tuple[str, ...] = (),
) -> Path:
    message = Message()
    message["Metadata-Version"] = "2.3"
    message["Name"] = name
    message["Version"] = version
    for key, url in (EXPECTED_URLS if urls is None else urls).items():
        message["Project-URL"] = f"{key}, {url}"
    if duplicate:
        message["Project-URL"] = f"Homepage, {EXPECTED_URLS['Homepage']}"
    for requirement in requirements:
        message["Requires-Dist"] = requirement
    for extra in extras:
        message["Provides-Extra"] = extra
    root = f"{name.replace('-', '_')}-{version}.dist-info/"
    payloads = {
        root + "METADATA": message.as_bytes(),
        root + "WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        name.replace("-", "_") + "/__init__.py": b"\n",
    }
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for member, contents in payloads.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).rstrip(b"=").decode()
        writer.writerow((member, "sha256=" + digest, len(contents)))
    writer.writerow((root + "RECORD", "", ""))
    with zipfile.ZipFile(path, "w") as archive:
        for member, contents in payloads.items():
            archive.writestr(member, contents)
        archive.writestr(root + "RECORD", record.getvalue())
    return path


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


@pytest.mark.parametrize(
    ("requirements", "extras"),
    [
        (("pillow==12.3.0; extra == 'rq1-runtime-feasibility'",), ("rq1-runtime-feasibility",)),
        (("certifi==2026.6.1",), ()),
        ((), ("training-hf-sft",)),
    ],
)
def test_core_only_gate_rejects_advertised_dependency_or_extra(
    tmp_path: Path, requirements: tuple[str, ...], extras: tuple[str, ...]
) -> None:
    wheel = _wheel(tmp_path / "research-extras.whl", requirements=requirements, extras=extras)
    checked = inspect_wheel(wheel, require_core_only=True)
    assert checked["status"] == "BLOCKED"
    assert checked["core_only_verified"] is False
    assert "core-only wheel advertises dependencies or extras" in checked["issues"]
    assert checked["publication_authorized"] is False
    legacy = inspect_wheel(wheel)
    assert legacy["core_only_verified"] is False
    assert legacy["publication_authorized"] is False


def test_core_only_gate_accepts_dependency_free_metadata_but_never_release(
    tmp_path: Path,
) -> None:
    wheel = _wheel(tmp_path / "isolated-core.whl")
    result = inspect_wheel(wheel, require_core_only=True, expected_version="0.3.0")
    assert result["status"] == "METADATA_QUALIFIED_ONLY"
    assert result["core_only_verified"] is True
    assert result["publication_authorized"] is False
    assert not result["issues"]


def test_malformed_wheel_is_never_core_only_verified(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.whl"
    path.write_bytes(b"not-a-wheel")
    result = inspect_wheel(path, require_core_only=True)
    assert result["status"] == "BLOCKED"
    assert result["core_only_verified"] is False
    assert result["publication_authorized"] is False


def test_in_place_archive_mutation_during_inspection_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No report may bind a pre-read SHA to different post-read Wheel bytes."""
    from runpy import run_path

    wheel = _wheel(tmp_path / "mutable.whl")
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    inspector = run_path(str(SCRIPT))["inspect_wheel"]
    original = zipfile.ZipFile

    def mutate_after_digest(source: Any) -> zipfile.ZipFile:
        # A ZIP permits trailing bytes, so metadata can still be parsed.
        with wheel.open("ab") as dest:
            dest.write(b"changed-after-first-hash")
        return original(source)

    monkeypatch.setattr(zipfile, "ZipFile", mutate_after_digest)
    result = inspector(wheel, require_core_only=True)
    assert result["status"] == "BLOCKED"
    assert result["core_only_verified"] is False
    assert "wheel bytes changed during inspection" in result["issues"]
    assert result["publication_authorized"] is False


@pytest.mark.parametrize(
    ("member", "reason"),
    [
        ("../escape.py", "unsafe member path"),
        ("medscale/../escape.py", "unsafe member path"),
        ("MEDSCALE/__init__.py", "duplicate or case-colliding members"),
    ],
)
def test_core_only_rejects_unsafe_or_case_colliding_zip_entries(
    tmp_path: Path, member: str, reason: str
) -> None:
    wheel = _wheel(tmp_path / "unsafe.whl")
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr(member, b"synthetic")
    result = inspect_wheel(wheel, require_core_only=True)
    assert result["status"] == "BLOCKED"
    assert result["core_only_verified"] is False
    assert any(reason in issue for issue in result["issues"])


def test_core_only_rejects_unix_symlink_member(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "symlink.whl")
    entry = zipfile.ZipInfo("medscale/link")
    entry.create_system = 3
    entry.external_attr = 0o120777 << 16
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr(entry, b"../other")
    result = inspect_wheel(wheel, require_core_only=True)
    assert "core wheel contains symbolic link" in result["issues"]
    assert result["core_only_verified"] is False


def test_core_only_detects_payload_with_stale_record_hash(tmp_path: Path) -> None:
    original = _wheel(tmp_path / "original.whl")
    with zipfile.ZipFile(original) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    contents["medscale/__init__.py"] = b"X"
    tampered = tmp_path / "tampered.whl"
    with zipfile.ZipFile(tampered, "w") as archive:
        for name, payload in contents.items():
            archive.writestr(name, payload)
    result = inspect_wheel(tampered, require_core_only=True)
    assert "core wheel RECORD digest mismatch" in result["issues"]
    assert result["core_only_verified"] is False
    assert result["publication_authorized"] is False


def test_core_only_rejects_metadata_directory_spoof(tmp_path: Path) -> None:
    original = _wheel(tmp_path / "original.whl")
    with zipfile.ZipFile(original) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    metadata = contents.pop("medscale-0.3.0.dist-info/METADATA")
    contents["other-0.3.0.dist-info/METADATA"] = metadata
    tampered = tmp_path / "spoof.whl"
    with zipfile.ZipFile(tampered, "w") as archive:
        for name, payload in contents.items():
            archive.writestr(name, payload)
    result = inspect_wheel(tampered, require_core_only=True)
    assert "core wheel METADATA path disagrees with distribution/version" in result["issues"]
    assert result["core_only_verified"] is False


@pytest.mark.parametrize(
    "member",
    [
        "medscale/_native.pyd",
        "medscale/embedded.so",
        "medscale/startup.pth",
        "medscale/setup.ps1",
        "medscale-0.3.0.data/scripts/launch",
    ],
)
def test_core_wheel_rejects_unexpected_native_or_install_payload(
    tmp_path: Path, member: str
) -> None:
    wheel = _wheel(tmp_path / "native.whl")
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr(member, b"synthetic-untrusted-payload")
    result = inspect_wheel(wheel, require_core_only=True)
    assert "core wheel contains native executable or installer payload" in result["issues"]
    assert result["core_only_verified"] is False
    assert result["publication_authorized"] is False


def test_expected_digest_binds_core_wheel_to_operator_supplied_reference(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "candidate.whl")
    reference_digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    verified = inspect_wheel(
        wheel,
        expected_version="0.3.0",
        require_core_only=True,
        expected_sha256=reference_digest,
    )
    assert verified["status"] == "METADATA_QUALIFIED_ONLY"
    assert verified["core_only_verified"] is True
    assert verified["expected_digest_matched"] is True
    assert verified["publication_authorized"] is False
    bad = inspect_wheel(wheel, require_core_only=True, expected_sha256="0" * 64)
    assert bad["status"] == "BLOCKED"
    assert bad["core_only_verified"] is False
    assert bad["expected_digest_matched"] is False
    assert "Wheel SHA-256 disagrees with operator expected digest" in bad["issues"]


@pytest.mark.parametrize(
    "invalid",
    ["", "F" * 64, "g" * 64, "a" * 63, "a" * 65, " a" * 32, "sha256:" + "a" * 64],
)
def test_expected_digest_rejects_malformed_or_noncanonical_reference(
    tmp_path: Path, invalid: str
) -> None:
    wheel = _wheel(tmp_path / "candidate.whl")
    result = inspect_wheel(wheel, require_core_only=True, expected_sha256=invalid)
    assert result["status"] == "BLOCKED"
    assert result["expected_digest_matched"] is False
    assert result["publication_authorized"] is False
    assert "expected Wheel SHA-256 must be 64 lowercase hexadecimal characters" in result["issues"]


def test_digest_reference_match_never_overrides_invalid_wheel(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "candidate.whl", requirements=("pillow==12.3.0",))
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    result = inspect_wheel(wheel, require_core_only=True, expected_sha256=digest)
    assert result["status"] == "BLOCKED"
    assert result["core_only_verified"] is False
    assert result["expected_digest_matched"] is False
    assert result["publication_authorized"] is False


def test_legacy_inspection_never_claims_external_digest_binding(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "candidate.whl")
    result = inspect_wheel(wheel)
    assert result["expected_digest_matched"] is False
    assert result["publication_authorized"] is False
