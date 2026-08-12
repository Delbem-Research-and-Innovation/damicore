# Quickstart

For a notebook — Jupyter or Colab. The cells below use `%pip` and `display`, which
only a notebook defines. In a `.py` script use `pip install damicore`, `print`, and
put the `run` call under `if __name__ == "__main__":`, because the default worker
count opens a process pool whose workers re-import the calling module.

```python
%pip install damicore
```

Upload a CSV (or mount storage) and set its local path:

```python
csv_path = "/content/dataset.csv"
```

```python
from damicore import estimate, run

preview = estimate(csv_path, split="columns")
display(preview.model_dump())

result = run(csv_path, split="columns", output_dir="/content/damicore-run")
display(result.membership)
display(result.clusters)
print(result.tree_newick)
display(result.distance_matrix.head(10))
```

Optionally copy only verified, completed artifacts to a final empty directory:

```python
result.save("/content/drive/MyDrive/damicore-result")
result.close()
```

On Colab, keep active processing under `/content`; mounted Drive is better used
as the final destination. No repository checkout, `apt`, or `sys.path` change is
required.
