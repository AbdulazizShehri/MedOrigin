"""Read-only cross-host archive comparison for the unapproved ADR-0045 proposal.

Every input must pass the exact-Git source-bound verifier BEFORE any comparison.
No archive rewriting, signing, staging, release, publishing, or ADR adoption.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
import sys
import tarfile
import zipfile
from pathlib import Path

from verify_medorigin_base_only_proposal import (
    MAX_MEMBERS,
    MAX_TOTAL,
    ProposalVerificationError,
    digest,
    load_sdist,
    load_wheel,
    verify,
)

WHEEL = "medscale-0.3.0-py3-none-any.whl"
SDIST = "medscale-0.3.0.tar.gz"
MAX_TAR_DIAGNOSTIC = MAX_TOTAL + MAX_MEMBERS * 2048


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


def _zip_compressed_fingerprint(path: Path) -> str:
    """Hash compressed ZIP member streams without rebuilding the artifact."""
    entries: list[tuple[str, str]] = []
    with path.open("rb") as stream, zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            stream.seek(member.header_offset)
            header = stream.read(30)
            if len(header) != 30 or header[:4] != b"PK\x03\x04":
                raise ProposalVerificationError("missing ZIP member local header")
            name_length, extra_length = struct.unpack_from("<HH", header, 26)
            stream.seek(member.header_offset + 30 + name_length + extra_length)
            compressed = stream.read(member.compress_size)
            if len(compressed) != member.compress_size:
                raise ProposalVerificationError("incomplete ZIP compressed stream")
            entries.append((member.filename, digest(compressed)))
    return digest(json.dumps(sorted(entries), separators=(",", ":")).encode("ascii"))


def _tar_payload_hash(path: Path) -> str:
    """Hash verified decompressed TAR bytes, including TAR headers/padding."""
    checksum = hashlib.sha256()
    inflated = 0
    with gzip.open(path, "rb") as archive:
        while chunk := archive.read(1024 * 1024):
            inflated += len(chunk)
            if inflated > MAX_TAR_DIAGNOSTIC:
                raise ProposalVerificationError("inflated TAR diagnostic exceeds budget")
            checksum.update(chunk)
    return checksum.hexdigest()


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


def compare(
    repository: Path, left: Path, right: Path, *, require_identical: bool = False
) -> dict[str, object]:
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
    archive_equal: dict[str, bool] = {}
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
        entry: dict[str, object] = {
            "left_sha256": a_hash,
            "right_sha256": b_hash,
            "archive_bytes_identical": a_hash == b_hash,
            "member_fingerprint": a_fingerprint,
            "member_count": len(a_members),
            "archive_header_difference": _changed_headers(a_meta, b_meta),
        }
        if kind == "sdist":
            a_tar, b_tar = _tar_payload_hash(a_path), _tar_payload_hash(b_path)
            entry["decompressed_tar_sha256"] = a_tar
            entry["decompressed_tar_identical"] = a_tar == b_tar
            entry["gzip_header_identical"] = a_path.read_bytes()[:10] == b_path.read_bytes()[:10]
        else:
            a_streams = _zip_compressed_fingerprint(a_path)
            b_streams = _zip_compressed_fingerprint(b_path)
            entry["compressed_member_streams_identical"] = a_streams == b_streams
            entry["left_compressed_stream_fingerprint"] = a_streams
            entry["right_compressed_stream_fingerprint"] = b_streams
        archive_equal[kind] = a_hash == b_hash
        result[kind] = entry
    both_equal = all(archive_equal[k] for k in ("wheel", "sdist"))
    result["status"] = (
        "SOURCE_BOUND_ARCHIVES_BYTE_IDENTICAL"
        if both_equal
        else "SOURCE_BOUND_MEMBERS_EQUAL_ARCHIVE_ENVELOPES_DIFFER"
    )
    if require_identical and not both_equal:
        raise ProposalVerificationError(
            "require-identical: source-bound archives have different outer bytes"
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--left", type=Path, required=True, help="First dist directory")
    parser.add_argument("--right", type=Path, required=True, help="Second dist directory")
    parser.add_argument(
        "--require-identical",
        action="store_true",
        help="Refuse nonidentical archive bytes even when all members match",
    )
    args = parser.parse_args(argv)
    try:
        output = compare(args.repo, args.left, args.right, require_identical=args.require_identical)
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
