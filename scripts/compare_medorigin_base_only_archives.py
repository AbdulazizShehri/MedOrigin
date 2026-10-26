"""Read-only cross-host archive comparison for the unapproved ADR-0045 proposal.

Every input must pass the exact-Git source-bound verifier BEFORE any comparison.
No archive rewriting, signing, staging, release, publishing, or ADR adoption.
"""

from __future__ import annotations

import argparse
import json
import sys
import tarfile
import zipfile
from pathlib import Path

from verify_medorigin_base_only_proposal import (
    ProposalVerificationError,
    digest,
    load_sdist,
    load_wheel,
    verify,
)

WHEEL = "medscale-0.3.0-py3-none-any.whl"
SDIST = "medscale-0.3.0.tar.gz"


def _fingerprint(members: dict[str, bytes]) -> str:
    """Stable digest of exact names and uncompressed member bytes."""
    entries = [(name, digest(blob)) for name, blob in sorted(members.items())]
    return digest(json.dumps(entries, separators=(",", ":"), ensure_ascii=True).encode("ascii"))


def _zip_headers(path: Path) -> dict[str, dict[str, object]]:
    with zipfile.ZipFile(path) as archive:
        return {
            member.filename: {
                "create_system": member.create_system,
                "date_time": list(member.date_time),
                "external_attr": member.external_attr,
                "flag_bits": member.flag_bits,
                "compress_type": member.compress_type,
                "compress_size": member.compress_size,
                "extra_sha256": digest(member.extra),
                "comment_sha256": digest(member.comment),
            }
            for member in archive.infolist()
        }


def _tar_headers(path: Path) -> dict[str, dict[str, object]]:
    with tarfile.open(path, mode="r:gz") as archive:
        return {
            member.name: {
                "type": member.type.decode("latin-1"),
                "mtime": member.mtime,
                "mode": member.mode,
                "uid": member.uid,
                "gid": member.gid,
                "uname": member.uname,
                "gname": member.gname,
                "pax_headers": dict(sorted(member.pax_headers.items())),
            }
            for member in archive.getmembers()
        }


def _changed_headers(
    left: dict[str, dict[str, object]],
    right: dict[str, dict[str, object]],
) -> dict[str, object]:
    names = sorted(set(left) | set(right))
    changed = [name for name in names if left.get(name) != right.get(name)]
    return {"changed_count": len(changed), "first_changed_members": changed[:20]}


def compare(repository: Path, left: Path, right: Path) -> dict[str, object]:
    """Compare artifacts only after both independently pass Git-bound verification."""
    left = left.resolve()
    right = right.resolve()
    if left == right:
        raise ProposalVerificationError("comparison requires distinct directories")
    # Fail closed on any source, metadata, injected-member, archive, or RECORD defect.
    left_gate = verify(repository, left)
    right_gate = verify(repository, right)
    result: dict[str, object] = {
        "schema": "MEDORIGIN-ADR0045-CROSS-HOST-DIAGNOSTIC-1",
        "source_git_commit": left_gate["source_git_commit"],
        "adr_0045_accepted": False,
        "independent_review_complete": False,
        "publication_authorized": False,
    }
    if left_gate["source_git_commit"] != right_gate["source_git_commit"]:
        raise ProposalVerificationError("comparison spans different Git source revisions")
    for kind, filename, load in (
        ("wheel", WHEEL, load_wheel),
        ("sdist", SDIST, load_sdist),
    ):
        a_path, b_path = left / filename, right / filename
        a_members, b_members = load(a_path), load(b_path)
        a_fingerprint, b_fingerprint = _fingerprint(a_members), _fingerprint(b_members)
        if a_fingerprint != b_fingerprint or a_members != b_members:
            raise ProposalVerificationError(f"{kind} source-bound member bytes differ")
        a_hash, b_hash = digest(a_path.read_bytes()), digest(b_path.read_bytes())
        a_meta = _zip_headers(a_path) if kind == "wheel" else _tar_headers(a_path)
        b_meta = _zip_headers(b_path) if kind == "wheel" else _tar_headers(b_path)
        result[kind] = {
            "left_sha256": a_hash,
            "right_sha256": b_hash,
            "archive_bytes_identical": a_hash == b_hash,
            "member_fingerprint": a_fingerprint,
            "member_count": len(a_members),
            "archive_header_difference": _changed_headers(a_meta, b_meta),
        }
        if kind == "sdist":
            result[kind]["gzip_header_identical"] = (
                a_path.read_bytes()[:10] == b_path.read_bytes()[:10]
            )
    both_equal = all(result[k]["archive_bytes_identical"] for k in ("wheel", "sdist"))
    result["status"] = (
        "SOURCE_BOUND_ARCHIVES_BYTE_IDENTICAL"
        if both_equal
        else "SOURCE_BOUND_MEMBERS_EQUAL_ARCHIVE_ENVELOPES_DIFFER"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--left", type=Path, required=True, help="First dist directory")
    parser.add_argument("--right", type=Path, required=True, help="Second dist directory")
    args = parser.parse_args(argv)
    try:
        output = compare(args.repo, args.left, args.right)
    except (
        ProposalVerificationError,
        OSError,
        ValueError,
        KeyError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as exc:
        print(
            json.dumps(
                {"status": "BLOCKED", "reason": str(exc), "publication_authorized": False},
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
