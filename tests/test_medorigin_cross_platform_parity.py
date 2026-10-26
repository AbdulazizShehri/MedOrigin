"""Unit guardrails for the nonpublishing cross-host artifact comparison."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


def _load():
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


def _record(system: str, *, archive_hash: str = "a"):
    return {
        "schema": "MEDORIGIN_CORE_PARITY_REVIEW_V1",
        "source_git_commit": "f27faada48311fa09e712842e11f4f9fe1e412ac",
        "platform": system,
        "build_backend": "hatchling==1.32.4",
        "publication_authorized": False,
        "adr_0045_accepted": False,
        "source_bound_verified": True,
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


def test_same_contents_different_archive_headers_do_not_authorize_publication():
    subject = _load()
    result = subject.compare(_record("windows"), _record("linux", archive_hash="b"))
    assert result["status"] == "CONTENT_PARITY_VERIFIED_ARCHIVE_HEADERS_DIFFER"
    assert result["publication_authorized"] is False
    assert result["independent_security_review_completed"] is False
    assert all(item["members_byte_identical"] for item in result["archives"].values())
    assert not any(item["whole_archive_byte_identical"] for item in result["archives"].values())


def test_identical_archive_payloads_and_headers_report_exact_parity():
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
    ],
)
def test_cross_host_audit_fails_closed(tamper: str):
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
    with pytest.raises(subject.ParityError):
        subject.compare(left, right)
