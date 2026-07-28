# damicore

Pipeline orchestrator that sequences the `damicore_*` packages: normalizer →
distance → tree_builder (clusterizer not wired in yet — see below).

## Install

```bash
pip install damicore
```

## Usage

```python
from damicore.pipeline import run_pipeline

result = run_pipeline(
    {
        "normalizer": {
            "source_file_path": "raw.csv",
            "split_strategy": {
                "type": "composite_keys",
                "key_columns": ["cod_distr", "ano", "Idade"],
                "content_columns": ["sexo", "populacao", "regiao"],
            },
            "output_folder_name": "normalized",
        },
        "distance_metric_strategy": {
            "algorithm": "ncd",
            "compressor": "gzip",
            "compression_level": 9,
        },
        "distance_output_path": "distance_matrix.csv",
        "tree_output_path": "tree.nwk",
    }
)
```

## Scope

This package holds no domain logic. It only depends on
[`damicore-normalizer`](../damicore_normalizer), [`damicore-distance`](../damicore_distance)
and [`damicore-tree-builder`](../damicore_tree_builder), and wires their public
contracts together. The `damicore-clusterizer` stage is not yet integrated —
that package has no public API to call.

If you only need one stage, install that package directly (e.g.
`pip install damicore-distance`) instead of the full pipeline.
