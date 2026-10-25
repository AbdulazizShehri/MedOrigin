"""Prevent unverified payloads hidden outside sdist archive member inventory."""

from __future__ import annotations

import gzip
import importlib.util
import io
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_medorigin_base_only_proposal.py"


@pytest.fixture
def gate() -> Any:
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location("medorigin_strict_archive", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT.parent))


@pytest.fixture
def sample_sdist(tmp_path: Path) -> tuple[Path, bytes]:
    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w") as archive:
        entry = tarfile.TarInfo("medscale-0.3.0/hello.txt")
        data = b"source-bound content\n"
        entry.size = len(data)
        archive.addfile(entry, io.BytesIO(data))
    payload = gzip.compress(tar_bytes.getvalue(), mtime=0)
    dest = tmp_path / "medscale-0.3.0.tar.gz"
    dest.write_bytes(payload)
    return dest, tar_bytes.getvalue()


def test_exact_single_gzip_tar_accepts_source_bytes(
    gate: Any, sample_sdist: tuple[Path, bytes]
) -> None:
    path, _ = sample_sdist
    assert gate.load_sdist(path) == {"medscale-0.3.0/hello.txt": b"source-bound content\n"}


@pytest.mark.parametrize(
    "attack",
    ["appended_garbage", "concatenated_gzip", "truncated_crc", "extended_header"],
)
def test_gzip_trailer_and_header_attacks_are_refused(
    gate: Any,
    sample_sdist: tuple[Path, bytes],
    attack: str,
) -> None:
    path, _ = sample_sdist
    raw = path.read_bytes()
    if attack == "appended_garbage":
        altered = raw + b"\nUNQUALIFIED_HIDDEN_BYTES\n"
    elif attack == "concatenated_gzip":
        altered = raw + gzip.compress(b"UNQUALIFIED_SECOND_GZIP_MEMBER", mtime=0)
    elif attack == "truncated_crc":
        altered = raw[:-3]
    else:
        blob = bytearray(raw)
        blob[3] = 0x08  # FNAME header flag: no longer the qualified simple envelope
        altered = bytes(blob)
    path.write_bytes(altered)
    with pytest.raises(gate.ProposalVerificationError):
        gate.load_sdist(path)


@pytest.mark.parametrize("trailer_mutation", [b"hidden", b"\0hidden", b"\x00\x01"])
def test_hidden_data_after_tar_eof_is_refused(
    gate: Any,
    sample_sdist: tuple[Path, bytes],
    trailer_mutation: bytes,
) -> None:
    path, tar_content = sample_sdist
    raw = bytearray(tar_content)
    raw[-1024 : -1024 + len(trailer_mutation)] = trailer_mutation
    path.write_bytes(gzip.compress(raw, mtime=0))
    with pytest.raises(gate.ProposalVerificationError, match="TAR trailer"):
        gate.load_sdist(path)


def test_decompression_budget_fails_closed_without_large_allocation(
    gate: Any,
    sample_sdist: tuple[Path, bytes],
) -> None:
    path, _ = sample_sdist
    gate.MAX_TAR_ENVELOPE = 4096
    with pytest.raises(gate.ProposalVerificationError, match="budget"):
        gate.load_sdist(path)


def test_non_aligned_tar_payload_refused(gate: Any, sample_sdist: tuple[Path, bytes]) -> None:
    path, uncompressed = sample_sdist
    path.write_bytes(gzip.compress(uncompressed + b"bad", mtime=0))
    with pytest.raises(gate.ProposalVerificationError, match="aligned"):
        gate.load_sdist(path)


def test_real_source_bound_sdist_envelope_when_available(gate: Any) -> None:
    artifact = Path(r"C:\Users\Shehr\work\MedOrigin-PR630-20261025-dist\medscale-0.3.0.tar.gz")
    if not artifact.exists():
        pytest.skip("External Windows exact-head sdist fixture is optional")
    contents = gate.load_sdist(artifact)
    assert len(contents) == 258
    assert contents["medscale-0.3.0/.gitignore"] == b""
