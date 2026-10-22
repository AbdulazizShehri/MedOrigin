"""Guards against accidentally re-publishing private agent and strategy notes.

Public scientific protocols and original source evidence are deliberately
outside this presentation-only check.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_STUB = "# Historical planning reference"
_REDACTED = (
    "docs/architecture/ai_model_strategy.md",
    "docs/strategy/mesc_capability_realization_layer_2026-08-18.md",
    "docs/strategy/mesc_frontier_program_2026-08-18.md",
    "docs/strategy/mesc_health_model_program_2026-09-05.md",
    "docs/strategy/mesc_strategic_model_roadmap_2026-08-18.md",
)


def test_no_tracked_local_agent_config_or_donor_strategy_drafts() -> None:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=_ROOT,
        capture_output=True,
        check=True,
    )
    paths = set(result.stdout.decode("utf-8").rstrip("\x00").split("\x00"))
    forbidden = {
        "AGENTS.md",
        "AGENT.md",
        "CLAUDE.md",
        "CURSOR.md",
        "cursor.md",
        ".cursorrules",
    }
    assert not paths.intersection(forbidden)
    assert not any(
        path.startswith(("docs/strategy/donors/", ".cursor/", ".claude/")) for path in paths
    )


def test_public_strategy_placeholders_do_not_publish_internal_plan() -> None:
    for path in _REDACTED:
        text = (_ROOT / path).read_text(encoding="utf-8")
        assert text.startswith(_STUB)
        assert len(text) < 900
    roadmap = (_ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert roadmap.startswith("# MedOrigin Roadmap")
    assert len(roadmap) < 2200
    assert "not an unpublished strategic or engineering roadmap" in roadmap
