from __future__ import annotations

import csv
import math
from collections.abc import Generator
from pathlib import Path
from typing import Any, TypedDict

DistanceMatrix = list[list[float]]


class TreeNode(TypedDict):
    name: str | None
    branch_length: float
    children: list[TreeNode]


def _build_success_report(
    input_path: Path,
    output_path: Path,
    total_leaf_nodes: int,
    total_internal_nodes: int,
) -> dict[str, Any]:
    return {
        "status": "success",
        "distance_matrix_path": str(input_path),
        "tree_format": "newick",
        "total_leaf_nodes": total_leaf_nodes,
        "total_internal_nodes": total_internal_nodes,
        "output_file_path": str(output_path),
    }


def run(input_path: str, output_path: str) -> dict[str, Any]:
    """Load a distance matrix, build an NJ tree, and write it to a Newick file.

    Parameters
    ----------
    input_path : str
        Path to the input distance matrix CSV file.
    output_path : str
        Destination path for the output Newick file.

    Returns
    -------
    dict[str, Any]
        Report with keys ``status``, ``distance_matrix_path``,
        ``tree_format``, ``total_leaf_nodes``, ``total_internal_nodes``,
        and ``output_file_path``.

    Raises
    ------
    FileNotFoundError
        If ``input_path`` does not exist.
    ValueError
        If the CSV is invalid or the matrix cannot be used for NJ.
    """
    input_file_path = Path(input_path)

    names, matrix = load_distance_matrix(input_path)
    tree = build_neighbor_joining_tree(names, matrix)
    generated_path = write_newick(tree, output_path)

    return _build_success_report(
        input_path=input_file_path,
        output_path=generated_path,
        total_leaf_nodes=len(get_terminals(tree)),
        total_internal_nodes=len(get_nonterminals(tree)),
    )


def load_distance_matrix(input_path: str) -> tuple[list[str], DistanceMatrix]:
    """Load and validate a distance matrix from a CSV file.

    Parameters
    ----------
    input_path : str
        Path to the CSV file. The first row and column must be label headers;
        the matrix body must be numeric, square, symmetric, and have zeros on
        the diagonal.

    Returns
    -------
    tuple[list[str], DistanceMatrix]
        Ordered label names and the corresponding distance matrix.

    Raises
    ------
    FileNotFoundError
        If ``input_path`` does not exist.
    ValueError
        If the CSV is malformed, non-numeric, non-square, asymmetric,
        contains negative values, a non-zero diagonal, or duplicate labels.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    rows = _read_csv_rows(path)
    names, matrix = _parse_csv_rows(rows, path)
    _validate_distance_matrix(names, matrix)

    return names, matrix


def _read_csv_rows(path: Path) -> list[list[str]]:
    try:
        with path.open(newline="", encoding="utf-8") as csv_file:
            return list(csv.reader(csv_file))
    except csv.Error as exc:
        raise ValueError(f"Could not parse CSV file: {path}") from exc


def _parse_csv_rows(rows: list[list[str]], path: Path) -> tuple[list[str], DistanceMatrix]:
    if not rows:
        raise ValueError(f"Input CSV file is empty: {path}")

    header = rows[0]
    if len(header) < 2:
        raise ValueError("Distance matrix header must contain at least one label.")

    column_labels = header[1:]
    row_labels: list[str] = []
    matrix: DistanceMatrix = []

    for row_number, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            raise ValueError(
                "Distance matrix rows must have the same number of columns as the header. "
                f"Row {row_number} has {len(row)} columns, expected {len(header)}."
            )

        row_labels.append(row[0])
        try:
            matrix.append([float(value) for value in row[1:]])
        except ValueError as exc:
            raise ValueError("Distance matrix contains non-numeric values.") from exc

    if row_labels != column_labels:
        raise ValueError("Row labels and column labels must match and appear in the same order.")

    return row_labels, matrix


def _validate_distance_matrix(names: list[str], matrix: DistanceMatrix) -> None:
    if not names or not matrix:
        raise ValueError("Distance matrix is empty.")

    if len(set(names)) != len(names):
        raise ValueError("Distance matrix contains duplicated labels.")

    rows = len(matrix)
    columns = {len(row) for row in matrix}
    if len(columns) != 1 or rows != len(names) or columns.pop() != len(names):
        raise ValueError("Distance matrix must be square.")

    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            if value < 0:
                raise ValueError("Distance matrix cannot contain negative values.")

            if row_index == column_index and not math.isclose(value, 0.0, abs_tol=1e-9):
                raise ValueError("Distance matrix diagonal must contain only zeros.")

            transposed_value = matrix[column_index][row_index]
            if not math.isclose(value, transposed_value, rel_tol=1e-9, abs_tol=1e-12):
                raise ValueError("Distance matrix must be symmetric.")


def build_neighbor_joining_tree(names: list[str], matrix: DistanceMatrix) -> TreeNode:
    """Build a Neighbor-Joining phylogenetic tree from a distance matrix.

    Parameters
    ----------
    names : list[str]
        Unique ordered labels corresponding to matrix rows and columns.
    matrix : DistanceMatrix
        Square, symmetric distance matrix with zeros on the diagonal.

    Returns
    -------
    TreeNode
        Root of the unrooted NJ tree. Leaf ``branch_length`` values are
        set; the root's ``branch_length`` is 0.

    Raises
    ------
    ValueError
        If ``names`` has fewer than 3 elements, contains duplicates, or does
        not match the shape of ``matrix``.
    """
    _validate_neighbor_joining_input(names, matrix)

    active_nodes: list[str] = list(names)
    clades: dict[str, TreeNode] = {name: _leaf_node(name) for name in names}
    distances = _initial_distances(names, matrix)
    next_internal_id = 1

    while len(active_nodes) > 2:
        left, right = _select_pair(active_nodes, distances)
        new_node = f"Inner{next_internal_id}"
        next_internal_id += 1

        left_length, right_length = _branch_lengths(left, right, active_nodes, distances)
        clades[left]["branch_length"] = left_length
        clades[right]["branch_length"] = right_length
        clades[new_node] = _internal_node([clades[left], clades[right]])

        for other in active_nodes:
            if other == left or other == right:
                continue
            distances[frozenset((new_node, other))] = (
                _distance(left, other, distances)
                + _distance(right, other, distances)
                - _distance(left, right, distances)
            ) / 2.0

        active_nodes = [node for node in active_nodes if node != left and node != right]
        active_nodes.append(new_node)

    left, right = active_nodes
    final_distance = _distance(left, right, distances) / 2.0
    clades[left]["branch_length"] = final_distance
    clades[right]["branch_length"] = final_distance

    return _internal_node([clades[left], clades[right]])


def _validate_neighbor_joining_input(names: list[str], matrix: DistanceMatrix) -> None:
    if not names:
        raise ValueError("The names list cannot be empty.")

    if len(set(names)) != len(names):
        raise ValueError("The names list cannot contain duplicates.")

    if not matrix:
        raise ValueError("The distance matrix cannot be empty.")

    if len(names) != len(matrix):
        raise ValueError("The number of names must match the number of matrix rows.")

    for row in matrix:
        if len(row) != len(names):
            raise ValueError("The distance matrix must be square and match the number of names.")

    if len(names) < 3:
        raise ValueError("Neighbor-Joining requires at least 3 elements to build a tree.")


def _leaf_node(name: str) -> TreeNode:
    return TreeNode(name=name, branch_length=0.0, children=[])


def _internal_node(children: list[TreeNode]) -> TreeNode:
    return TreeNode(name=None, branch_length=0.0, children=children)


def _initial_distances(names: list[str], matrix: DistanceMatrix) -> dict[frozenset[str], float]:
    distances: dict[frozenset[str], float] = {}
    for row_index, left in enumerate(names):
        for column_index, right in enumerate(names):
            if row_index < column_index:
                distances[frozenset((left, right))] = float(matrix[row_index][column_index])
    return distances


def _select_pair(
    active_nodes: list[str], distances: dict[frozenset[str], float]
) -> tuple[str, str]:
    node_count = len(active_nodes)
    total_distances = {
        node: sum(_distance(node, other, distances) for other in active_nodes if other != node)
        for node in active_nodes
    }

    best_pair: tuple[str, str] | None = None
    best_score: float | None = None
    for left_index, left in enumerate(active_nodes):
        for right in active_nodes[left_index + 1 :]:
            score = (
                (node_count - 2) * _distance(left, right, distances)
                - total_distances[left]
                - total_distances[right]
            )
            if best_score is None or score < best_score:
                best_score = score
                best_pair = (left, right)

    if best_pair is None:
        raise ValueError("Could not select a pair for Neighbor-Joining.")
    return best_pair


def _branch_lengths(
    left: str,
    right: str,
    active_nodes: list[str],
    distances: dict[frozenset[str], float],
) -> tuple[float, float]:
    node_count = len(active_nodes)
    left_total = sum(_distance(left, other, distances) for other in active_nodes if other != left)
    right_total = sum(
        _distance(right, other, distances) for other in active_nodes if other != right
    )
    pair_distance = _distance(left, right, distances)
    delta = (left_total - right_total) / (node_count - 2)

    return (pair_distance + delta) / 2.0, (pair_distance - delta) / 2.0


def _distance(left: str, right: str, distances: dict[frozenset[str], float]) -> float:
    if left == right:
        return 0.0
    return distances[frozenset((left, right))]


def write_newick(tree: TreeNode, output_path: str) -> Path:
    """Serialize a tree to a Newick file.

    Parameters
    ----------
    tree : TreeNode
        Root node of the tree to serialize.
    output_path : str
        Destination file path; parent directories are created if needed.

    Returns
    -------
    Path
        Resolved path of the written file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_newick(tree), encoding="utf-8")
    return path


def to_newick(tree: TreeNode) -> str:
    """Serialize a tree to a Newick-format string.

    Parameters
    ----------
    tree : TreeNode
        Root node of the tree to serialize.

    Returns
    -------
    str
        Newick string terminated with ``";\\n"``.
    """
    return f"{_format_clade(tree)};\n"


def _format_clade(clade: TreeNode) -> str:
    label = _escape_label(clade["name"]) if clade["name"] is not None else ""
    length = f":{clade['branch_length']:.10g}"

    children = clade["children"]
    if children:
        inner = ",".join(_format_clade(child) for child in children)
        return f"({inner}){label}{length}"

    return f"{label}{length}"


def _escape_label(name: str) -> str:
    if name and all(character not in name for character in " \t\n\r():;,[]'"):
        return name
    return "'" + name.replace("'", "''") + "'"


def get_terminals(tree: TreeNode) -> list[TreeNode]:
    """Return all leaf nodes in the tree.

    Parameters
    ----------
    tree : TreeNode
        Root node to traverse.

    Returns
    -------
    list[TreeNode]
        Nodes with no children, in pre-order.
    """
    return [node for node in _walk_tree(tree) if not node["children"]]


def get_nonterminals(tree: TreeNode) -> list[TreeNode]:
    """Return all internal nodes in the tree.

    Parameters
    ----------
    tree : TreeNode
        Root node to traverse.

    Returns
    -------
    list[TreeNode]
        Nodes with at least one child, in pre-order.
    """
    return [node for node in _walk_tree(tree) if node["children"]]


def _walk_tree(node: TreeNode) -> Generator[TreeNode, None, None]:
    yield node
    for child in node["children"]:
        yield from _walk_tree(child)
