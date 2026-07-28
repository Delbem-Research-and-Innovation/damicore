# damicore-distance

Computes a Normalized Compression Distance (NCD) matrix for a directory of
files. Second stage of the [DAMICORE](../../README.md) pipeline.

## Install

```bash
pip install damicore-distance
```

## Usage

```python
from damicore_distance import DistanceMatrixInput, MetricStrategy, compute_distance_matrix

result = compute_distance_matrix(
    DistanceMatrixInput(
        input_directory="normalized/",
        metric_strategy=MetricStrategy(
            algorithm="ncd",
            compressor="gzip",
            compression_level=9,
        ),
        output_destination="distance_matrix.csv",
    )
)
```

This package has no dependency on any other `damicore-*` package.
