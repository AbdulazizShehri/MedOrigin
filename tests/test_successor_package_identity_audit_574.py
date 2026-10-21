"""No-write successor-root planning regression for Issue #574."""

from __future__ import annotations

import hashlib
import json
from importlib import import_module
from pathlib import Path

import pytest

audit = import_module("scripts.audit_successor_package_metadata_574")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _project() -> bytes:
    return (
        b'[project]\nname = "medscale"\n'
        b"[project.urls]\n"
        b'Homepage = "https://github.com/TheHalfMoon/MESC"\n'
        b'Repository = "https://github.com/TheHalfMoon/MESC"\n'
        b'Documentation = "https://github.com/TheHalfMoon/MESC/tree/main/docs"\n'
        b'Issues = "https://github.com/TheHalfMoon/MESC/issues"\n'
    )


def _root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    old = _project()
    lock = b"[[package]]\nname = 'safe-fixture'\n"
    monkeypatch.setattr(audit, "_FROZEN_LOCK_SHA256", _sha(lock))
    (tmp_path / "pyproject.toml").write_bytes(old)
    (tmp_path / "uv.lock").write_bytes(lock)
    for rel in audit._MANIFESTS:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "dependency_lock_sha256": _sha(lock),
                    "sources": [
                        {"path": "pyproject.toml", "sha256": _sha(old)},
                        {"path": "uv.lock", "sha256": _sha(lock)},
                    ],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    monkeypatch.setattr(
        audit,
        "_FROZEN_MANIFEST_SHA256",
        {rel: _sha((tmp_path / rel).read_bytes()) for rel in audit._MANIFESTS},
    )
    return tmp_path


def _all_files(root: Path) -> dict[str, bytes]:
    return {str(x.relative_to(root)): x.read_bytes() for x in root.rglob("*") if x.is_file()}


def test_audit_proposes_exact_four_urls_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path, monkeypatch)
    before = _all_files(root)
    report = audit.audit(root, expected_project_sha=_sha(_project()))
    assert report["release_authorized"] is False
    assert report["status"] == "proposal_only_no_files_written"
    assert report["original_project_sha256"] == _sha(_project())
    assert report["proposed_successor_project_sha256"] == _sha(
        audit.propose_canonical_project_bytes(_project())
    )
    assert len(report["historical_manifest_evidence"]) == 2
    assert _all_files(root) == before
    proposal = audit.propose_canonical_project_bytes(_project())
    assert proposal.count(b"TheHalfMoon/MedOrigin") == 4
    assert b"TheHalfMoon/MESC" not in proposal
    assert proposal.replace(b"TheHalfMoon/MedOrigin", b"TheHalfMoon/MESC") == _project()


@pytest.mark.parametrize(
    "mutator",
    [
        lambda raw: raw.replace(b"/MESC", b"/other", 1),
        lambda raw: raw.replace(b'Issues = "https://github.com/TheHalfMoon/MESC/issues"\n', b""),
        lambda raw: raw.replace(b'Homepage = "https://github.com/TheHalfMoon/MESC"\n', b""),
    ],
)
def test_unexpected_source_identity_fails_closed(mutator: object) -> None:
    with pytest.raises(audit.AuditError):
        audit.propose_canonical_project_bytes(mutator(_project()))  # type: ignore[operator]


def test_audit_rejects_tampered_historical_manifest_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path, monkeypatch)
    path = root / audit._MANIFESTS[0]
    src = json.loads(path.read_text(encoding="utf-8"))
    src["sources"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(src), encoding="utf-8")
    before = _all_files(root)
    with pytest.raises(audit.AuditError, match="historical manifest SHA-256 mismatch"):
        audit.audit(root, expected_project_sha=_sha(_project()))
    assert _all_files(root) == before


@pytest.mark.parametrize("content", [b"null", b"[]", b"42", b'"wrong"'])
def test_non_object_manifest_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: bytes
) -> None:
    root = _root(tmp_path, monkeypatch)
    path = root / audit._MANIFESTS[0]
    path.write_bytes(content)
    monkeypatch.setitem(audit._FROZEN_MANIFEST_SHA256, audit._MANIFESTS[0], _sha(content))
    before = _all_files(root)
    with pytest.raises(audit.AuditError, match="invalid static prerequisite manifest"):
        audit.audit(root, expected_project_sha=_sha(_project()))
    assert _all_files(root) == before


def test_audit_rejects_modified_root_and_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path, monkeypatch)
    project = root / "pyproject.toml"
    original = project.read_bytes()
    project.write_bytes(original + b"\n# drift\n")
    with pytest.raises(audit.AuditError, match="frozen root"):
        audit.audit(root, expected_project_sha=_sha(original))
    project.write_bytes(original)
    lock = root / "uv.lock"
    lock.write_bytes(lock.read_bytes() + b"X")
    with pytest.raises(audit.AuditError, match="frozen root"):
        audit.audit(root, expected_project_sha=_sha(original))


def test_unbound_manifest_content_mutation_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root(tmp_path, monkeypatch)
    path = root / audit._MANIFESTS[1]
    original = json.loads(path.read_text(encoding="utf-8"))
    original["unexpected_nonbinding_field"] = "unauthorized drift"
    path.write_text(json.dumps(original, sort_keys=True), encoding="utf-8")
    before = _all_files(root)
    with pytest.raises(audit.AuditError, match="historical manifest SHA-256 mismatch"):
        audit.audit(root, expected_project_sha=_sha(_project()))
    assert _all_files(root) == before
