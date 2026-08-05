import csv
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import damicore_clusterizer.artifacts as artifacts
from damicore_clusterizer import ClusterConfig, ClusterizerError, cluster_tree

pytestmark = pytest.mark.unit


def _tree(tmp_path: Path) -> Path:
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


def test_fastgreedy_projects_every_leaf_deterministically(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    first = cluster_tree(tree, tmp_path / "one", config=ClusterConfig(num_clusters=2))
    second = cluster_tree(tree, tmp_path / "two", config=ClusterConfig(num_clusters=2))
    assert first.community_count == 2
    assert first.clusters_path.read_bytes() == second.clusters_path.read_bytes()
    with first.membership_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["object_id"] for row in rows] == ["a", "b", "c", "d"]
    assert sorted({int(row["cluster"]) for row in rows}) == list(range(first.cluster_count))


def test_one_global_shift_lifts_the_most_negative_branch_above_zero(tmp_path: Path) -> None:
    """The fixture's lowest branch is -0.5, so the shift must clear zero by the smallest
    margin the implementation needs. The exact epsilon is not part of the contract."""
    result = cluster_tree(_tree(tmp_path), tmp_path / "shifted")
    assert result.branch_length_shift > 0.5
    assert result.branch_length_shift == pytest.approx(0.5, abs=1e-6)


def test_an_occupied_output_directory_is_rejected(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    cluster_tree(tree, tmp_path / "one", config=ClusterConfig(num_clusters=2))
    with pytest.raises(ClusterizerError, match="already exist"):
        cluster_tree(tree, tmp_path / "one", config=ClusterConfig(num_clusters=2))


def test_an_automatic_cut_yields_at_least_one_community(tmp_path: Path) -> None:
    automatic = cluster_tree(_tree(tmp_path), tmp_path / "automatic")
    assert automatic.community_count >= 1


def test_more_requested_clusters_than_leaves_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ClusterizerError, match="leaf count"):
        cluster_tree(
            _tree(tmp_path),
            tmp_path / "too-many",
            config=ClusterConfig(num_clusters=5),
        )


# Each row breaks one clause of the tree contract. The ids name the clause, so a regression
# reports which part of the schema stopped being enforced instead of an opaque index.
# JSON payloads are dynamic by nature, hence the Any in the mutation signature.
TreeMutation = Callable[[dict[str, Any]], object]


def _leave_one_leaf(value: dict[str, Any]) -> None:
    """Demote every leaf but the first, so the graph carries fewer than two objects."""
    for node in value["nodes"][1:4]:
        node.update(kind="internal")


def _add_redundant_edge(value: dict[str, Any]) -> None:
    """An extra edge breaks the n-1 count that makes the graph a tree."""
    value["edges"].append({"source": "i1", "target": "c", "length": 1.0})


def _strand_one_leaf(value: dict[str, Any]) -> None:
    """Point i2's second edge back at c, leaving d isolated while the edge count still
    equals n-1 -- the one shape that reaches the connectivity check rather than the count."""
    value["edges"][3].update(target="c")


def _overflow_root_merge(value: dict[str, Any]) -> None:
    """The root's two branches are summed into one edge, and that sum can leave float range
    even though each operand is finite, so the schema's allow_inf_nan=False cannot catch it."""
    value["edges"][4].update(length=1e308)
    value["edges"][5].update(length=1e308)


def _overflow_shift(value: dict[str, Any]) -> None:
    """A hugely negative branch forces a shift so large that adding it to the largest branch
    overflows, which the post-shift finiteness check exists to catch."""
    value["edges"][0].update(length=-1e308)
    value["edges"][1].update(length=1e308)


TREE_CONTRACT_MUTATIONS: list[tuple[str, TreeMutation]] = [
    ("wrong-schema-version", lambda value: value.update(schema_version=2)),
    ("unknown-root", lambda value: value.update(root_id="missing")),
    ("duplicate-node", lambda value: value["nodes"].append(value["nodes"][0])),
    ("unknown-node-kind", lambda value: value["nodes"][0].update(kind="unknown")),
    ("root-as-leaf", lambda value: value["nodes"][-1].update(kind="leaf", label="root")),
    ("leaf-without-label", lambda value: value["nodes"][0].update(label=None)),
    ("node-without-id", lambda value: value["nodes"][0].pop("id")),
    ("missing-edge", lambda value: value["edges"].pop()),
    ("non-finite-length", lambda value: value["edges"][0].update(length=float("nan"))),
    ("dangling-edge", lambda value: value["edges"][0].update(target="missing")),
    ("extra-field", lambda value: value.update(unexpected=True)),
    # Structural clauses the schema alone cannot express: they hold over the assembled graph,
    # after the root's two edges are merged into the single unrooted edge.
    ("fewer-than-two-leaves", _leave_one_leaf),
    ("edge-count-not-n-minus-one", _add_redundant_edge),
    ("disconnected-graph", _strand_one_leaf),
    ("root-merge-overflows-to-infinity", _overflow_root_merge),
    ("shift-overflows-adjusted-length", _overflow_shift),
]


@pytest.mark.parametrize(
    "mutation",
    [mutation for _, mutation in TREE_CONTRACT_MUTATIONS],
    ids=[name for name, _ in TREE_CONTRACT_MUTATIONS],
)
def test_invalid_tree_contract_is_rejected(tmp_path: Path, mutation: TreeMutation) -> None:
    source = _tree(tmp_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    mutation(payload)
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ClusterizerError):
        cluster_tree(source, tmp_path / "invalid")


# Both artifacts are written through their own temporary file, so each rename is a separate
# place a partial file could survive a failure. The index selects which one fails.
@pytest.mark.parametrize(
    "failing_rename",
    [pytest.param(1, id="membership-csv"), pytest.param(2, id="clusters-json")],
)
def test_a_failed_artifact_write_leaves_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failing_rename: int
) -> None:
    renames = 0
    real_replace = os.replace

    def counting_replace(src: object, dst: object) -> None:
        nonlocal renames
        renames += 1
        if renames == failing_rename:
            raise OSError("simulated failure while committing an artifact")
        real_replace(src, dst)  # pyright: ignore[reportArgumentType]

    monkeypatch.setattr(artifacts.os, "replace", counting_replace)
    output = tmp_path / "out"
    with pytest.raises(OSError):
        cluster_tree(_tree(tmp_path), output)

    assert not list(output.glob(".membership.*"))
    assert not list(output.glob(".clusters.json.*"))


def test_invalid_json_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text("nope", encoding="utf-8")
    with pytest.raises(ClusterizerError):
        cluster_tree(source, tmp_path / "invalid")
