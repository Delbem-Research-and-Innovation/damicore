# synthetic-data

**Internal-only tool.** Generates synthetic CSV datasets used to validate and
test the other DAMICORE packages (`damicore_distance`, `damicore_normalizer`,
`damicore_tree_builder`, `damicore_clusterizer`, `damicore`). It is:

- not published to PyPI,
- not a runtime dependency of any `damicore-*` package,
- never imported by any package's build — only used ad hoc from the CLI to
  produce fixtures for local/manual testing.

## Usage

```bash
uv run synthetic-data --rows 30000 --seed 42
# writes to .temp/synthetic_data/mixed_16col.csv (gitignored) by default
```

```bash
uv run synthetic-data --rows 30000 --seed 42 --output /path/to/out.csv
```

## Dataset: `mixed_16col`

16 heterogeneous columns designed to exercise compression-based distance,
normalization, clustering, and tree-building on varied entropy, cardinality,
magnitude, and missing-data conditions:

| # | Column              | Type                    | Notes                                   |
|---|---------------------|-------------------------|------------------------------------------|
| 1 | `row_id`            | natural, sequential      | 0..n-1                                   |
| 2 | `small_natural`      | natural                  | uniform [0, 100]                         |
| 3 | `large_natural`      | natural                  | uniform [0, 10,000,000]                  |
| 4 | `bounded_age`        | natural                  | uniform [0, 120]                         |
| 5 | `small_int`          | signed int               | uniform [-50, 50]                        |
| 6 | `wide_int`           | signed int               | uniform [-1e9, 1e9]                      |
| 7 | `probability_float`  | real                     | uniform [0.0, 1.0], 4 decimals           |
| 8 | `wide_float`         | real                     | uniform [-1e6, 1e6]                      |
| 9 | `scientific_float`   | real                     | log-uniform magnitude [1e-9, 1e9], signed|
| 10| `status_categorical` | categorical (low card.)  | 4 fixed values                           |
| 11| `sku_categorical`    | categorical (high card.) | ~80 distinct tokens                      |
| 12| `flag_categorical`   | categorical (binary)     | yes/no                                   |
| 13| `near_constant`      | categorical (low entropy)| ~95% one repeated value                  |
| 14| `sparse_numeric`     | numeric, sparse          | ~15% empty cells                         |
| 15| `free_text_short`    | free text                | 1-6 words                                |
| 16| `free_text_long`     | free text                | 15-40 words, pseudo-sentences            |

Every generator draws from a single seeded `random.Random`, so the same
`--seed` always reproduces byte-identical output.
