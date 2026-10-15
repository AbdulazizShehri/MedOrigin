"""Typed boundaries for synthetic linked objects and one-way research references.

This test guards signatures only, never asserts Research Core backflow authority.
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
    / "linked_workspace.py"
)
_CLASSES = {
    "ResearchRef",
    "LinkedDocument",
    "LinkedTable",
    "MemberRef",
    "LinkSource",
    "WorkspaceLink",
}
_API = {
    "document_id_for",
    "table_id_for",
    "link_id_for",
    "document_binding",
    "table_binding",
    "link_binding",
    "member_binding",
    "read_document",
    "read_table",
    "verify_member",
    "read_link",
    "resolve_link",
    "links_for_member",
    "delete_link",
    "delete_member",
    "admit_document",
    "admit_table",
    "admit_link",
}


def test_linked_workspace_read_and_identity_signatures_are_typed() -> None:
    module = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    found: set[str] = set()
    missing: list[str] = []

    def inspect(node: ast.FunctionDef) -> None:
        if node.returns is None:
            missing.append(f"{node.name}: return")
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            if arg.arg != "self" and arg.annotation is None:
                missing.append(f"{node.name}: {arg.arg}")
        for variadic in (node.args.vararg, node.args.kwarg):
            if variadic is not None and variadic.annotation is None:
                missing.append(f"{node.name}: {variadic.arg}")

    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name in _API:
            found.add(node.name)
            inspect(node)
        elif isinstance(node, ast.ClassDef) and node.name in _CLASSES:
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name in {
                    "validated",
                    "to_document",
                    "from_document",
                }:
                    inspect(method)
    assert found == _API
    assert not missing, f"untyped linked workspace boundaries: {missing}"
