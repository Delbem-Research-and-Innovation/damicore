# damicore

DAMICORE clusters the rows or columns of a local CSV without asking you to pick a
feature representation or a number of clusters. It serializes each object
canonically, measures every pair with exact Normalized Compression Distance (NCD),
builds a deterministic Neighbor Joining tree, and cuts communities out of that tree
with FastGreedy.

This distribution is the complete pipeline and the only one with a command line.
The four stage distributions — `damicore-normalizer`, `damicore-distance`,
`damicore-tree-builder`, `damicore-clusterizer` — are Python APIs that can be
installed and used on their own.

```bash
pip install damicore
```

## Python

```python
from damicore import ExecutionConfig, ResourceLimits, estimate, load_result, run

# `workers="auto"` opens a process pool whose workers re-import the calling module, so in a
# `.py` script this call must sit under the guard below. A notebook or REPL satisfies it too.
if __name__ == "__main__":
    preview = estimate("dataset.csv", split="columns")
    result = run(
        "dataset.csv",
        split="columns",
        execution=ExecutionConfig(workers="auto", limits=ResourceLimits()),
    )
    result.membership
    result.distance_matrix.head()
    result.close()

    restored = load_result(result.artifacts.run_dir)
```

`estimate` reports the exact cost of a run — objects, pairs, matrix bytes, working
memory, free disk — without creating anything. Call it before raising a limit.

## Command line

```bash
damicore estimate dataset.csv --json
damicore run dataset.csv --split columns --output-dir ./results
damicore --version
```

Progress and the artifact paths go to stderr. Only `estimate --json` writes to
stdout, so a shell pipeline reads one JSON document and nothing else.

### Exit codes

A failure is also one JSON line on stderr carrying a stable `code`, so a script can
branch on the status and log the reason.

| Status | Meaning |
|---:|---|
| 0 | Completed |
| 2 | Configuration or input rejected, including a malformed CSV |
| 3 | A resource limit would be exceeded |
| 4 | An artifact failed validation |
| 5 | The output directory conflicts, or a checkpoint does not match |
| 130 | Interrupted; the run is resumable |

## Results

A run writes a versioned, hash-verified directory: the distance matrix as a
`float64` `.npy` memory map, the tree as JSON and Newick, cluster membership as CSV
and JSON, plus a manifest and a report. `load_result` reopens it, and an
interrupted run resumes from its checkpoints to the same bytes a fresh run would
have produced.

## Scale

The exact algorithm accepts at most 1,000 objects, 500,000 pairs and 512 MiB per
matrix by default. A multi-gigabyte CSV with tens of columns is feasible; the same
file split into millions of rows is rejected during preflight rather than after
hours of work. Streaming and memory maps bound RAM, but NCD stays quadratic and
Neighbor Joining cubic in the object count. Raise an individual `ResourceLimits`
field only after reading `estimate`.

## Links

- Source, issues and full documentation:
  <https://github.com/Delbem-Research-and-Innovation/damicore>
- Licensed under Apache-2.0.
