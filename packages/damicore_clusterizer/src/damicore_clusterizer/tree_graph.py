from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import igraph as ig
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from damicore_clusterizer.errors import ClusterizerError


class _TreeNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    id: str
    kind: Literal["leaf", "internal"]
    label: str | None


class _TreeEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source: str
    target: str
    length: float = Field(allow_inf_nan=False)


class _TreeArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[1]
    root_id: str
    nodes: tuple[_TreeNode, ...]
    edges: tuple[_TreeEdge, ...]


@dataclass(frozen=True)
class GraphInput:
    graph: ig.Graph
    # Vertex order as igraph holds it. Exposed here so callers never read graph.vs
    # themselves: this module is the only place that touches igraph's attribute API.
    vertex_names: tuple[str, ...]
    object_ids: tuple[str, ...]
    labels: dict[str, str]
    shift: float


def _load_tree_graph(path: Path) -> GraphInput:
    try:
        artifact = _TreeArtifact.model_validate_json(path.read_text(encoding="utf-8"))
        root_id = artifact.root_id
        nodes = artifact.nodes
        edges = artifact.edges
    except (OSError, ValidationError) as exc:
        raise ClusterizerError("Invalid tree artifact", code="tree_format_error") from exc

    node_ids = [node.id for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ClusterizerError("Tree node ids are not unique", code="tree_format_error")
    if root_id not in node_ids:
        raise ClusterizerError("Tree root_id names no node", code="tree_format_error")
    root_node = next(node for node in nodes if node.id == root_id)
    if root_node.kind != "internal":
        raise ClusterizerError("Tree root must be internal", code="tree_format_error")
    leaves = tuple(node.id for node in nodes if node.kind == "leaf")
    if len(leaves) < 2:
        raise ClusterizerError("Tree must contain at least two leaves", code="tree_format_error")
    # Validate and collect in one pass: a separate `any(...)` guard establishes the invariant
    # for a reader but not for the comprehension that follows, which then carries `str | None`.
    labels: dict[str, str] = {}
    for node in nodes:
        if node.kind != "leaf":
            continue
        if not isinstance(node.label, str):
            raise ClusterizerError("Every leaf must have a string label", code="tree_format_error")
        labels[node.id] = node.label
    root_edges = [edge for edge in edges if edge.source == root_id]
    if len(root_edges) != 2:
        raise ClusterizerError("Tree root must have exactly two children", code="tree_format_error")

    retained_nodes = [node_id for node_id in node_ids if node_id != root_id]
    index = {node_id: position for position, node_id in enumerate(retained_nodes)}
    graph_edges: list[tuple[int, int]] = []
    lengths: list[float] = []
    for edge in edges:
        source, target = edge.source, edge.target
        if source == root_id:
            continue
        if source not in index or target not in index:
            raise ClusterizerError("Tree edge references an unknown node", code="tree_format_error")
        graph_edges.append((index[source], index[target]))
        lengths.append(edge.length)
    left, right = root_edges
    graph_edges.append((index[left.target], index[right.target]))
    lengths.append(left.length + right.length)
    if any(not math.isfinite(length) for length in lengths):
        raise ClusterizerError("Branch lengths must be finite", code="tree_format_error")
    if len(graph_edges) != len(retained_nodes) - 1:
        raise ClusterizerError("Unrooted tree must have n-1 edges", code="tree_format_error")
    minimum = min(lengths)
    shift = -minimum + 1e-12 if minimum <= 0 else 0.0
    adjusted = [length + shift for length in lengths]
    if any(not math.isfinite(length) or length <= 0 for length in adjusted):
        raise ClusterizerError("Adjusted branch lengths must be positive", code="tree_format_error")
    graph = ig.Graph(n=len(retained_nodes), edges=graph_edges, directed=False)
    if not graph.is_connected():
        raise ClusterizerError("Tree graph is disconnected", code="tree_format_error")
    graph.vs["name"] = retained_nodes
    graph.es["weight"] = [1.0 / length for length in adjusted]
    return GraphInput(
        graph=graph,
        vertex_names=tuple(retained_nodes),
        object_ids=leaves,
        labels=labels,
        shift=shift,
    )


def load_tree_graph(path: Path) -> GraphInput:
    try:
        return _load_tree_graph(path)
    except ClusterizerError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ClusterizerError(
            "Tree artifact does not match schema version 1",
            code="tree_format_error",
        ) from exc
