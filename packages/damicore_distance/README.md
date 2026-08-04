# damicore-distance

Compute an exact, unclamped, float64 NCD matrix from a normalization manifest.

```python
from damicore_distance import DistanceConfig, compute_distance_matrix

result = compute_distance_matrix(
    "normalization/manifest.json",
    "run",
    config=DistanceConfig(compressor="zlib", workers="auto"),
)
```

Compression is incremental, pairs are lexicographically sharded, only the
coordinator writes the memory map, and compatible completed shards can resume.
