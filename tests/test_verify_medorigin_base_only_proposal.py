"""Adversarial tests for the separate UNAPPROVED ADR-0045 source verifier."""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
import io
import json
import os
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_medorigin_base_only_proposal.py"


@pytest.fixture
def gate() -> Any:
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location("medorigin_proposal_verifier", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT.parent))


@pytest.mark.parametrize(
    "name",
    [
        "",
        "/absolute",
        "../traversal",
        "medscale/../evil",
        "two//slashes",
        "medscale\\evil",
        "medscale/./another",
    ],
)
def test_unsafe_member_names_refused(gate: Any, name: str) -> None:
    with pytest.raises(gate.ProposalVerificationError):
        gate.safe_name(name)


def test_positive_frozen_optional_root_has_exact_change(gate: Any) -> None:
    original = gate.git(ROOT, "show", "HEAD:pyproject.toml")
    before, after = gate.exact_removed_projected_root(original)
    assert b"[project.optional-dependencies]" in before
    assert b"[project.optional-dependencies]" not in after
    assert hashlib.sha256(after).hexdigest() != hashlib.sha256(before).hexdigest()


def test_mutated_frozen_extra_block_is_blocked(gate: Any) -> None:
    original = gate.git(ROOT, "show", "HEAD:pyproject.toml")
    assert b"pillow==12.3.0" in original
    with pytest.raises((gate.ProposalVerificationError, ValueError)):
        gate.exact_removed_projected_root(original.replace(b"pillow==12.3.0", b"pillow==13.0.0"))


def test_provenance_template_never_grants_release(gate: Any) -> None:
    revision, sources, original, *_ = gate.trusted_source(ROOT)
    base, changed = gate.exact_removed_projected_root(original)
    manifest = json.loads(gate.expected_receipt(revision, sources, base, changed))
    assert manifest["source_git_commit"] == revision
    assert manifest["source_file_count"] == 254
    assert manifest["publication_authorized"] is False
    assert manifest["adr_0044_amendment_accepted"] is False
    assert manifest["independent_security_review_completed"] is False
    assert manifest["staged_vcs_ignore_sha256"] == hashlib.sha256(b"").hexdigest()


def test_in_memory_wheel_record_self_rehash_not_a_trust_anchor(gate: Any) -> None:
    data = b"from medscale import unsafe"
    wanted = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    rows = [
        ["medscale/__init__.py", "sha256=" + wanted, str(len(data))],
        ["medscale-0.3.0.dist-info/RECORD", "", ""],
    ]
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    wheels = {
        "medscale/__init__.py": data,
        "medscale-0.3.0.dist-info/RECORD": buffer.getvalue().encode(),
    }
    gate.check_record(wheels)  # only proves *internal* consistency
    # The actual verifier separately compares every source member to Git bytes.
    assert gate.trusted_source(ROOT)[1]["src/medscale/__init__.py"] != data
    wheels["medscale/__init__.py"] += b"\n# changed after record"
    with pytest.raises(gate.ProposalVerificationError):
        gate.check_record(wheels)


def test_duplicate_zip_and_hidden_zip_prefix_refused(gate: Any, tmp_path: Path) -> None:
    wheel = tmp_path / "changed.whl"
    with zipfile.ZipFile(wheel, "w") as z:
        z.writestr("medscale/a.py", "pass\n", compress_type=zipfile.ZIP_DEFLATED)
        with pytest.warns(UserWarning, match="Duplicate name"):
            z.writestr("medscale/a.py", "other\n", compress_type=zipfile.ZIP_DEFLATED)
    with pytest.raises(gate.ProposalVerificationError):
        gate.load_wheel(wheel)
    with zipfile.ZipFile(wheel, "w") as z:
        z.writestr("medscale/a.py", "pass\n", compress_type=zipfile.ZIP_DEFLATED)
    wheel.write_bytes(b"hidden-preface" + wheel.read_bytes())
    with pytest.raises(gate.ProposalVerificationError):
        gate.load_wheel(wheel)


@pytest.mark.parametrize("kind", ["symlink", "duplicate", "traversal"])
def test_unsafe_tar_member_refused(gate: Any, tmp_path: Path, kind: str) -> None:
    path = tmp_path / "bad.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        member = tarfile.TarInfo("medscale-0.3.0/a.py")
        if kind == "symlink":
            member.type = tarfile.SYMTYPE
            member.linkname = "../../outside"
            tar.addfile(member)
        else:
            member.size = 1
            tar.addfile(member, io.BytesIO(b"a"))
            member2 = tarfile.TarInfo(
                "medscale-0.3.0/a.py" if kind == "duplicate" else "../outside"
            )
            member2.size = 1
            tar.addfile(member2, io.BytesIO(b"x"))
    with pytest.raises(gate.ProposalVerificationError):
        gate.load_sdist(path)


def test_real_dist_when_supplied_remains_unpublished(gate: Any) -> None:
    target = os.environ.get("MEDORIGIN_PROPOSAL_TEST_DIST")
    if not target:
        pytest.skip("Only run real-artifact fixture when exact-head build is supplied")
    result = gate.verify(ROOT, Path(target))
    assert result["status"] == "BASE_ONLY_PROPOSAL_SOURCE_BOUND_VERIFIED"
    assert result["publication_authorized"] is False
    assert result["independent_review_complete"] is False


def test_cli_uses_explicit_receipt_without_logging_full_verifier_data(
    gate: Any, monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    marker = "PRIVATE-SENTINEL-VERIFIER"
    evidence = {
        "status": "BASE_ONLY_PROPOSAL_SOURCE_BOUND_VERIFIED",
        "publication_authorized": False,
        "unexpected_detail": marker,
    }
    monkeypatch.setattr(gate, "verify", lambda *_args: evidence)
    receipt = tmp_path / "verified-receipt.json"
    argv = ["--dist", str(tmp_path), "--out", str(receipt)]
    assert gate.main(argv) == 0
    output = capsys.readouterr().out
    assert marker not in output
    assert json.loads(output)["status"] == "BASE_ONLY_PROPOSAL_SOURCE_BOUND_VERIFIED"
    assert json.loads(receipt.read_text(encoding="utf-8")) == evidence
    assert gate.main(argv) == 2
    assert json.loads(receipt.read_text(encoding="utf-8")) == evidence
