"""Unit guardrails for the nonpublishing cross-host artifact comparison."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any

import pytest


def _load() -> Any:
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "qualify_medorigin_cross_platform_parity.py"
    )
    spec = importlib.util.spec_from_file_location("medorigin_cross_platform", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record(system: str, *, archive_hash: str = "a") -> dict[str, Any]:
    return {
        "schema": "MEDORIGIN_CORE_PARITY_REVIEW_V1",
        "source_git_commit": "f27faada48311fa09e712842e11f4f9fe1e412ac",
        "platform": system,
        "build_backend": "hatchling==1.32.4",
        "publication_authorized": False,
        "adr_0045_accepted": False,
        "source_bound_verified": True,
        "installed_python_versions": ["3.11", "3.12"],
        "installed_python_source_count": 249,
        "synthetic_report_sha256": (
            "991d319d9c567db3a71985661a12abb67c8432ff43b439c08759f8ee1d52fbd9"
        ),
        "archives": {
            name: {
                "archive_sha256": archive_hash * 64,
                "member_count": size,
                "members": {f"member_{i:04d}": f"{i:064x}" for i in range(size)},
                **(
                    {"zip_creator_systems": [0 if system == "windows" else 3]}
                    if name == "wheel"
                    else {}
                ),
            }
            for name, size in (("wheel", 255), ("sdist", 258))
        },
    }


def test_same_contents_different_archive_headers_do_not_authorize_publication() -> None:
    subject = _load()
    result = subject.compare(_record("windows"), _record("linux", archive_hash="b"))
    assert result["status"] == "CONTENT_PARITY_VERIFIED_ARCHIVE_HEADERS_DIFFER"
    assert result["publication_authorized"] is False
    assert result["independent_security_review_completed"] is False
    assert all(item["members_byte_identical"] for item in result["archives"].values())
    assert not any(item["whole_archive_byte_identical"] for item in result["archives"].values())


def test_identical_archive_payloads_and_headers_report_exact_parity() -> None:
    subject = _load()
    result = subject.compare(_record("windows"), _record("linux"))
    assert result["status"] == "CONTENT_AND_ARCHIVE_PARITY_VERIFIED"
    assert all(item["whole_archive_byte_identical"] for item in result["archives"].values())


@pytest.mark.parametrize(
    "tamper",
    [
        "member_byte",
        "extra_member",
        "revised_git_commit",
        "auth_true",
        "adr_accepted",
        "not_source_verified",
        "wrong_backend",
        "wrong_member_count",
        "malformed_digest",
        "same_platform",
        "missing_runtime_evidence",
        "wrong_runtime_count",
        "wrong_report_digest",
    ],
)
def test_cross_host_audit_fails_closed(tamper: str) -> None:
    subject = _load()
    left, right = _record("windows"), _record("linux")
    right = copy.deepcopy(right)
    if tamper == "member_byte":
        right["archives"]["wheel"]["members"]["member_0001"] = "f" * 64
    elif tamper == "extra_member":
        right["archives"]["sdist"]["members"]["unexpected"] = "a" * 64
    elif tamper == "revised_git_commit":
        right["source_git_commit"] = "a" * 40
    elif tamper == "auth_true":
        right["publication_authorized"] = True
    elif tamper == "adr_accepted":
        right["adr_0045_accepted"] = True
    elif tamper == "not_source_verified":
        right["source_bound_verified"] = False
    elif tamper == "wrong_backend":
        right["build_backend"] = "hatchling==0"
    elif tamper == "wrong_member_count":
        right["archives"]["wheel"]["member_count"] = 254
    elif tamper == "malformed_digest":
        right["archives"]["sdist"]["archive_sha256"] = "zzz"
    elif tamper == "same_platform":
        right["platform"] = "windows"
    elif tamper == "missing_runtime_evidence":
        del right["installed_python_versions"]
    elif tamper == "wrong_runtime_count":
        right["installed_python_source_count"] = 248
        left["installed_python_source_count"] = 249
    elif tamper == "wrong_report_digest":
        right["synthetic_report_sha256"] = "a" * 64
    with pytest.raises(subject.ParityError):
        subject.compare(left, right)


def test_macos_and_linux_whole_archives_identical_if_bytes_agree() -> None:
    subject = _load()
    result = subject.compare(_record("darwin"), _record("linux"))
    assert result["status"] == "CONTENT_AND_ARCHIVE_PARITY_VERIFIED"
    assert result["publication_authorized"] is False


def test_windows_and_macos_wheel_headers_may_differ_without_member_changes() -> None:
    subject = _load()
    windows, macos = _record("windows"), _record("darwin")
    macos["archives"]["wheel"]["archive_sha256"] = "b" * 64
    result = subject.compare(windows, macos)
    assert result["archives"]["sdist"]["whole_archive_byte_identical"] is True
    assert result["archives"]["wheel"]["members_byte_identical"] is True
    assert result["archives"]["wheel"]["whole_archive_byte_identical"] is False
    assert result["status"] == "CONTENT_PARITY_VERIFIED_ARCHIVE_HEADERS_DIFFER"


def test_runtime_evidence_is_attested_in_pairwise_result() -> None:
    subject = _load()
    record = subject.compare(_record("darwin"), _record("linux"))
    assert record["offline_installed_python_versions"] == ["3.11", "3.12"]
    assert record["offline_installed_source_count"] == 249
    assert record["synthetic_report_sha256"] == subject.SYNTHETIC_REPORT_SHA256
    assert record["publication_authorized"] is False


def test_synthetic_evidence_rejects_tampered_reports(tmp_path: Path) -> None:
    import json

    subject = _load()
    report = tmp_path / "evidence.json"
    baseline = {
        "runs": [
            {
                "report_sha256": subject.SYNTHETIC_REPORT_SHA256,
                "structural_status": "valid",
                "malformed_exit": 1,
            }
        ]
        * 2
    }
    report.write_text(json.dumps(baseline), encoding="utf-8")
    subject._verify_synthetic_evidence(report)
    for tampered in (
        {"runs": baseline["runs"][:1]},
        {"runs": [baseline["runs"][0], dict(baseline["runs"][0], report_sha256="f" * 64)]},
        {"runs": [baseline["runs"][0], dict(baseline["runs"][0], malformed_exit=0)]},
        {"runs": [baseline["runs"][0], dict(baseline["runs"][0], structural_status="invalid")]},
        {"runs": [baseline["runs"][0], dict(baseline["runs"][0], malformed_exit=True)]},
    ):
        report.write_text(json.dumps(tampered), encoding="utf-8")
        with pytest.raises(subject.ParityError):
            subject._verify_synthetic_evidence(report)


def test_offline_command_fails_closed_when_command_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import subprocess

    subject = _load()
    seen: list[dict[str, object]] = []

    def fake(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        seen.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(args, returncode=2, stdout=b"", stderr=b"secret")

    monkeypatch.setattr(subject.subprocess, "run", fake)
    with pytest.raises(subject.ParityError) as info:
        subject._offline_command(["uv", "pip", "install", "--no-index"], tmp_path)
    assert "secret" not in str(info.value)
    assert seen[0]["env"]["UV_OFFLINE"] == "1"
    assert seen[0]["env"]["UV_NO_PROGRESS"] == "1"
