# damicore-clusterizer

damicore-clusterizer clusters every node of a validated DAMICORE tree with
igraph FastGreedy and projects the resulting communities onto leaves. It is the
fourth and final stage of the DAMICORE pipeline; most users install the
aggregate `damicore` distribution, which runs all four stages end to end.
Install this package alone to cluster trees without the rest of the pipeline.

```bash
pip install damicore-clusterizer
```

## Python

```python
from damicore_clusterizer import ClusterConfig, cluster_tree

result = cluster_tree("tree.json", "run", config=ClusterConfig(num_clusters=None))
```

`tree.json` is produced by the sibling `damicore-tree-builder` distribution; the
call writes cluster membership as `membership.csv` and `clusters.json`. Negative
branch lengths receive one global shift, and output cluster IDs and leaf
ordering are deterministic.

## Links

- Repository: <https://github.com/Delbem-Research-and-Innovation/damicore>
- Issues: <https://github.com/Delbem-Research-and-Innovation/damicore/issues>
- Documentation:
  <https://github.com/Delbem-Research-and-Innovation/damicore/blob/main/docs/quickstart.md>

Licensed under Apache-2.0.
