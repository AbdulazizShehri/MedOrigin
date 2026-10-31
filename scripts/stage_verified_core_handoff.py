"""Stage exact inspected synthetic Core Wheel/sdist bytes; never publish.

This source-only, no-upload handoff is NOT a release authorization or an
independent Git source-attestation verifier. The real release workflow retains
every owner, advisory, review and tag gate. This script only constrains the
bytes supplied to a later artifact uploader inside the same isolated job.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import check_base_core_publication_scope as scope


class HandoffError(RuntimeError):
    """Do not stage or upload if receipt/source/publisher bytes differ."""


def _qualified_pair(dist: Path) -> dict[str, list[Path]]:
    """Only pass exactly two normal medscale archive names to pinned readers."""
    try:
        with os.scandir(dist) as listing:
            entries = list(listing)
    except OSError as exc:
        raise HandoffError("source distribution directory unavailable") from exc
    if len(entries) != 2 or any(not e.is_file(follow_symlinks=False) for e in entries):
        raise HandoffError("source distribution directory is not an exact regular pair")
    wheel = [
        dist / e.name for e in entries if e.name.startswith("medscale-") and e.name.endswith(".whl")
    ]
    sdist = [
        dist / e.name
        for e in entries
        if e.name.startswith("medscale-") and e.name.endswith(".tar.gz")
    ]
    if len(wheel) != 1 or len(sdist) != 1:
        raise HandoffError("source distribution directory has no exact Wheel/sdist pair")
    return {"wheel": wheel, "sdist": sdist}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage(dist: Path, target: Path) -> dict[str, object]:
    """Build a fresh private pair and require exact SHA parity with initial scope.

    All copying is from Windows HANDLE-/POSIX dirfd-backed private snapshots.
    The directory identity is checked on context exit *before* stage exposure.
    Caller must upload target/*, never reopen the original dist/* names.
    """
    source_dir, target_dir = dist.absolute(), target.absolute()
    parent = target_dir.parent
    if (
        target_dir.exists()
        or target_dir.is_symlink()
        or not parent.is_dir()
        or scope._has_untrusted_ancestor_alias(parent)
    ):
        raise HandoffError("destination must be a new directory under a trusted existing parent")
    first = scope.inspect(source_dir)
    if (
        first.get("status") != "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
        or first.get("publication_authorized") is not False
        or first.get("independent_security_review_complete") is not False
    ):
        raise HandoffError("source Core scope is not qualified for a private handoff")
    expected = first.get("inspected_private_snapshot_sha256")
    if (
        not isinstance(expected, dict)
        or set(expected) != {"wheel", "sdist"}
        or any(
            not isinstance(expected[k], str)
            or len(expected[k]) != 64
            or any(c not in "0123456789abcdef" for c in expected[k])
            for k in ("wheel", "sdist")
        )
    ):
        raise HandoffError("missing or invalid private snapshot digest receipt")

    scratch: Path | None = None
    try:
        scratch = Path(tempfile.mkdtemp(prefix=".medorigin-core-handoff-", dir=parent))
        packages = _qualified_pair(source_dir)
        snapshot = (
            scope._windows_pinned_scope_archives(source_dir, packages)
            if os.name == "nt"
            else scope._posix_pinned_scope_archives(source_dir, packages)
        )
        with snapshot as pinned:
            for kind in ("wheel", "sdist"):
                source = pinned[kind][0]
                destination = scratch / source.name
                with source.open("rb") as reader, destination.open("xb") as output:
                    shutil.copyfileobj(reader, output, length=1024 * 1024)
                if _sha256(destination) != expected[kind]:
                    raise HandoffError("archive bytes differ from inspected private receipt")
            staged_check = scope.inspect(scratch)
            if (
                staged_check.get("status") != "BASE_CORE_PUBLICATION_SCOPE_CLEAN"
                or staged_check.get("inspected_private_snapshot_sha256") != expected
                or staged_check.get("publication_authorized") is not False
            ):
                raise HandoffError("staged archive metadata or SHA-256 cannot be requalified")
        # The source directory has passed final identity checks on snapshot exit.
        # Prevent accidental clobber; this is not a transactional/hostile-process
        # lock against future changes to this new directory after return.
        if target_dir.exists() or target_dir.is_symlink():
            raise HandoffError("destination appeared during private handoff")
        scratch.rename(target_dir)
        scratch = None
        return {
            "status": "STAGED_SCOPE_CLEAN_NOT_AUTHORIZED",
            "inspected_private_snapshot_sha256": expected,
            "publication_authorized": False,
            "independent_security_review_complete": False,
        }
    except (scope.PublicationScopeError, OSError, ValueError) as exc:
        raise HandoffError("private artifact handoff could not be qualified") from exc
    finally:
        if scratch is not None:
            shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = stage(args.dist, args.out)
    except HandoffError as exc:
        print(
            json.dumps({"status": "BLOCKED", "reason": str(exc), "publication_authorized": False})
        )
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
