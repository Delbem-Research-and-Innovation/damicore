# damicore-clusterizer

Cluster every node of a validated DAMICORE tree with igraph FastGreedy and
project the resulting communities onto leaves.

```python
from damicore_clusterizer import ClusterConfig, cluster_tree

result = cluster_tree("tree.json", "run", config=ClusterConfig(num_clusters=None))
```

Negative branch lengths receive one global shift. Output cluster IDs and leaf
ordering are deterministic.
