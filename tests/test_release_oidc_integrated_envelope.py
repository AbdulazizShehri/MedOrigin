"""Nonpublishing exact-source integration regression for the TestPyPI artifact boundary.

Run with: python3 -m unittest discover -s tests -p test_release_oidc_integrated_envelope.py
This executes the actual workflow Bash on synthetic files; it never invokes OIDC,
builds a distribution, installs dependencies, or publishes anything.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"


def job_block(workflow: str, name: str) -> str:
    start = f"  {name}:\n"
    if workflow.count(start) != 1:
        raise AssertionError(f"Missing or duplicate job: {name}")
    remainder = workflow.split(start, 1)[1]
    next_job = re.search(r"(?m)^  [a-z0-9-]+:\\s*$", remainder)
    return remainder[: next_job.start()] if next_job else remainder


def actual_oidc_shell(workflow: str) -> str:
    job = job_block(workflow, "testpypi-publish")
    start = "      - name: Verify exact distribution payload\n        shell: bash\n        run: |\n"
    end = "      # The only route here is needs: github-release"
    if job.count(start) != 1 or job.count(end) != 1:
        raise AssertionError("Actual downstream payload shell boundary changed")
    return textwrap.dedent(job.split(start, 1)[1].split(end, 1)[0])


class TestReleaseOidcIntegratedEnvelope(unittest.TestCase):
    def test_cross_job_sha_name_and_private_staging_still_present(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        build = job_block(source, "build")
        release = job_block(source, "github-release")
        pypi = job_block(source, "testpypi-publish")
        self.assertIn("stage_verified_core_handoff.py --dist dist --out qualified-dist", build)
        self.assertIn("files: qualified-dist/*", release)
        self.assertIn("needs: [github-release, build]", pypi)
        self.assertIn("BUILD_WHEEL_SHA256: ${{ needs.build.outputs.wheel_sha256 }}", pypi)
        self.assertIn("BUILD_SDIST_SHA256: ${{ needs.build.outputs.sdist_sha256 }}", pypi)
        self.assertIn("BUILD_WHEEL_FILENAME: ${{ needs.build.outputs.wheel_filename }}", pypi)
        self.assertIn("BUILD_SDIST_FILENAME: ${{ needs.build.outputs.sdist_filename }}", pypi)
        self.assertIn("sha256sum", pypi)
        self.assertIn("basename --", pypi)
        self.assertLess(
            pypi.index("Verify downloaded archives against build SHA-256"),
            pypi.index("Verify exact distribution payload"),
        )
        self.assertLess(
            pypi.index("Verify exact distribution payload"),
            pypi.index("pypa/gh-action-pypi-publish@"),
        )
        self.assertIn("vars.TESTPYPI_PUBLISH_ENABLED == 'true'", pypi)
        self.assertNotIn("actions/checkout@", pypi)

    @unittest.skipUnless(shutil.which("bash"), "Bash required for actual shell execution")
    def test_actual_oidc_payload_shell_rejects_unreviewed_entries(self) -> None:
        script = actual_oidc_shell(WORKFLOW.read_text(encoding="utf-8"))
        self.assertIn("set -euo pipefail", script)
        self.assertIn("dotglob", script)
        self.assertIn("test ! -L", script)
        for fixture in (
            "clean",
            "hidden",
            "unexpected-text",
            "unexpected-directory",
            "extra-wheel",
            "extra-sdist",
            "linked-wheel",
            "linked-dist",
            "missing-sdist",
            "wrong-wheel-name",
        ):
            with self.subTest(fixture=fixture):
                with tempfile.TemporaryDirectory(prefix="medorigin-oidc-integration-") as tmp:
                    root = Path(tmp)
                    dist = root / "dist"
                    dist.mkdir()
                    wheel = dist / "medscale-0.3.0-py3-none-any.whl"
                    wheel.write_bytes(b"fictional-wheel")
                    sdist = dist / "medscale-0.3.0.tar.gz"
                    sdist.write_bytes(b"fictional-sdist")
                    if fixture == "hidden":
                        (dist / ".unreviewed").write_bytes(b"x")
                    elif fixture == "unexpected-text":
                        (dist / "unreviewed.txt").write_bytes(b"x")
                    elif fixture == "unexpected-directory":
                        (dist / "unreviewed").mkdir()
                    elif fixture == "extra-wheel":
                        (dist / "other-0.3.0-py3-none-any.whl").write_bytes(b"x")
                    elif fixture == "extra-sdist":
                        (dist / "other-0.3.0.tar.gz").write_bytes(b"x")
                    elif fixture == "linked-wheel":
                        target = root / "synthetic-outside"
                        target.write_bytes(b"x")
                        wheel.unlink()
                        try:
                            wheel.symlink_to(target)
                        except (OSError, NotImplementedError):
                            continue  # Windows without symlink privilege; Linux CI covers.
                    elif fixture == "linked-dist":
                        target = root / "real-dist"
                        dist.rename(target)
                        try:
                            dist.symlink_to(target, target_is_directory=True)
                        except (OSError, NotImplementedError):
                            continue
                    elif fixture == "missing-sdist":
                        sdist.unlink()
                    elif fixture == "wrong-wheel-name":
                        wheel.rename(dist / "rogue-0.3.0-py3-none-any.whl")
                    result = subprocess.run(
                        ["bash", "-c", script],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    self.assertEqual(
                        result.returncode == 0,
                        fixture == "clean",
                        (fixture, result.stdout, result.stderr),
                    )


if __name__ == "__main__":
    unittest.main()
