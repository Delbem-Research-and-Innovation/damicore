import csv
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

import damicore_clusterizer.api as api
import damicore_clusterizer.artifacts as artifacts
import damicore_clusterizer.tree_graph as tree_graph
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


# Each row breaks one clause of the tree contract and names the message that clause raises.
# The discriminator is what makes the row test the clause it is named for: without it every
# row asserts only "some ClusterizerError", and several would pass through a different guard
# entirely -- `duplicate-node` still raised with its own guard deleted, and the old
# `missing-edge` row popped a ROOT edge and so never reached the edge-count check at all.
TREE_CONTRACT_MUTATIONS: list[tuple[str, TreeMutation, str]] = [
    ("wrong-schema-version", lambda value: value.update(schema_version=2), "Invalid tree artifact"),
    ("unknown-root", lambda value: value.update(root_id="missing"), "root_id names no node"),
    (
        "duplicate-node",
        lambda value: value["nodes"].append(value["nodes"][0]),
        "node ids are not unique",
    ),
    (
        "unknown-node-kind",
        lambda value: value["nodes"][0].update(kind="unknown"),
        "Invalid tree artifact",
    ),
    (
        "root-as-leaf",
        lambda value: value["nodes"][-1].update(kind="leaf", label="root"),
        "Tree root must be internal",
    ),
    (
        "leaf-without-label",
        lambda value: value["nodes"][0].update(label=None),
        "Every leaf must have a string label",
    ),
    ("node-without-id", lambda value: value["nodes"][0].pop("id"), "Invalid tree artifact"),
    (
        "missing-non-root-edge",
        lambda value: value["edges"].pop(0),
        "Unrooted tree must have n-1 edges",
    ),
    (
        "missing-root-edge",
        lambda value: value["edges"].pop(),
        "Tree root must have exactly two children",
    ),
    (
        "non-finite-length",
        lambda value: value["edges"][0].update(length=float("nan")),
        "Invalid tree artifact",
    ),
    (
        "dangling-edge",
        lambda value: value["edges"][0].update(target="missing"),
        "Tree edge references an unknown node",
    ),
    ("extra-field", lambda value: value.update(unexpected=True), "Invalid tree artifact"),
    # Structural clauses the schema alone cannot express: they hold over the assembled graph,
    # after the root's two edges are merged into the single unrooted edge.
    ("fewer-than-two-leaves", _leave_one_leaf, "at least two leaves"),
    ("edge-count-not-n-minus-one", _add_redundant_edge, "Unrooted tree must have n-1 edges"),
    ("disconnected-graph", _strand_one_leaf, "Tree graph is disconnected"),
    ("root-merge-overflows-to-infinity", _overflow_root_merge, "Branch lengths must be finite"),
    (
        "shift-overflows-adjusted-length",
        _overflow_shift,
        "Adjusted branch lengths must be positive",
    ),
]


@pytest.mark.parametrize(
    ("mutation", "discriminator"),
    [(mutation, discriminator) for _, mutation, discriminator in TREE_CONTRACT_MUTATIONS],
    ids=[name for name, _, _ in TREE_CONTRACT_MUTATIONS],
)
def test_invalid_tree_contract_is_rejected(
    tmp_path: Path, mutation: TreeMutation, discriminator: str
) -> None:
    source = _tree(tmp_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    mutation(payload)
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ClusterizerError, match=discriminator):
        cluster_tree(source, tmp_path / "invalid")


def test_a_membership_that_misses_a_leaf_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every leaf must land in exactly one cluster. A membership shorter than the vertex list
    silently drops the trailing leaves, so the completeness check is the only thing standing
    between that and a membership.csv missing rows the caller asked for."""

    def truncated_membership(
        graph: object, num_clusters: int | None
    ) -> tuple[list[int], int, float]:
        return ([0, 0, 0], 1, 0.5)

    monkeypatch.setattr(api, "fastgreedy_membership", truncated_membership)
    with pytest.raises(ClusterizerError, match="incomplete") as raised:
        cluster_tree(_tree(tmp_path), tmp_path / "out")
    assert raised.value.code == "clusterization_error"


def test_an_unexpected_graph_failure_is_reported_as_a_tree_format_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load_tree_graph wraps the assembly step so a low-level failure from igraph or from
    float handling reaches the caller as this package's own typed error, never as a raw
    library exception the caller cannot classify."""

    def failing_graph(*args: object, **kwargs: object) -> object:
        raise TypeError("simulated igraph construction failure")

    monkeypatch.setattr(tree_graph.ig, "Graph", failing_graph)
    with pytest.raises(ClusterizerError, match="schema version 1") as raised:
        cluster_tree(_tree(tmp_path), tmp_path / "out")
    assert raised.value.code == "tree_format_error"


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


def test_an_unknown_configuration_field_is_rejected() -> None:
    """A misspelled option must fail rather than be dropped: ClusterConfig(num_cluster=3)
    silently clustering with the default is worse than not running at all."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ClusterConfig(num_cluster=3)  # pyright: ignore[reportCallIssue]


def test_the_root_is_removed_by_merging_its_two_edges(tmp_path: Path) -> None:
    """Specification 16.1: a degree-two root is not a real bifurcation, so its two edges
    become one edge between its children carrying the summed length, and every edge weight
    is the reciprocal of the shifted length. Both were unasserted while coverage read 100%."""
    graph_input = tree_graph.load_tree_graph(_tree(tmp_path))
    names = graph_input.vertex_names
    # igraph's edge list and attribute access are untyped in the shipped stubs; the casts
    # isolate that boundary rather than letting Unknown leak into the assertions.
    graph = cast(Any, graph_input.graph)
    lengths = {
        frozenset((names[int(edge.source)], names[int(edge.target)])): 1.0 / float(edge["weight"])
        for edge in graph.es
    }

    assert "nj_root" not in names
    shift = graph_input.shift
    # The fixture's root edges are 2.0 and 2.0, so the merged edge is 4.0 before the shift.
    assert lengths[frozenset(("i1", "i2"))] == pytest.approx(4.0 + shift)
    assert lengths[frozenset(("b", "i1"))] == pytest.approx(1.0 + shift)


def test_a_branch_far_below_zero_exhausts_the_shift_epsilon(tmp_path: Path) -> None:
    """Specification 16.1 fixes the shift as `-min + 1e-12`, an absolute epsilon. Once the
    minimum is large enough that 1e-12 falls below its ulp, the shifted minimum lands exactly
    on zero and a structurally valid tree is refused. This pins that boundary as the current
    contract; widening it means changing the formula the specification mandates.
    """
    payload = json.loads(_tree(tmp_path).read_text(encoding="utf-8"))
    payload["edges"][0].update(length=-1e5)
    source = tmp_path / "deep.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ClusterizerError, match="Adjusted branch lengths must be positive"):
        cluster_tree(source, tmp_path / "out")
