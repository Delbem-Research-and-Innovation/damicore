import json
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest

from damicore_tree_builder import Tree, TreeBuilderError, build_tree, neighbor_joining
from damicore_tree_builder.newick import to_newick

pytestmark = pytest.mark.unit


def test_two_leaf_tree_preserves_half_distance() -> None:
    matrix = np.array([[0.0, 4.0], [4.0, 0.0]], dtype=np.float64)
    tree = neighbor_joining(matrix, ["a", "b"])
    assert [edge.length for edge in tree.edges] == [2.0, 2.0]
    assert tree.root_id == "nj_root"


# The additive five-taxon matrix of Saitou and Nei. Neighbor Joining is exact on an additive
# matrix, so this fixture pins the Q criterion, the delta split and the d(u,k) update at once:
# a wrong formula changes the topology, a branch length, or both.
ADDITIVE_LABELS = ["a", "b", "c", "d", "e"]
ADDITIVE_MATRIX = np.array(
    [
        [0.0, 5.0, 9.0, 9.0, 8.0],
        [5.0, 0.0, 10.0, 10.0, 9.0],
        [9.0, 10.0, 0.0, 8.0, 7.0],
        [9.0, 10.0, 8.0, 0.0, 3.0],
        [8.0, 9.0, 7.0, 3.0, 0.0],
    ],
    dtype=np.float64,
)
ADDITIVE_EDGES = [
    ("nj_000001", "a", 2.0),
    ("nj_000001", "b", 3.0),
    ("nj_000002", "c", 4.0),
    ("nj_000002", "nj_000001", 3.0),
    ("nj_000003", "d", 2.0),
    ("nj_000003", "e", 1.0),
    ("nj_root", "nj_000002", 1.0),
    ("nj_root", "nj_000003", 1.0),
]


def _leaf_path_length(tree: Tree, source: str, target: str) -> float:
    incident: dict[str, list[tuple[str, float]]] = {}
    for edge in tree.edges:
        incident.setdefault(edge.source, []).append((edge.target, edge.length))
        incident.setdefault(edge.target, []).append((edge.source, edge.length))
    pending = [(source, 0.0, "")]
    while pending:
        node, walked, previous = pending.pop()
        if node == target:
            return walked
        pending.extend(
            (neighbor, walked + length, node)
            for neighbor, length in incident[node]
            if neighbor != previous
        )
    raise AssertionError(f"{source} and {target} are not connected")


def test_additive_matrix_yields_the_expected_topology_and_branch_lengths() -> None:
    tree = neighbor_joining(ADDITIVE_MATRIX, ADDITIVE_LABELS)
    assert [(edge.source, edge.target, edge.length) for edge in tree.edges] == ADDITIVE_EDGES
    assert [node.id for node in tree.nodes] == [
        *ADDITIVE_LABELS,
        "nj_000001",
        "nj_000002",
        "nj_000003",
        "nj_root",
    ]


def test_additive_matrix_is_reconstructed_exactly_by_path_sums() -> None:
    """The independent check on the fixture above: on an additive matrix every leaf-to-leaf
    path in the result must sum back to the input distance with no floating-point slack."""
    tree = neighbor_joining(ADDITIVE_MATRIX, ADDITIVE_LABELS)
    for left in range(len(ADDITIVE_LABELS)):
        for right in range(left + 1, len(ADDITIVE_LABELS)):
            walked = _leaf_path_length(tree, ADDITIVE_LABELS[left], ADDITIVE_LABELS[right])
            assert walked == float(ADDITIVE_MATRIX[left, right])


def test_negative_branch_length_is_preserved_through_every_artifact(tmp_path: Path) -> None:
    """Specification section 15.2: a negative length is a real Neighbor Joining outcome on a
    non-additive matrix and is reported, never truncated to zero."""
    matrix = np.array([[0.0, 1.0, 1.0], [1.0, 0.0, 10.0], [1.0, 10.0, 0.0]], dtype=np.float64)
    ids = ["a", "b", "c"]
    tree = neighbor_joining(matrix, ids)
    assert [edge.length for edge in tree.edges if edge.target == "a"] == [-4.0]
    assert "a:-4.0" in to_newick(tree)

    matrix_path = tmp_path / "distance.npy"
    np.save(matrix_path, matrix, allow_pickle=False)  # pyright: ignore[reportUnknownMemberType]
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(
        json.dumps({"schema_version": 1, "object_ids": ids, "labels": ids}),
        encoding="utf-8",
    )
    result = build_tree(matrix_path, labels_path, tmp_path)
    assert result.negative_branch_count == 1
    persisted = json.loads(result.tree_path.read_text(encoding="utf-8"))
    assert [edge for edge in persisted["edges"] if edge["length"] < 0] == [
        {"source": "nj_000001", "target": "a", "length": -4.0}
    ]
    assert "a:-4.0" in result.newick_path.read_text(encoding="utf-8")


def test_tie_break_and_path_api_are_deterministic(tmp_path: Path) -> None:
    matrix = np.array(
        [
            [0.0, 5.0, 9.0, 9.0],
            [5.0, 0.0, 10.0, 10.0],
            [9.0, 10.0, 0.0, 8.0],
            [9.0, 10.0, 8.0, 0.0],
        ],
        dtype=np.float64,
    )
    ids = ["a", "b", "c", "d"]
    in_memory = neighbor_joining(matrix, ids)
    matrix_path = tmp_path / "distance.npy"
    np.save(matrix_path, matrix, allow_pickle=False)  # pyright: ignore[reportUnknownMemberType]
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(
        json.dumps({"schema_version": 1, "object_ids": ids, "labels": ids}),
        encoding="utf-8",
    )
    result = build_tree(matrix_path, labels_path, tmp_path)
    persisted = json.loads(result.tree_path.read_text(encoding="utf-8"))
    assert persisted == in_memory.model_dump(mode="json")
    assert result.newick_path.read_text(encoding="utf-8").strip().endswith(";")
    assert not (tmp_path / "tree-work.npy").exists()
    with pytest.raises(TreeBuilderError, match="already exist"):
        build_tree(matrix_path, labels_path, tmp_path)


# Each row is one property a distance matrix must have. Keeping them separate means a
# regression names the property that broke rather than stopping at the first bad matrix.
def _matrix(rows: list[list[float]]) -> npt.NDArray[np.float64]:
    return np.array(rows, dtype=np.float64)


@pytest.mark.parametrize(
    ("matrix", "labels"),
    [
        pytest.param(_matrix([[0.0, float("nan")], [float("nan"), 0.0]]), ["a", "b"], id="nan"),
        pytest.param(_matrix([[0.0, 1.0], [2.0, 0.0]]), ["a", "b"], id="asymmetric"),
        pytest.param(_matrix([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]), ["a", "b"], id="not-square"),
        pytest.param(_matrix([[0.0, 1.0], [1.0, 0.0]]), ["a", "a"], id="duplicate-labels"),
        pytest.param(_matrix([[1.0, 1.0], [1.0, 0.0]]), ["a", "b"], id="non-zero-diagonal"),
    ],
)
def test_invalid_matrix_is_rejected(matrix: npt.NDArray[np.float64], labels: list[str]) -> None:
    with pytest.raises(TreeBuilderError):
        neighbor_joining(matrix, labels)


def test_a_float32_matrix_is_converted_rather_than_rejected() -> None:
    converted = neighbor_joining(np.zeros((2, 2), dtype=np.float32), ["a", "b"])
    assert converted.root_id == "nj_root"


def test_labels_artifact_and_newick_escaping(tmp_path: Path) -> None:
    matrix = np.array([[0.0, 2.0], [2.0, 0.0]], dtype=np.float64)
    np.save(tmp_path / "distance.npy", matrix, allow_pickle=False)  # pyright: ignore[reportUnknownMemberType]
    labels = tmp_path / "labels.json"
    labels.write_text("not-json", encoding="utf-8")
    with pytest.raises(TreeBuilderError, match="labels"):
        build_tree(tmp_path / "distance.npy", labels, tmp_path)
    tree = neighbor_joining(matrix, ["a space", "b"])
    assert "'a space'" in to_newick(tree)


def test_labels_schema_rejects_coercion_and_extra_fields(tmp_path: Path) -> None:
    matrix = np.array([[0.0, 2.0], [2.0, 0.0]], dtype=np.float64)
    np.save(tmp_path / "distance.npy", matrix, allow_pickle=False)  # pyright: ignore[reportUnknownMemberType]
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "object_ids": [1, "b"],
                "labels": ["a", "b"],
                "unexpected": True,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(TreeBuilderError, match="labels"):
        build_tree(tmp_path / "distance.npy", labels, tmp_path / "tree-output")
