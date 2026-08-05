# damicore-tree-builder

Build a deterministic Neighbor Joining tree from `distance.npy` and
`labels.json`.

```python
from damicore_tree_builder import build_tree

result = build_tree("distance.npy", "labels.json", "run")
```

The path API copies into a temporary memory map, reuses slots, evaluates Q
pairwise without materializing it, preserves negative branches, and writes
`tree.json` plus Newick. `neighbor_joining(matrix, labels)` is available for
small matrices.
