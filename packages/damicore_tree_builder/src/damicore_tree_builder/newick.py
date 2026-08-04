from __future__ import annotations

from damicore_tree_builder.models import Tree


def _escape(identifier: str) -> str:
    if identifier and all(character not in identifier for character in " \t\n\r():;,[]'"):
        return identifier
    return "'" + identifier.replace("'", "''") + "'"


def to_newick(tree: Tree) -> str:
    children: dict[str, list[tuple[str, float]]] = {}
    for edge in tree.edges:
        children.setdefault(edge.source, []).append((edge.target, edge.length))

    def render(node_id: str, length: float | None = None) -> str:
        descendants = sorted(children.get(node_id, []), key=lambda item: item[0])
        prefix = ""
        if descendants:
            prefix = "(" + ",".join(render(child, branch) for child, branch in descendants) + ")"
        value = prefix + _escape(node_id)
        if length is not None:
            value += ":" + repr(float(length))
        return value

    return render(tree.root_id) + ";"
