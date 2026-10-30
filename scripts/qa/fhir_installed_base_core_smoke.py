"""Cross-OS installed Core-only FHIR CLI smoke for fictional developer data.

All build artifacts and virtualenvs are disposable and never uploaded.
This QA script does not authorize the unapproved base-only package lineage.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FROZEN = (ROOT / "pyproject.toml", ROOT / "uv.lock")
PROPOSAL_RECEIPT = "MEDORIGIN_SOURCE_PROVENANCE.json"


def _run(args: list[str], *, cwd: Path, expect: int = 0) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    process = subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True, check=False, timeout=300
    )
    if process.returncode != expect:
        raise AssertionError(
            f"command failed with exit {process.returncode}, expected {expect}; "
            f"stdout={process.stdout[-1500:]!r}; stderr={process.stderr[-1500:]!r}"
        )
    return process


def _snapshot() -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in FROZEN}


def _assert_cli(cli: Path, tmp: Path, filename: str, data: bytes, *, valid: bool) -> None:
    src = tmp / filename
    src.write_bytes(data)
    out = tmp / (filename + "-reports")
    command = [str(cli), "fhir", "validate", str(src), "--output-dir", str(out)]
    result = _run(command, cwd=tmp, expect=0 if valid else 1)
    assert "Traceback" not in result.stderr
    if valid:
        body, *_ = result.stdout.splitlines()
        report: dict[str, Any] = json.loads(body)
        assert isinstance(report, dict)
        assert list(out.rglob("report.json")), "installed CLI did not persist a FHIR report"
        assert "report stored at:" in result.stderr
    else:
        assert result.stdout == "", "invalid input leaked a report to stdout"
        assert "input read error:" in result.stderr, result.stderr[-500:]
        assert not out.exists(), "invalid input unexpectedly persisted a report"
    print(f"INSTALLED_FHIR_{'ACCEPTED' if valid else 'REJECTED'}: {filename}")


def main() -> int:
    before = _snapshot()
    with tempfile.TemporaryDirectory(prefix="medorigin-fhir-installed-") as scratch:
        tmp = Path(scratch)
        proposal = tmp / "unapproved-proposal"
        dist = tmp / "artifacts-never-upload"
        venv = tmp / "isolated-venv"

        _run(
            [
                sys.executable,
                str(ROOT / "scripts/stage_medorigin_base_only_proposal.py"),
                "--out",
                str(proposal),
            ],
            cwd=ROOT,
        )
        receipt = json.loads((proposal / PROPOSAL_RECEIPT).read_text(encoding="utf-8"))
        assert receipt["schema"] == "MEDORIGIN-CORE-BASE-ONLY-PROPOSAL-1"
        assert receipt["publication_authorized"] is False
        assert receipt["adr_0044_amendment_accepted"] is False
        assert receipt["independent_security_review_completed"] is False

        _run(["uv", "build", str(proposal), "--out-dir", str(dist)], cwd=ROOT)
        _run(
            [
                sys.executable,
                str(ROOT / "scripts/check_base_core_publication_scope.py"),
                "--dist",
                str(dist),
            ],
            cwd=ROOT,
        )
        wheels = list(dist.glob("medscale-*.whl"))
        sdists = list(dist.glob("medscale-*.tar.gz"))
        assert len(wheels) == 1 and len(sdists) == 1, "ambiguous base-only build output"

        _run(["uv", "venv", "--python", sys.executable, str(venv)], cwd=tmp)
        py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cli = venv / ("Scripts/medscale.exe" if os.name == "nt" else "bin/medscale")
        _run(["uv", "pip", "install", "--python", str(py), "--no-deps", str(wheels[0])], cwd=tmp)
        assert cli.is_file(), "expected wheel's installed console command"

        # Real subprocesses from the clean Wheel installation, not local source imports.
        _assert_cli(
            cli,
            tmp,
            "fictional-patient.json",
            b'{"resourceType":"Patient","id":"fictional-only"}',
            valid=True,
        )
        _assert_cli(cli, tmp, "invalid-utf8.json", bytes([0xFF, 0xFE, 0x80]), valid=False)
        _assert_cli(
            cli,
            tmp,
            "duplicate-key.json",
            b'{"resourceType":"Patient","id":"a","id":"b"}',
            valid=False,
        )
        _assert_cli(cli, tmp, "non-object.json", b"[]", valid=False)
        _assert_cli(cli, tmp, "missing-type.json", b'{"id":"fictional"}', valid=False)
        _assert_cli(
            cli,
            tmp,
            "overflow-number.json",
            b'{"resourceType":"Patient","value":1e999}',
            valid=False,
        )
        _assert_cli(
            cli,
            tmp,
            "lone-surrogate.json",
            b'{"resourceType":"Patient","id":"\\ud800"}',
            valid=False,
        )

        deep = b'{"resourceType":"Patient","extension":' + b"[" * 300 + b"0" + b"]" * 300 + b"}"
        _assert_cli(cli, tmp, "deep-nesting.json", deep, valid=False)
        # --summary-only must also fail before printing the deeply nested JSON.
        summary_out = tmp / "deep-summary-reports"
        summary = _run(
            [
                str(cli),
                "fhir",
                "validate",
                str(tmp / "deep-nesting.json"),
                "--summary-only",
                "--output-dir",
                str(summary_out),
            ],
            cwd=tmp,
            expect=1,
        )
        assert summary.stdout == ""
        assert "FHIR JSON nesting limit exceeded" in summary.stderr
        assert "Traceback" not in summary.stderr and not summary_out.exists()
        print("INSTALLED_FHIR_DEPTH_SUMMARY_REJECTED")

        # Exercise the actual installed console script, not source imports.
        # A sparse >8 MiB fictional file must fail before JSON decoding, in
        # both normal report mode and the stdout-only summary path.
        oversized = tmp / "oversized-8mib.json"
        with oversized.open("wb") as stream:
            stream.truncate(8 * 1024 * 1024 + 1)
        for summary_only in (False, True):
            mode = "summary" if summary_only else "report"
            output = tmp / f"oversized-{mode}-reports"
            argv = [
                str(cli),
                "fhir",
                "validate",
                str(oversized),
                "--output-dir",
                str(output),
            ]
            if summary_only:
                argv.append("--summary-only")
            denied = _run(argv, cwd=tmp, expect=1)
            assert denied.stdout == "", "oversized installed CLI printed a report"
            assert "FHIR JSON input exceeds 8 MiB limit" in denied.stderr
            assert "Traceback" not in denied.stderr
            assert not output.exists(), "oversized input persisted an invalid report"
            print(f"INSTALLED_FHIR_BYTE_BOUND_REJECTED: {mode}")

        # An existing unrelated local output file must be preserved, not overwritten.
        input_file = tmp / "valid-again.json"
        input_file.write_bytes(b'{"resourceType":"Patient","id":"fictional"}')
        occupied = tmp / "do-not-overwrite.txt"
        occupied.write_text("original fictional bytes", encoding="utf-8")
        refused = _run(
            [str(cli), "fhir", "validate", str(input_file), "--output-dir", str(occupied)],
            cwd=tmp,
            expect=1,
        )
        assert refused.stdout == ""
        assert "report storage error:" in refused.stderr and "Traceback" not in refused.stderr
        assert occupied.read_text(encoding="utf-8") == "original fictional bytes"
        print("INSTALLED_FHIR_REPORT_CLOBBER_REFUSED")

    assert before == _snapshot(), "frozen research root/lock changed during installed smoke"
    assert not (ROOT / "dist").exists(), "refuse repository-local build outputs"
    print("INSTALLED_FHIR_3OS_PROPOSAL_SMOKE_PASS_NOT_PUBLICATION_AUTHORITY")
    print("BASE_ONLY_PROPOSAL_NOT_APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
