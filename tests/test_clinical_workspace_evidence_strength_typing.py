"""Type-contract guard for synthetic claims, evidence links and verdicts.

This does not qualify real clinical evidence. Unsupported or citation-only claims
remain subject to explicit abstention and fail-closed assessment rules.
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
    / "evidence_strength.py"
)


def test_evidence_strength_signatures_remain_explicitly_annotated() -> None:
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    missing: list[str] = []
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        count += 1
        if node.returns is None:
            missing.append(f"{node.name}: return")
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ):
            if argument.arg != "self" and argument.annotation is None:
                missing.append(f"{node.name}: {argument.arg}")
        for variadic in (node.args.vararg, node.args.kwarg):
            if variadic is not None and variadic.annotation is None:
                missing.append(f"{node.name}: {variadic.arg}")
    assert count >= 60
    assert not missing, f"untyped evidence strength APIs: {missing}"
