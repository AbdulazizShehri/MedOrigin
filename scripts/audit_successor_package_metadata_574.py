"""Read-only, pinned-root successor public package metadata preflight (#574).

The output is an unsigned engineering *proposal*, NOT a publication credential.
Do not mutate historical MRL-0809 prerequisites or root packaging inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

_FROZEN_PROJECT_SHA256 = "c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510"
_FROZEN_LOCK_SHA256 = "6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4"
_OLD = "https://github.com/TheHalfMoon/MESC"
_NEW = "https://github.com/TheHalfMoon/MedOrigin"
_URLS = {
    "Homepage": "",
    "Repository": "",
    "Documentation": "/tree/main/docs",
    "Issues": "/issues",
}
_MANIFESTS = (
    "specs/mesc-experiment-0/mrl-0809-static-prerequisites-v1.json",
    "specs/mesc-experiment-0/mrl-0809-static-prerequisites-v2.json",
)
_FROZEN_MANIFEST_SHA256 = {
    _MANIFESTS[0]: "7773967611e42c3d74338a1ec7c9004f661843df809865f6c6d455923fea89d1",
    _MANIFESTS[1]: "56de494cf30b6d3dd3aa005e63d55ea7490f7645dd37cbb388188d635813a36d",
}


class AuditError(ValueError):
    """A supposed frozen-root/manifest observation does not match evidence."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def propose_canonical_project_bytes(raw: bytes) -> bytes:
    """Change exactly four TOML URL *lines* in memory; preserve all other bytes."""
    try:
        parsed = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise AuditError("root pyproject.toml cannot be safely parsed") from exc
    urls = parsed.get("project", {}).get("urls", {})
    if not isinstance(urls, dict) or set(urls) != set(_URLS):
        raise AuditError("root [project.urls] has unexpected or missing keys")
    lines = raw.splitlines(keepends=True)
    updated: list[bytes] = []
    changed: set[str] = set()
    for line in lines:
        replacement = line
        for key, suffix in _URLS.items():
            old = f'{key} = "{_OLD}{suffix}"'.encode("ascii")
            new = f'{key} = "{_NEW}{suffix}"'.encode("ascii")
            if urls.get(key) != _OLD + suffix:
                raise AuditError(f"unapproved source URL for {key}")
            if line.rstrip(b"\r\n") == old:
                if key in changed:
                    raise AuditError(f"duplicate source URL line: {key}")
                replacement = new + line[len(old) :]
                changed.add(key)
        updated.append(replacement)
    if changed != set(_URLS):
        raise AuditError(f"unexpected URL line layout; matched {sorted(changed)}")
    candidate = b"".join(updated)
    if candidate == raw:
        raise AuditError("no canonicalization occurred")
    after = tomllib.loads(candidate.decode("utf-8"))
    if after["project"]["urls"] != {key: _NEW + suffix for key, suffix in _URLS.items()}:
        raise AuditError("candidate project metadata failed structural verification")
    return candidate


def audit(root: Path, *, expected_project_sha: str = _FROZEN_PROJECT_SHA256) -> dict[str, Any]:
    """Inspect exact old roots and immutable manifest bindings without any writes."""
    source = (root / "pyproject.toml").read_bytes()
    lock = (root / "uv.lock").read_bytes()
    old_project_sha = _sha(source)
    if old_project_sha != expected_project_sha or _sha(lock) != _FROZEN_LOCK_SHA256:
        raise AuditError("frozen root input SHA-256 mismatch; do not rewrite existing evidence")
    successor = propose_canonical_project_bytes(source)
    manifest_evidence: list[dict[str, str]] = []
    for rel in _MANIFESTS:
        data = (root / rel).read_bytes()
        if _sha(data) != _FROZEN_MANIFEST_SHA256[rel]:
            raise AuditError(f"immutable historical manifest SHA-256 mismatch: {rel}")
        try:
            obj = json.loads(data)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise AuditError(f"invalid static prerequisite manifest: {rel}") from exc
        if not isinstance(obj, dict):
            raise AuditError(f"invalid static prerequisite manifest: {rel}")
        sources = obj.get("sources")
        if not isinstance(sources, list):
            raise AuditError(f"missing sources list: {rel}")
        roots = [x for x in sources if isinstance(x, dict) and x.get("path") == "pyproject.toml"]
        locks = [x for x in sources if isinstance(x, dict) and x.get("path") == "uv.lock"]
        if (
            len(roots) != 1
            or roots[0].get("sha256") != old_project_sha
            or len(locks) != 1
            or locks[0].get("sha256") != _FROZEN_LOCK_SHA256
            or obj.get("dependency_lock_sha256") != _FROZEN_LOCK_SHA256
        ):
            raise AuditError(f"frozen MRL-0809 source bindings mismatch: {rel}")
        manifest_evidence.append(
            {"path": rel, "sha256": _sha(data), "bound_project_sha256": old_project_sha}
        )
    return {
        "status": "proposal_only_no_files_written",
        "release_authorized": False,
        "original_project_sha256": old_project_sha,
        "proposed_successor_project_sha256": _sha(successor),
        "unaltered_lock_sha256": _sha(lock),
        "exact_changed_url_fields": list(_URLS),
        "historical_manifest_evidence": manifest_evidence,
        "next_gate": (
            "separate founder-accepted successor research-root identity "
            "and publication authorization"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = audit(args.root)
    except (AuditError, OSError) as exc:
        parser.exit(2, f"ROOT_IDENTITY_AUDIT_BLOCKED: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
