from __future__ import annotations

from damicore_tree_builder.errors import TreeBuilderError
from damicore_tree_builder.models import Tree

# Underscore is in this set on purpose. Newick converts an unquoted underscore to a blank on
# reading, and every id this package emits contains one (`column_000001`, `nj_root`), so an
# unquoted label reaches a conforming viewer with its digits split off from its prefix.
_MUST_QUOTE = " \t\n\r():;,[]'_"


def _escape(identifier: str) -> str:
    if identifier and all(character not in identifier for character in _MUST_QUOTE):
        return identifier
    return "'" + identifier.replace("'", "''") + "'"


def to_newick(tree: Tree) -> str:
    """Render `tree` as a Newick string closed by a single terminator.

    The traversal is iterative because tree depth is not bounded by the object count in any
    useful way: Neighbor Joining produces a caterpillar of depth n-1 whenever one taxon joins
    per round, so a recursive renderer exhausts the interpreter stack inside the supported
    input range rather than at some unreachable extreme.

    Raises
    ------
    TreeBuilderError
        If the edges reach a node already on the current path. A recursive renderer ends such
        a cycle with RecursionError; an iterative one would otherwise never terminate.
    """
    children: dict[str, list[tuple[str, float]]] = {}
    for edge in tree.edges:
        children.setdefault(edge.source, []).append((edge.target, edge.length))

    # A node's own branch length belongs to the edge that reaches it, not to the node, so
    # `body` holds each subtree rendered without it and the length is appended per edge.
    body: dict[str, str] = {}
    on_path: set[str] = set()
    stack: list[tuple[str, bool]] = [(tree.root_id, False)]
    while stack:
        node_id, expanded = stack.pop()
        if expanded:
            on_path.discard(node_id)
            descendants = sorted(children.get(node_id, []), key=lambda item: item[0])
            prefix = ""
            if descendants:
                prefix = (
                    "("
                    + ",".join(
                        body[child] + ":" + repr(float(length)) for child, length in descendants
                    )
                    + ")"
                )
            body[node_id] = prefix + _escape(node_id)
            continue
        if node_id in on_path:
            raise TreeBuilderError(
                "Tree edges form a cycle",
                code="artifact_validation_error",
                node_id=node_id,
            )
        on_path.add(node_id)
        stack.append((node_id, True))
        stack.extend((child, False) for child, _ in children.get(node_id, []))

    return body[tree.root_id] + ";"
