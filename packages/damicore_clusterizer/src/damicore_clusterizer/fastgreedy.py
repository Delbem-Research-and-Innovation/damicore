from __future__ import annotations

from typing import Any

import igraph as ig


def fastgreedy_membership(
    graph: ig.Graph,
    num_clusters: int | None,
) -> tuple[list[int], int, float]:
    dendrogram = graph.community_fastgreedy(weights="weight")
    clustering: Any = (
        dendrogram.as_clustering()
        if num_clusters is None
        else dendrogram.as_clustering(n=num_clusters)
    )
    return (
        [int(value) for value in clustering.membership],
        len(clustering),
        float(clustering.modularity),
    )
