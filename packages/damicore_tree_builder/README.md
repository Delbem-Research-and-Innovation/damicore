# damicore-tree-builder

Builds a Neighbor-Joining tree from a distance matrix CSV file and writes it
as Newick. Third stage of the [DAMICORE](../../README.md) pipeline.

## Install

```bash
pip install damicore-tree-builder
```

## Usage

```python
from damicore_tree_builder import run

report = run(input_path="distance_matrix.csv", output_path="tree.nwk")
```

A CLI is also available:

```bash
damicore-tree-builder --input distance_matrix.csv --output tree.nwk
```

This package has no dependency on any other `damicore-*` package.
