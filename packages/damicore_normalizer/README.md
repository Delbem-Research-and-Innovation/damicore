# damicore-normalizer

damicore-normalizer deterministically serializes the columns or rows of a local
CSV as canonical JSONL objects, recording the size and SHA-256 of every object.
It is the first stage of the DAMICORE pipeline; most users install the aggregate
`damicore` distribution, which runs all four stages end to end. Install this
package alone to normalize datasets without the rest of the pipeline.

```bash
pip install damicore-normalizer
```

## Python

```python
from damicore_normalizer import NormalizationConfig, normalize_csv

result = normalize_csv(
    "dataset.csv",
    "normalization",
    config=NormalizationConfig(split="columns", chunk_rows=50_000),
)
```

The call streams through `pandas.read_csv`, bounds open column files with an
LRU pool, and writes the objects plus a `manifest.json` into the output
directory. That normalization manifest is the input the sibling
`damicore-distance` distribution consumes to compute the NCD matrix.

## Links

- Repository: <https://github.com/Delbem-Research-and-Innovation/damicore>
- Issues: <https://github.com/Delbem-Research-and-Innovation/damicore/issues>
- Documentation:
  <https://github.com/Delbem-Research-and-Innovation/damicore/blob/main/docs/quickstart.md>

Licensed under Apache-2.0.
