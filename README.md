# DAMICORE 0.1

DAMICORE clusters the rows or columns of a local CSV through canonical
serialization, exact Normalized Compression Distance (NCD), deterministic
Neighbor Joining, and FastGreedy community detection.

```bash
pip install damicore
```

```python
from damicore import estimate, run

# The default worker count opens a process pool, and each worker re-imports the calling
# module. In a `.py` script the call must therefore sit under this guard. A notebook or REPL
# also satisfies it, so the guard is safe everywhere; `ExecutionConfig(workers=1)` avoids the
# pool entirely.
if __name__ == "__main__":
    preview = estimate("dataset.csv", split="columns")
    print(preview.model_dump())

    result = run("dataset.csv", split="columns")
    print(result.membership)
    print(result.clusters)
    print(result.tree_newick)
    print(result.distance_matrix.head())
    result.close()
```

The default exact algorithm accepts at most 1,000 objects, 500,000 pairs, and
512 MiB per matrix. A multi-gigabyte CSV with tens of columns can be feasible;
the same file split into millions of rows is intentionally rejected during
preflight. Streaming and memory maps bound RAM, but NCD remains quadratic and
Neighbor Joining cubic in the object count. Raise individual `ResourceLimits`
only after reviewing `estimate`.

Runs are content-addressed, checkpointed, resumable, and verified before they
become `completed`. Internal paths are contained in the run directory, JSON
writes are atomic, and completed artifacts are hash-checked by `load_result`.
See [quickstart](docs/quickstart.md), [CSV contract](docs/csv-contract.md),
[artifact contract](docs/artifacts.md), and [scalability](docs/scalability.md).

The five public distributions are `damicore`, `damicore-normalizer`,
`damicore-distance`, `damicore-tree-builder`, and `damicore-clusterizer`.
Stage packages do not import one another. `synthetic-data` is workspace-only
and is never published.

For Colab, process and checkpoint on local `/content`, then use `result.save`
to copy completed artifacts to a mounted Drive destination. DAMICORE never
imports `google.colab`, accesses the network, or uploads data.

## Development

```bash
make install
make check
make test
make build
```

Python 3.11–3.14 is supported. The normative contract is
[`DAMICORE_IMPLEMENTATION_SPECIFICATION.md`](DAMICORE_IMPLEMENTATION_SPECIFICATION.md).
