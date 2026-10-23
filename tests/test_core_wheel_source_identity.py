"""Adversarial checks that exact installed Core wheel code comes from Git."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_core_wheel_source_identity.py"
DIST_INFO = "medscale-0.3.0.dist-info/"


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def _source() -> dict[str, bytes]:
    commit = _git("rev-parse", "HEAD").decode("ascii").strip()
    data = _git("archive", "--format=zip", commit, "--", "src/medscale")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {
            name.removeprefix("src/"): archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }


def _wheel(path: Path, mutation: str | None = None) -> Path:
    source = _source()
    entries = dict(source)
    entries.update(
        {
            DIST_INFO + "METADATA": b"Metadata-Version: 2.3\nName: medscale\nVersion: 0.3.0\n",
            DIST_INFO + "WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
            DIST_INFO + "entry_points.txt": b"[console_scripts]\nmedscale=medscale.cli:main\n",
            DIST_INFO + "licenses/LICENSE": _git("show", "HEAD:LICENSE"),
        }
    )
    if mutation == "tamper":
        entries["medscale/__about__.py"] += b"\n# injected post-build code\n"
    if mutation == "extra":
        entries["medscale/injected.py"] = b"print('unexpected code')\n"
    if mutation == "outside":
        entries["data/private.json"] = b"{}"
    if mutation == "license":
        entries[DIST_INFO + "licenses/LICENSE"] = b"wrong license bytes"
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name, contents in sorted(entries.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).rstrip(b"=")
        writer.writerow((name, "sha256=" + digest.decode("ascii"), str(len(contents))))
    writer.writerow((DIST_INFO + "RECORD", "", ""))
    entries[DIST_INFO + "RECORD"] = record.getvalue().encode("utf-8")
    if mutation == "record":
        entries[DIST_INFO + "RECORD"] = b"invalid,nohash,0\n"
    with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, contents in entries.items():
            archive.writestr(name, contents)
    return path


def _inspect(path: Path) -> tuple[int, dict[str, Any]]:
    run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--wheel",
            str(path),
            "--verify-source-checkout",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode in (0, 2), run.stderr
    return run.returncode, cast(dict[str, Any], json.loads(run.stdout))


def test_full_committed_source_wheel_is_read_only_and_source_bound(tmp_path: Path) -> None:
    code, report = _inspect(_wheel(tmp_path / "good.whl"))
    assert code == 0, report
    assert report["status"] == "SOURCE_BOUND_WHEEL_QUALIFIED_ONLY"
    assert report["publication_authorized"] is False
    assert report["source_file_count"] >= 200
    assert report["wheel_members"] == report["source_file_count"] + 5


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("tamper", "wheel payload bytes differ from committed Git source"),
        ("extra", "wheel Python payload membership differs from committed Git source"),
        ("outside", "wheel distribution metadata membership differs from allowlist"),
        ("license", "wheel license bytes differ from committed Git"),
        ("record", "invalid or duplicate wheel RECORD entry"),
    ],
)
def test_rehashed_record_does_not_admit_unreviewed_payload(
    tmp_path: Path, mutation: str, expected: str
) -> None:
    code, report = _inspect(_wheel(tmp_path / (mutation + ".whl"), mutation))
    assert code == 2
    assert report["status"] == "BLOCKED"
    assert report["publication_authorized"] is False
    assert any(expected in str(item) for item in report["issues"]), report


def test_corrupt_wheel_is_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "corrupt.whl"
    bad.write_bytes(b"not a zip archive")
    code, report = _inspect(bad)
    assert code == 2
    assert report["status"] == "BLOCKED"


def test_duplicate_python_entry_is_rejected(tmp_path: Path) -> None:
    path = _wheel(tmp_path / "duplicate.whl")
    with pytest.warns(UserWarning, match="Duplicate name"), zipfile.ZipFile(path, "a") as archive:
        archive.writestr("medscale/__about__.py", b"overriding version")
    code, report = _inspect(path)
    assert code == 2
    assert "duplicate wheel entry" in report["issues"]


def test_release_workflows_require_source_bound_wheel_verification() -> None:
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    check = (
        'scripts/check_core_wheel_source_identity.py --wheel "$wheel" --verify-source-checkout .'
    )
    assert release.count(check) == 2
    for step in release.split("      - name: Upload ", 1)[:1]:
        assert check in step
    qualification = (
        ROOT / ".github/workflows/core-release-projection-qualification.yml"
    ).read_text(encoding="utf-8")
    assert '      - "tests/test_core_wheel_source_identity.py"' in qualification
    assert qualification.count("scripts/check_core_wheel_source_identity.py") >= 3
