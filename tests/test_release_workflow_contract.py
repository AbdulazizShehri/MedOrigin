from __future__ import annotations

import re
from pathlib import Path

_WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
_JOB_HEADER_RE = re.compile(r"^  [a-z0-9-]+:\s*$", re.MULTILINE)
_PUBLISH_ACTION = "pypa/gh-action-pypi-publish@7245906fb61fa33a13554f9d5fb856fe61758086"
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


def _installed_wheel_url_guard_script() -> str:
    """Extract the actual published-tag installed-wheel guard, not a copy."""
    from textwrap import dedent

    block = _job_block(_workflow_text(), "install-smoke")
    assert "Verify installed wheel canonical MedOrigin URLs before publication" in block
    marker = ".venv/bin/python - <<'PY'\n"
    assert block.count(marker) == 1
    script = block.split(marker, maxsplit=1)[1].split("\n          PY", maxsplit=1)[0]
    return dedent(script)


def test_tag_release_rejects_stale_or_missing_wheel_metadata_urls() -> None:
    """Check fail-closed release logic against real in-memory METADATA messages."""
    from email.message import Message
    from unittest.mock import patch

    import pytest

    canonical = "https://github.com/AbdulazizShehri/MedOrigin"
    labels = {
        "Homepage": canonical,
        "Repository": canonical,
        "Documentation": canonical + "/tree/main/docs",
        "Issues": canonical + "/issues",
    }
    script = _installed_wheel_url_guard_script()
    assert "from importlib.metadata import metadata" in script
    assert 'metadata("medscale")' in script

    def run_guard(values: dict[str, str]) -> None:
        msg = Message()
        for key, value in values.items():
            msg["Project-URL"] = f"{key}, {value}"
        with patch("importlib.metadata.metadata", return_value=msg) as read_metadata:
            exec(compile(script, "release.yml:tag-wheel-metadata-guard", "exec"), {})
        read_metadata.assert_called_once_with("medscale")

    # The complete canonical candidate may pass a future authorized release.
    run_guard(labels)

    # Today's exact wheel would be blocked, even if tag+publication guards
    # were enabled: it still advertises the frozen MESC package URL values.
    for broken_key in labels:
        stale = dict(labels)
        stale[broken_key] = labels[broken_key].replace("/MedOrigin", "/MESC")
        with pytest.raises(SystemExit, match=broken_key):
            run_guard(stale)

        missing = {key: url for key, url in labels.items() if key != broken_key}
        with pytest.raises(SystemExit, match=broken_key):
            run_guard(missing)

    # Duplicate metadata must not be accepted through last-write-wins.
    duplicate = Message()
    for key, url in labels.items():
        duplicate["Project-URL"] = f"{key}, {url}"
    duplicate["Project-URL"] = f"Homepage, {canonical}"
    with (
        patch("importlib.metadata.metadata", return_value=duplicate),
        pytest.raises(SystemExit, match="duplicate"),
    ):
        exec(compile(script, "release.yml:tag-wheel-metadata-guard", "exec"), {})


def test_tag_release_requires_qualified_wheel_url_gate_before_github_release() -> None:
    text = _workflow_text()
    smoke = _job_block(text, "install-smoke")
    release = _job_block(text, "github-release")
    assert "needs: build" in smoke
    assert "Verify installed wheel canonical MedOrigin URLs before publication" in smoke
    assert "uv pip install --python .venv/bin/python --no-deps" in smoke
    assert "needs: [quality, build, install-smoke]" in release
    assert "vars.GITHUB_RELEASE_PUBLISH_ENABLED == 'true'" in release


def test_tag_and_pr_paths_use_identical_audited_core_projection() -> None:
    """Source build, metadata and sdist checks must precede all artifact use."""
    text = _workflow_text()
    required_stage = (
        "uv run --no-sync python scripts/stage_medorigin_core_projection.py "
        '--out "$RUNNER_TEMP/medorigin-core"'
    )
    required_build = 'run: uv build "$RUNNER_TEMP/medorigin-core" --out-dir dist'
    wheel_check = "scripts/inspect_release_wheel_metadata.py --wheel"
    archive_check = "scripts/check_sdist_publication_scope.py --sdist"
    for job_id in ("build", "pr-artifact-build"):
        block = _job_block(text, job_id)
        assert block.count(required_stage) == 1
        assert block.count(required_build) == 1
        assert block.count(wheel_check) == 1
        assert block.count(archive_check) == 1
        assert block.index(required_stage) < block.index(required_build)
        assert block.index(required_build) < block.index(wheel_check)
        assert block.index(wheel_check) < block.index(archive_check)
        assert block.index(archive_check) < block.index("actions/upload-artifact@")
        assert "uv build\n" not in block
        assert "contents: write" not in block
        assert "id-token: write" not in block

    assert text.count(required_stage) == 2
    assert text.count(required_build) == 2
    assert text.count(wheel_check) == 2
    assert text.count(archive_check) == 2
    assert "vars.GITHUB_RELEASE_PUBLISH_ENABLED == 'true'" in _job_block(text, "github-release")
    assert "vars.TESTPYPI_PUBLISH_ENABLED == 'true'" in _job_block(text, "testpypi-publish")
