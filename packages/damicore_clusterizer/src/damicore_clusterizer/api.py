from __future__ import annotations

import time
from pathlib import Path

from damicore_clusterizer.artifacts import write_cluster_artifacts
from damicore_clusterizer.config import ClusterConfig
from damicore_clusterizer.errors import ClusterizerError
from damicore_clusterizer.fastgreedy import fastgreedy_membership
from damicore_clusterizer.models import ClusterResult
from damicore_clusterizer.tree_graph import load_tree_graph


def cluster_tree(
    tree_path: str | Path,
    output_dir: str | Path,
    *,
    config: ClusterConfig | None = None,
) -> ClusterResult:
    """Cluster every node in an unrooted tree and project communities to leaves."""
    started = time.monotonic()
    settings = config or ClusterConfig()
    source = load_tree_graph(Path(tree_path).resolve())
    if settings.num_clusters is not None and settings.num_clusters > len(source.object_ids):
        raise ClusterizerError(
            "num_clusters cannot exceed the leaf count", code="configuration_error"
        )
    membership, community_count, modularity = fastgreedy_membership(
        source.graph,
        settings.num_clusters,
    )
    names = list(source.graph.vs["name"])
    raw_leaf_groups: dict[int, list[str]] = {}
    for vertex_index, community in enumerate(membership):
        name = str(names[vertex_index])
        if name in source.object_ids:
            raw_leaf_groups.setdefault(int(community), []).append(name)
    ordered_groups = sorted(
        (tuple(sorted(group)) for group in raw_leaf_groups.values() if group),
        key=lambda group: group,
    )
    cluster_for = {
        object_id: cluster for cluster, group in enumerate(ordered_groups) for object_id in group
    }
    if set(cluster_for) != set(source.object_ids):
        raise ClusterizerError("Cluster membership is incomplete", code="clusterization_error")

    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "membership.csv").exists() or (destination / "clusters.json").exists():
        raise ClusterizerError(
            "Cluster outputs already exist without a reusable receipt",
            code="output_directory_conflict_error",
        )
    membership_path, clusters_path = write_cluster_artifacts(
        destination,
        source.object_ids,
        source.labels,
        cluster_for,
        ordered_groups,
    )
    return ClusterResult(
        membership_path=membership_path,
        clusters_path=clusters_path,
        community_count=community_count,
        cluster_count=len(ordered_groups),
        modularity=modularity,
        branch_length_shift=source.shift,
        timing=time.monotonic() - started,
    )
