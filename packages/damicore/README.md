# damicore

Install the complete DAMICORE 0.1 pipeline:

```bash
pip install damicore
```

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

The `damicore` command exposes matching `estimate` and `run` subcommands. Only
this aggregate distribution has a CLI; stage distributions are Python APIs.
