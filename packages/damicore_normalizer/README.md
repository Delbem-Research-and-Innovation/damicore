# damicore-normalizer

Splits a raw dataset into per-column content files, keyed by a composite key
strategy. First stage of the [DAMICORE](../../README.md) pipeline.

## Install

```bash
pip install damicore-normalizer
```

## Usage

```python
from damicore_normalizer import normalize_dataset

result = normalize_dataset(
    {
        "source_file_path": "raw.csv",
        "split_strategy": {
            "type": "composite_keys",
            "key_columns": ["cod_distr", "ano", "Idade"],
            "content_columns": ["sexo", "populacao"],
        },
        "output_folder_name": "normalized",
    }
)
```

This package has no dependency on any other `damicore-*` package.
