from __future__ import annotations

import re
from pathlib import Path

_WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
_JOB_HEADER_RE = re.compile(r"^  [a-z0-9-]+:\s*$", re.MULTILINE)
_PUBLISH_ACTION = "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33"
_DOWNLOAD_ACTION = "actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333"


def _workflow_text() -> str:
    return _WORKFLOW.read_text(encoding="utf-8")


def _job_block(text: str, job_id: str) -> str:
    marker = f"  {job_id}:\n"
    start = text.index(marker)
    tail = text[start + len(marker) :]
    next_job = _JOB_HEADER_RE.search(tail)
    end = len(text) if next_job is None else start + len(marker) + next_job.start()
    return text[start:end]


def test_testpypi_publish_job_is_fail_closed_and_least_privilege() -> None:
    text = _workflow_text()
    block = _job_block(text, "testpypi-publish")
    compact = " ".join(line.strip() for line in block.splitlines())

    release_block = _job_block(text, "github-release")
    assert "needs: [quality, build, install-smoke]" in release_block
    assert "vars.GITHUB_RELEASE_PUBLISH_ENABLED == 'true'" in release_block
    assert "github.event_name == 'push'" in release_block
    assert "startsWith(github.ref, 'refs/tags/v')" in release_block
    assert "contents: write" in release_block

    assert "needs: github-release" in block
    assert "github.event_name == 'push'" in block
    assert "startsWith(github.ref, 'refs/tags/v')" in block
    assert "vars.TESTPYPI_PUBLISH_ENABLED == 'true'" in block
    assert "environment: testpypi" in block
    assert "permissions: id-token: write" in compact

    workflow_prefix = text.split("jobs:", maxsplit=1)[0]
    assert "permissions:\n  contents: read" in workflow_prefix
    assert "id-token:" not in workflow_prefix
    assert text.count("id-token:") == block.count("id-token:") == 1


def test_testpypi_publish_job_reuses_exact_artifact_without_rebuild_or_secret() -> None:
    text = _workflow_text()
    block = _job_block(text, "testpypi-publish")

    assert _DOWNLOAD_ACTION in block
    assert "name: dist-${{ github.ref_name }}" in block
    assert "path: dist" in block
    assert _PUBLISH_ACTION in block
    assert "repository-url: https://test.pypi.org/legacy/" in block
    assert "packages-dir: dist" in block
    assert "attestations: true" in block
    assert text.count(_PUBLISH_ACTION) == 1

    for forbidden in (
        "actions/checkout@",
        "uv build",
        "password:",
        "user:",
        "secrets.",
        "twine",
    ):
        assert forbidden not in block


def test_manual_main_qualification_never_opens_tag_or_publish_jobs() -> None:
    text = _workflow_text()
    triggers = text.split("permissions:", maxsplit=1)[0]
    assert "  workflow_dispatch:" in triggers
    assert "  push:\n    tags:" in triggers
    assert "permissions:\n  contents: read" in text.split("jobs:", maxsplit=1)[0]

    allowed = (
        "github.event_name == 'pull_request' || "
        "(github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main')"
    )
    for job_id in ("pr-artifact-build", "pr-artifact-roundtrip", "pr-clean-wheel-smoke"):
        block = _job_block(text, job_id)
        assert f"if: {allowed}" in block
        assert "gh release" not in block
        assert "softprops/action-gh-release@" not in block
        assert "pypa/gh-action-pypi-publish@" not in block

    for job_id in ("quality", "build", "install-smoke", "github-release", "testpypi-publish"):
        block = _job_block(text, job_id)
        assert "github.event_name == 'push'" in block
        assert "workflow_dispatch" not in block

    artifact = "release-action-roundtrip-" + "${{ github.run_id }}-${{ github.run_attempt }}"
    assert text.count(artifact) == 3
    assert "github.event.pull_request.number" not in text
