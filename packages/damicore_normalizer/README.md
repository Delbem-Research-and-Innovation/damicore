# damicore-normalizer

Deterministically serialize CSV columns or rows as canonical JSONL objects.

```python
from damicore_normalizer import NormalizationConfig, normalize_csv

result = normalize_csv(
    "dataset.csv",
    "normalization",
    config=NormalizationConfig(split="columns", chunk_rows=50_000),
)
```

The package streams through `pandas.read_csv`, bounds open column files with
an LRU pool, and records the size and SHA-256 of every object.
