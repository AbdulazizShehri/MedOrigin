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


def test_pr_safe_release_qualification_triggers_on_trust_boundary_edits() -> None:
    """Changes to artifact-verifier code must actually trigger release checks."""
    workflow = _workflow_text()
    prefix = workflow.split("jobs:", maxsplit=1)[0]
    assert "  pull_request:\n    branches: [main]\n    paths:" in prefix
    watch = prefix.split("    paths:", maxsplit=1)[1].split("  workflow_dispatch:", maxsplit=1)[0]
    required = (
        ".github/workflows/release.yml",
        "scripts/stage_medorigin_core_projection.py",
        "scripts/check_sdist_publication_scope.py",
        "scripts/check_core_wheel_source_identity.py",
        "scripts/inspect_release_wheel_metadata.py",
        "scripts/check_release_tag_main_head.py",
        "scripts/check_release_tag_governance.py",
        "tests/test_release_workflow_contract.py",
        "tests/test_release_tag_governance.py",
        "tests/test_release_tag_main_admission.py",
        "tests/test_sdist_publication_scope.py",
        "tests/test_core_wheel_source_identity.py",
        "tests/test_core_release_projection_identity.py",
    )
    for path in required:
        assert f"      - '{path}'" in watch, path
    # Future tag builds must remain independent of PR-only path filters.
    assert '  push:\n    tags:\n      - "v*"' in prefix

    projection_file = _WORKFLOW.parent / "core-release-projection-qualification.yml"
    projection = projection_file.read_text(encoding="utf-8")
    qualification_paths = projection.split("    paths:", maxsplit=1)[1].split(
        "  workflow_dispatch:", maxsplit=1
    )[0]
    for path in (
        "scripts/stage_medorigin_core_projection.py",
        "scripts/check_core_wheel_source_identity.py",
        "scripts/check_sdist_publication_scope.py",
        "scripts/inspect_release_wheel_metadata.py",
    ):
        assert f'      - "{path}"' in qualification_paths, path


def test_tag_build_rejects_unqualified_extras_before_artifact_upload() -> None:
    """A successful static audit cannot silently bypass the actual tag build."""
    text = _workflow_text()
    build = _job_block(text, "build")
    gate = "python3 scripts/check_base_core_publication_scope.py --dist dist"
    stage = "scripts/stage_medorigin_core_projection.py"
    assert "github.event_name == 'push'" in build
    assert "needs: quality" in build
    assert build.count(stage) == 1
    assert build.count(gate) == 1
    assert build.index("uv build ") < build.index(gate)
    assert build.index("scripts/check_core_wheel_source_identity.py") < build.index(gate)
    assert build.index("scripts/check_sdist_publication_scope.py") < build.index(gate)
    assert build.index(gate) < build.index("actions/upload-artifact@")
    assert "continue-on-error: true" not in build
    assert "|| true" not in build

    # The release must still check the exact downloaded distribution,
    # separately from the new early build gate.
    release = _job_block(text, "github-release")
    assert "needs: [quality, build, install-smoke]" in release
    assert release.count(gate.replace("python3", "python")) == 1
    assert release.index(gate.replace("python3", "python")) < release.index(
        "softprops/action-gh-release@"
    )
    pypi = _job_block(text, "testpypi-publish")
    assert "needs: [github-release, build]" in pypi

    triggers = text.split("  workflow_dispatch:", maxsplit=1)[0]
    assert "'scripts/check_base_core_publication_scope.py'" in triggers
    assert "'tests/test_base_core_publication_scope.py'" in triggers


def test_tag_scope_gate_is_not_inserted_into_nonpublishing_qualification() -> None:
    text = _workflow_text()
    build = _job_block(text, "build")
    prescope = "scripts/check_base_core_publication_scope.py --dist dist"
    assert prescope in build
    # Read-only PR qualification is allowed to inspect the original canonical
    # source artifact; it never publishes it or approves the optional extras.
    for job in ("pr-artifact-build", "pr-artifact-roundtrip", "pr-clean-wheel-smoke"):
        section = _job_block(text, job)
        assert prescope not in section
        assert "softprops/action-gh-release@" not in section
        assert "pypa/gh-action-pypi-publish@" not in section


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

    assert "needs: [github-release, build]" in block
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


def test_manual_branch_qualification_never_opens_tag_or_publish_jobs() -> None:
    text = _workflow_text()
    triggers = text.split("permissions:", maxsplit=1)[0]
    assert "  workflow_dispatch:" in triggers
    assert "  push:\n    tags:" in triggers
    assert "permissions:\n  contents: read" in text.split("jobs:", maxsplit=1)[0]

    # Authorized manual qualification must work on an exact reviewed branch
    # without retargeting a stacked Draft PR to protected main. Never on tags.
    allowed = (
        "github.event_name == 'pull_request' || "
        "(github.event_name == 'workflow_dispatch' && "
        "startsWith(github.ref, 'refs/heads/'))"
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

    def run_guard(
        values: dict[str, str],
        *,
        extra_headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        msg = Message()
        for key, value in values.items():
            msg["Project-URL"] = f"{key}, {value}"
        for header, value in extra_headers:
            msg[header] = value
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

    # Core-only release candidate must not promote installable research
    # extras, even if their dependencies are conditional on an extra.
    for extra_headers in (
        (("Provides-Extra", "rq1-runtime-feasibility"),),
        (("Requires-Dist", "pillow==12.3.0; extra == 'rq1-runtime-feasibility'"),),
    ):
        with pytest.raises(SystemExit, match="core-only"):
            run_guard(labels, extra_headers=extra_headers)

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


def test_full_ci_eight_shards_preserve_exact_full_inventory_and_coverage() -> None:
    """More parallelism must never silently omit any test or coverage shard."""
    ci = (_WORKFLOW.parent / "ci.yml").read_text(encoding="utf-8")
    shard = _job_block(ci, "pytest-shard")
    quality = _job_block(ci, "quality")
    assert 'PYTEST_SHARD_COUNT: "8"' in ci.split("jobs:", maxsplit=1)[0]
    assert "shard: [0, 1, 2, 3, 4, 5, 6, 7]" in shard
    assert "buckets = [nodeids[index::shard_count] for index in range(shard_count)]" in shard
    assert "set(flattened) != set(nodeids)" in shard
    assert "test_nodes < pytest-shard.txt" in shard
    assert "name: coverage-py${{ matrix.python-version }}-shard-${{ matrix.shard }}" in shard
    assert 'test "${#coverage_files[@]}" -eq "${PYTEST_SHARD_COUNT}"' in quality
    assert "uv run coverage report --show-missing --fail-under=77" in quality


def test_full_ci_shards_have_bounded_verbose_test_diagnostics() -> None:
    """Slow or stalled pytest nodes must be attributable and time-bounded."""
    ci = (_WORKFLOW.parent / "ci.yml").read_text(encoding="utf-8")
    shard = _job_block(ci, "pytest-shard")
    assert "timeout-minutes: 45" in shard
    assert "needs: static" in shard
    assert "fail-fast: false" in shard
    assert "-vv --durations=15" in shard
    assert "--cov --cov-report= --cov-fail-under=0" in shard
    assert '"${test_nodes[@]}"' in shard
    assert 'test -s "${COVERAGE_FILE}"' in shard


def test_tag_path_inspects_exact_wheel_archive_before_publisher() -> None:
    """The installed-metadata check alone must not bypass the strict ZIP gate."""
    text = _workflow_text()
    smoke = _job_block(text, "install-smoke")
    release = _job_block(text, "github-release")
    assert "if: github.event_name == 'push'" in smoke
    assert "needs: build" in smoke
    assert "persist-credentials: false" in smoke
    assert "ref: ${{ github.sha }}" in smoke
    assert "Verify strict Core-only wheel archive metadata" in smoke
    assert "scripts/inspect_release_wheel_metadata.py" in smoke
    assert "--require-core-only" in smoke
    assert "--expected-version" in smoke
    assert smoke.index("Verify strict Core-only wheel archive metadata") < smoke.index(
        "Verify installed wheel canonical MedOrigin URLs"
    )
    assert "test \"$(find dist -maxdepth 1 -type f -name '*.whl' | wc -l)\" -eq 1" in smoke
    assert "needs: [quality, build, install-smoke]" in release
    assert "vars.GITHUB_RELEASE_PUBLISH_ENABLED == 'true'" in release


def test_tagged_upload_and_github_release_consume_only_private_qualified_bytes() -> None:
    """Guard the actual upload path, not merely a detached author-side checker."""
    workflow = _workflow_text()
    build = _job_block(workflow, "build")
    release = _job_block(workflow, "github-release")
    handoff = "scripts/stage_verified_core_handoff.py --dist dist --out qualified-dist"
    gate = "scripts/check_base_core_publication_scope.py --dist dist"
    assert build.count(handoff) == release.count(handoff) == 1
    assert build.index(gate) < build.index(handoff) < build.index("actions/upload-artifact@")
    assert "path: qualified-dist/*" in build
    assert "path: dist/*" not in build
    assert (
        release.index(gate) < release.index(handoff) < release.index("softprops/action-gh-release@")
    )
    assert "files: qualified-dist/*" in release
    assert "files: dist/*" not in release
    for block in (build, release):
        assert "continue-on-error: true" not in block
        assert "|| true" not in block
        assert "github.event_name == 'push'" in block
    assert "vars.GITHUB_RELEASE_PUBLISH_ENABLED == 'true'" in release

    # No new tag/publication jobs are enabled and TestPyPI still only consumes
    # the qualified artifact uploaded by the build job, with owner gating.
    testpypi = _job_block(workflow, "testpypi-publish")
    assert "needs: [github-release, build]" in testpypi
    assert "packages-dir: dist" in testpypi
    assert "vars.TESTPYPI_PUBLISH_ENABLED == 'true'" in testpypi
    watch = workflow.split("    paths:", maxsplit=1)[1].split("  workflow_dispatch:", maxsplit=1)[0]
    assert "'scripts/stage_verified_core_handoff.py'" in watch


def test_nonpublishing_pr_rehearsal_remains_unaffected_by_new_handoff_gate() -> None:
    """Frozen research extras are still denied by tags but can be tested in PR."""
    workflow = _workflow_text()
    for job in ("pr-artifact-build", "pr-artifact-roundtrip", "pr-clean-wheel-smoke"):
        block = _job_block(workflow, job)
        assert "stage_verified_core_handoff.py" not in block
        assert "qualified-dist" not in block
        assert "softprops/action-gh-release@" not in block
    assert (
        _job_block(workflow, "build").count(
            "scripts/check_base_core_publication_scope.py --dist dist"
        )
        == 1
    )


def test_tag_build_exports_qualified_archive_sha256_to_later_jobs() -> None:
    """Pin exact built archive bytes outside the uploaded artifact itself."""
    workflow = _workflow_text()
    build = _job_block(workflow, "build")
    assert "wheel_sha256: ${{ steps.pin_qualified_digests.outputs.wheel_sha256 }}" in build
    assert "sdist_sha256: ${{ steps.pin_qualified_digests.outputs.sdist_sha256 }}" in build
    assert "id: pin_qualified_digests" in build
    assert "wheel_sha256=" in build
    assert "sdist_sha256=" in build
    assert "sha256sum" in build
    assert '>> "$GITHUB_OUTPUT"' in build
    assert build.index("stage_verified_core_handoff.py") < build.index(
        "id: pin_qualified_digests"
    )
    assert build.index("id: pin_qualified_digests") < build.index("actions/upload-artifact@")


def test_tag_consumers_recheck_sha256_against_original_build_outputs() -> None:
    """Not enough to trust a downloaded archive's own editable manifest."""
    workflow = _workflow_text()
    smoke = _job_block(workflow, "install-smoke")
    release = _job_block(workflow, "github-release")
    pypi = _job_block(workflow, "testpypi-publish")
    for block, after in (
        (smoke, "uv pip install"),
        (release, "softprops/action-gh-release@"),
        (pypi, "pypa/gh-action-pypi-publish@"),
    ):
        assert block.count("Verify downloaded archives against build SHA-256") == 1
        assert block.count("BUILD_WHEEL_SHA256: ${{ needs.build.outputs.wheel_sha256 }}") == 1
        assert block.count("BUILD_SDIST_SHA256: ${{ needs.build.outputs.sdist_sha256 }}") == 1
        assert "sha256sum" in block
        assert "find dist -mindepth 1 -maxdepth 1" in block
        assert block.index("Verify downloaded archives against build SHA-256") < block.index(after)
        assert "continue-on-error: true" not in block
        assert "|| true" not in block

    assert "needs: build" in smoke
    assert "needs: [quality, build, install-smoke]" in release
    assert "needs: [github-release, build]" in pypi
    assert "id-token: write" in pypi
    assert "vars.TESTPYPI_PUBLISH_ENABLED == 'true'" in pypi
    assert "actions/checkout@" not in pypi
    assert workflow.count("pypa/gh-action-pypi-publish@") == 1
