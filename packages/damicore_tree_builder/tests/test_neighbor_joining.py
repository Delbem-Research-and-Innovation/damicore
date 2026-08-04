import json

import numpy as np
import pytest

from damicore_tree_builder import TreeBuilderError, build_tree, neighbor_joining
from damicore_tree_builder.newick import to_newick

pytestmark = pytest.mark.unit


def test_two_leaf_tree_preserves_half_distance():
    matrix = np.array([[0.0, 4.0], [4.0, 0.0]], dtype=np.float64)
    tree = neighbor_joining(matrix, ["a", "b"])
    assert [edge.length for edge in tree.edges] == [2.0, 2.0]
    assert tree.root_id == "nj_root"


def test_tie_break_and_path_api_are_deterministic(tmp_path):
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
    np.save(matrix_path, matrix, allow_pickle=False)
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


def test_invalid_matrices_are_rejected():
    with pytest.raises(TreeBuilderError):
        neighbor_joining(np.array([[0.0, np.nan], [np.nan, 0.0]]), ["a", "b"])
    with pytest.raises(TreeBuilderError):
        neighbor_joining(np.array([[0.0, 1.0], [2.0, 0.0]]), ["a", "b"])
    with pytest.raises(TreeBuilderError):
        neighbor_joining(np.zeros((2, 3), dtype=np.float64), ["a", "b"])
    with pytest.raises(TreeBuilderError):
        neighbor_joining(np.zeros((2, 2), dtype=np.float64), ["a", "a"])
    converted = neighbor_joining(np.zeros((2, 2), dtype=np.float32), ["a", "b"])
    assert converted.root_id == "nj_root"
    diagonal = np.zeros((2, 2), dtype=np.float64)
    diagonal[0, 0] = 1.0
    with pytest.raises(TreeBuilderError):
        neighbor_joining(diagonal, ["a", "b"])


def test_labels_artifact_and_newick_escaping(tmp_path):
    matrix = np.array([[0.0, 2.0], [2.0, 0.0]], dtype=np.float64)
    np.save(tmp_path / "distance.npy", matrix, allow_pickle=False)
    labels = tmp_path / "labels.json"
    labels.write_text("not-json", encoding="utf-8")
    with pytest.raises(TreeBuilderError, match="labels"):
        build_tree(tmp_path / "distance.npy", labels, tmp_path)
    tree = neighbor_joining(matrix, ["a space", "b"])
    assert "'a space'" in to_newick(tree)


def test_labels_schema_rejects_coercion_and_extra_fields(tmp_path):
    matrix = np.array([[0.0, 2.0], [2.0, 0.0]], dtype=np.float64)
    np.save(tmp_path / "distance.npy", matrix, allow_pickle=False)
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
