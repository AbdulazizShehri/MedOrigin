"""Fail-closed D1 manual CI contract for stacked, nonpublishing draft heads."""

from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "desktop-d1-preview.yml"


def test_d1_qualification_can_dispatch_exact_stacked_draft_head() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    header, body = content.split("\njobs:\n", maxsplit=1)
    assert "\n  workflow_dispatch:" in header
    assert "permissions:\n  contents: read" in header
    assert "github.event.pull_request.number || github.ref" in header
    assert "ref: ${{ github.event.pull_request.head.sha || github.sha }}" in body
    assert "persist-credentials: false" in body


def test_d1_manual_qualification_cannot_publish_or_bundle() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "branches: [main]" in content
    assert "runs-on: windows-latest" in content
    assert "timeout-minutes: 55" in content
    assert "config.bundle.active" in content
    assert "throw 'Packaging must remain disabled'" in content
    assert "cargo +1.97.1 test --locked --lib" in content
    for forbidden in (
        "id-token: write",
        "contents: write",
        "gh release create",
        "actions/upload-release-asset",
        "softprops/action-gh-release",
        "pypa/gh-action-pypi-publish",
        "npm publish",
    ):
        assert forbidden not in content
