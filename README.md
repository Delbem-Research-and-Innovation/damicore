# DAMICORE

DAMICORE is a compression-based data analysis pipeline, split into four
independent packages plus a thin orchestrator:

| Package | Responsibility | Install |
|---|---|---|
| [`damicore-normalizer`](packages/damicore_normalizer) | Splits a raw dataset into per-column content files | `pip install damicore-normalizer` |
| [`damicore-distance`](packages/damicore_distance) | Computes a Normalized Compression Distance (NCD) matrix | `pip install damicore-distance` |
| [`damicore-tree-builder`](packages/damicore_tree_builder) | Builds a Neighbor-Joining tree from a distance matrix | `pip install damicore-tree-builder` |
| [`damicore-clusterizer`](packages/damicore_clusterizer) | Clustering stage (placeholder, not yet implemented) | `pip install damicore-clusterizer` |
| [`damicore`](packages/damicore) | Orchestrates the stages above into a single pipeline | `pip install damicore` |

## Design

- **Independent by default.** Each `damicore-*` package has its own version,
  its own dependencies, and zero imports from its siblings. They communicate
  through typed data contracts (function inputs/outputs), not shared code.
  Install only the package you need.
- **`damicore` is additive.** It depends on the four packages above and
  exposes `damicore.pipeline.run_pipeline`, which sequences them. It exists
  for consumers who want the full pipeline in one `pip install`; it does not
  change how the individual packages are consumed.

## Repository layout

This is a single repository containing all five packages as independent,
separately publishable distributions, managed as a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/):
one shared lockfile/virtual environment for development, five independent
packages for consumption.

## Development

```bash
make install   # sync the workspace + install git hooks
make check     # lint + type-check every package
make test      # run every package's test suite
```

Each package also has its own `Makefile` with the same `dev`/`check`/`test`/`clean`
targets, runnable from inside `packages/<name>/`.
