"""Protect explicit typing of the read-only synthetic Research View boundary.

This regression checks signature annotations only. It is not a substitute for
strict mypy qualification across the full Workspace package.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "workspace"
    / "src"
    / "medscale_workspace"
    / "research_view.py"
)


def test_research_view_callable_signatures_remain_typed() -> None:
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    missing: list[str] = []
    functions = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        functions += 1
        if node.returns is None:
            missing.append(f"{node.name}: return")
        for argument in [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ]:
            if argument.arg != "self" and argument.annotation is None:
                missing.append(f"{node.name}: {argument.arg}")
        for argument in (node.args.vararg, node.args.kwarg):
            if argument is not None and argument.annotation is None:
                missing.append(f"{node.name}: {argument.arg}")
    assert functions >= 23
    assert not missing, f"untyped Research View API signatures: {missing}"
