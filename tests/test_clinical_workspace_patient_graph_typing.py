"""Protect typed synthetic graph read, identity, and deletion APIs.

The other graph features and full Workspace strict typing remain separate work.
No clinical or research capability follows from these annotations.
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
    / "patient_graph.py"
)
_PUBLIC = {
    "node_id_for",
    "edge_id_for",
    "view_id_for",
    "node_binding",
    "edge_binding",
    "view_binding",
    "read_node",
    "read_edge",
    "read_view",
    "delete_node",
    "delete_edge",
}
_CLASSES = {"GraphNode", "GraphEdgeSource", "GraphEdge", "GraphView", "PathExplanation"}


def test_graph_read_and_delete_signatures_remain_explicitly_typed() -> None:
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    seen: set[str] = set()
    missing: list[str] = []

    def check(node: ast.FunctionDef) -> None:
        if node.returns is None:
            missing.append(f"{node.name}: return")
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            if argument.arg != "self" and argument.annotation is None:
                missing.append(f"{node.name}: {argument.arg}")
        for variable in (node.args.vararg, node.args.kwarg):
            if variable is not None and variable.annotation is None:
                missing.append(f"{node.name}: {variable.arg}")

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in _PUBLIC:
            seen.add(node.name)
            check(node)
        elif isinstance(node, ast.ClassDef) and node.name in _CLASSES:
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name in {
                    "validated",
                    "to_document",
                    "from_document",
                }:
                    check(method)
    assert seen == _PUBLIC
    assert not missing, f"untyped graph read/delete boundaries: {missing}"
