import csv
import json

import pytest

from damicore_clusterizer import ClusterConfig, ClusterizerError, cluster_tree

pytestmark = pytest.mark.unit


def _tree(tmp_path):
    path = tmp_path / "tree.json"
    payload = {
        "schema_version": 1,
        "root_id": "nj_root",
        "nodes": [
            {"id": "a", "kind": "leaf", "label": "A"},
            {"id": "b", "kind": "leaf", "label": "B"},
            {"id": "c", "kind": "leaf", "label": "C"},
            {"id": "d", "kind": "leaf", "label": "D"},
            {"id": "i1", "kind": "internal", "label": None},
            {"id": "i2", "kind": "internal", "label": None},
            {"id": "nj_root", "kind": "internal", "label": None},
        ],
        "edges": [
            {"source": "i1", "target": "a", "length": -0.5},
            {"source": "i1", "target": "b", "length": 1.0},
            {"source": "i2", "target": "c", "length": 1.0},
            {"source": "i2", "target": "d", "length": 1.0},
            {"source": "nj_root", "target": "i1", "length": 2.0},
            {"source": "nj_root", "target": "i2", "length": 2.0},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_fastgreedy_projects_every_leaf_deterministically(tmp_path):
    tree = _tree(tmp_path)
    first = cluster_tree(tree, tmp_path / "one", config=ClusterConfig(num_clusters=2))
    second = cluster_tree(tree, tmp_path / "two", config=ClusterConfig(num_clusters=2))
    assert first.community_count == 2
    assert first.branch_length_shift == 0.500000000001
    assert first.clusters_path.read_bytes() == second.clusters_path.read_bytes()
    with pytest.raises(ClusterizerError, match="already exist"):
        cluster_tree(tree, tmp_path / "one", config=ClusterConfig(num_clusters=2))
    with first.membership_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["object_id"] for row in rows] == ["a", "b", "c", "d"]
    assert sorted({int(row["cluster"]) for row in rows}) == list(range(first.cluster_count))


def test_automatic_cut_and_invalid_requested_count(tmp_path):
    automatic = cluster_tree(_tree(tmp_path), tmp_path / "automatic")
    assert automatic.community_count >= 1
    with pytest.raises(ClusterizerError, match="leaf count"):
        cluster_tree(
            _tree(tmp_path),
            tmp_path / "too-many",
            config=ClusterConfig(num_clusters=5),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(schema_version=2),
        lambda value: value.update(root_id="missing"),
        lambda value: value["nodes"].append(value["nodes"][0]),
        lambda value: value["nodes"][0].update(kind="unknown"),
        lambda value: value["nodes"][-1].update(kind="leaf", label="root"),
        lambda value: value["nodes"][0].update(label=None),
        lambda value: value["nodes"][0].pop("id"),
        lambda value: value["edges"].pop(),
        lambda value: value["edges"][0].update(length=float("nan")),
        lambda value: value["edges"][0].update(target="missing"),
        lambda value: value.update(unexpected=True),
    ],
)
def test_invalid_tree_contracts_fail(tmp_path, mutation):
    source = _tree(tmp_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    mutation(payload)
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ClusterizerError):
        cluster_tree(source, tmp_path / "invalid")


def test_invalid_json_fails(tmp_path):
    source = tmp_path / "bad.json"
    source.write_text("nope", encoding="utf-8")
    with pytest.raises(ClusterizerError):
        cluster_tree(source, tmp_path / "invalid")
