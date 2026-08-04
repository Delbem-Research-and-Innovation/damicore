# synthetic-data

Workspace-only deterministic fixture generator. It is not a runtime dependency
and must never be published.

```python
from synthetic_data import generate_csv

generate_csv("fixture.csv", rows=1_000, columns=16, clusters=4, seed=42)
```
