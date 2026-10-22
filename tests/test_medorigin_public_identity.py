"""Regression tests for MedOrigin's public identity and historical compatibility.

Only actively maintained public entry points are inspected. Historical research
artifacts, versioned contracts, imports and immutable receipts are intentionally
outside this test's scope.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_HOME = "https://github.com/AbdulazizShehri/MedOrigin"
_OLD_HOME = "https://github.com/TheHalfMoon/MedOrigin"


def _text(path: str) -> str:
    return (_REPO / path).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("path", "title"),
    [
        ("README.md", "# MedOrigin"),
        ("docs/README.md", "# MedOrigin Documentation"),
        ("apps/workspace/README.md", "# MedOrigin Clinical Workspace"),
        ("docs/vision/MEDORIGIN_OVERVIEW.md", "# MedOrigin — Project Overview"),
        ("docs/BRAND_TRANSITION.md", "# MedOrigin — Identity and Compatibility Policy"),
        ("ROADMAP.md", "# MedOrigin Roadmap"),
        ("CONTRIBUTING.md", "# Contributing to MedOrigin"),
    ],
)
def test_public_entry_points_use_medorigin(path: str, title: str) -> None:
    """Public-facing entry-point headings must not silently revert."""
    assert title in _text(path).splitlines()


def test_readme_points_to_current_repository_and_describes_limits() -> None:
    """The quickstart and current status must remain truthful and reachable."""
    readme = _text("README.md")
    assert "# MedOrigin" in readme.splitlines()
    assert f"git clone {_HOME}.git" in readme
    assert "cd MedOrigin" in readme
    assert f"{_HOME}/actions/workflows/ci.yml" in readme
    assert "not a medical device" in readme.lower()
    assert "synthetic-only" in readme.lower()
    assert "CW-021" in readme
    assert "MRL-0809" in readme
    # Historical links are valid in archival records, but not as today's clone URL.
    assert "git clone https://github.com/TheHalfMoon/MESC" not in readme
    assert "git clone https://github.com/TheHalfMoon/MedScale" not in readme
    assert _OLD_HOME not in readme


def test_citation_uses_current_repository_without_inventing_release() -> None:
    """Candidate citation must not falsely claim a release date."""
    citation = _text("CITATION.cff")
    assert 'title: "MedOrigin: Verifiable medical AI research infrastructure"' in citation
    assert f'repository-code: "{_HOME}"' in citation
    assert f'url: "{_HOME}"' in citation
    from medscale.__about__ import __version__ as package_version

    assert f"version: {package_version}" in citation
    assert "date-released:" not in citation
    assert "v0.2.0" in _text("RELEASES.md")
    assert "2026-07-13" in _text("RELEASES.md")


def test_security_and_docs_link_to_current_home() -> None:
    """Public security, docs and accepted governance status must remain current."""
    assert f"{_HOME}/security/advisories/new" in _text("SECURITY.md")
    docs_index = _text("docs/README.md")
    assert "(BRAND_TRANSITION.md)" in docs_index
    assert "(vision/MEDORIGIN_OVERVIEW.md)" in docs_index
    assert "(architecture/medorigin_architecture.md)" in docs_index
    assert "(../GOVERNANCE.md)" in docs_index
    assert "(../CONTRIBUTING.md)" in docs_index
    assert _OLD_HOME not in docs_index
    # Original decisions are preserved but do not require the landing page
    # to advertise historical working titles or vendor comparisons.
    for filename in (
        "0010-release-architecture.md",
        "0011-versioning-licensing.md",
    ):
        adr = _text(f"docs/adr/{filename}")
        assert "- **Status:** Accepted" in adr


@pytest.mark.parametrize(
    "path",
    [
        "docs/guides/developer_guide.md",
        "docs/guides/research_quickstart.md",
        "docs/releases/developer_package_install.md",
    ],
)
def test_active_install_guides_use_current_repo_owner(path: str) -> None:
    """Contributor setup must clone the owner of the live GitHub repository."""
    guide = _text(path)
    assert f"git clone {_HOME}.git" in guide
    assert _OLD_HOME not in guide


def test_active_release_tracking_uses_current_owner() -> None:
    """Release planning links must refer to the transferred repository."""
    document = _text("docs/releases/software_release_track.md")
    assert f"{_HOME}/issues/" in document
    assert _OLD_HOME not in document


def test_public_roadmap_retains_governance_and_not_private_strategy() -> None:
    """Keep the already-merged public roadmap rather than restore older plans."""
    document = _text("ROADMAP.md")
    assert "# MedOrigin Roadmap" in document
    assert "[GOVERNANCE.md](GOVERNANCE.md)" in document
    assert "not an unpublished strategic or engineering roadmap" in document
    assert _OLD_HOME not in document


def test_public_brand_does_not_erase_legacy_compatibility() -> None:
    """Branding is not a license to alter source-bound package/API identities."""
    policy = _text("docs/BRAND_TRANSITION.md")
    overview = _text("docs/vision/MEDORIGIN_OVERVIEW.md")
    readme = _text("README.md")
    assert "The Python distribution, import package, and command remain `medscale`." in policy
    assert "MESC" in policy and "MedScale" in policy
    assert "uv run medscale --help" in overview
    assert "`medscale`" in readme
    assert "not a finished desktop or web application" in overview
    assert "OpenMed" not in _text("docs/README.md")
    assert "OpenMed" not in _text("docs/architecture/medorigin_architecture.md")
