"""Standalone synthetic-only three-OS FHIR JSON nesting boundary smoke.

Uses stdlib and checked-out Core source; no project dependencies, network,
external validator, publisher, installer or patient data.
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from medscale.cli import fhir as fhir_cli  # noqa: E402


def _run(argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = fhir_cli.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def main() -> int:
    with TemporaryDirectory(prefix="fictional-fhir-depth-") as temporary:
        folder = Path(temporary)
        source = folder / "deep-fictional-patient.json"
        output = folder / "reports"
        source.write_text(
            '{"resourceType":"Patient","extension":' + "[" * 300 + "0" + "]" * 300 + "}",
            encoding="utf-8",
        )
        for summary_only in (False, True):
            argv = [str(source), "--output-dir", str(output)]
            if summary_only:
                argv.append("--summary-only")
            code, stdout, stderr = _run(argv)
            assert code == 1, (code, summary_only)
            assert stdout == "", (stdout, summary_only)
            assert "input read error: FHIR JSON nesting limit exceeded" in stderr
            assert "Traceback" not in stderr
            assert not output.exists()

        safe = {"resourceType": "Patient", "id": "[" * 300 + '\\\\"[]' + "]" * 300}
        source.write_text(json.dumps(safe), encoding="utf-8")
        code, stdout, stderr = _run([str(source), "--summary-only"])
        assert code == 0, (code, stderr)
        assert json.loads(stdout) == safe

    print("FICTIONAL_FHIR_JSON_NESTING_BOUNDARY_PASS_NOT_RELEASE_AUTHORITY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
