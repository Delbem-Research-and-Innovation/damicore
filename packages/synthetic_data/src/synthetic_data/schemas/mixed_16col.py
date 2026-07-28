"""The ``mixed_16col`` synthetic dataset schema.

16 heterogeneous columns spanning naturals, signed integers, reals
(bounded/wide/scientific-magnitude), categoricals (low/high cardinality,
binary, near-constant), a sparse/missing-value numeric column, and free
text (short/long) — designed to exercise compression-based distance,
normalization, clustering, and tree-building under varied entropy,
cardinality, magnitude, and missing-data conditions.
"""

from __future__ import annotations

from synthetic_data import generators as gen
from synthetic_data.engine import ColumnSpec

WORDLIST: tuple[str, ...] = (
    "signal",
    "cluster",
    "vector",
    "matrix",
    "entropy",
    "sample",
    "sequence",
    "node",
    "edge",
    "graph",
    "kernel",
    "domain",
    "range",
    "weight",
    "bias",
    "layer",
    "batch",
    "epoch",
    "metric",
    "distance",
    "compress",
    "encode",
    "decode",
    "stream",
    "buffer",
    "token",
    "corpus",
    "shard",
    "record",
    "field",
    "table",
    "schema",
    "index",
    "query",
    "filter",
    "model",
    "feature",
    "label",
    "class",
    "score",
    "rank",
    "trend",
    "outlier",
    "anomaly",
    "baseline",
    "variance",
    "residual",
    "gradient",
    "threshold",
    "window",
    "cache",
    "queue",
    "stack",
    "tree",
    "branch",
    "leaf",
    "root",
    "path",
    "route",
    "region",
)

SKU_CODES: tuple[str, ...] = tuple(f"SKU-{i:04d}" for i in range(80))


def build_schema() -> list[ColumnSpec]:
    """Build a fresh ``mixed_16col`` schema.

    Returns a new list every call so stateful generators (e.g. the
    sequential ``row_id``) restart cleanly for each dataset generation.
    """
    return [
        ColumnSpec("row_id", gen.sequential_natural()),
        ColumnSpec("small_natural", gen.natural(0, 100)),
        ColumnSpec("large_natural", gen.natural(0, 10_000_000)),
        ColumnSpec("bounded_age", gen.natural(0, 120)),
        ColumnSpec("small_int", gen.integer(-50, 50)),
        ColumnSpec("wide_int", gen.integer(-1_000_000_000, 1_000_000_000)),
        ColumnSpec("probability_float", gen.real(0.0, 1.0, decimals=4)),
        ColumnSpec("wide_float", gen.real(-1_000_000.0, 1_000_000.0, decimals=3)),
        ColumnSpec("scientific_float", gen.scientific_real(1e-9, 1e9)),
        ColumnSpec(
            "status_categorical", gen.categorical(["active", "inactive", "pending", "archived"])
        ),
        ColumnSpec("sku_categorical", gen.categorical(SKU_CODES)),
        ColumnSpec("flag_categorical", gen.categorical(["yes", "no"])),
        ColumnSpec(
            "near_constant",
            gen.categorical(
                ["baseline", "alt_a", "alt_b", "alt_c"], weights=[0.95, 0.02, 0.02, 0.01]
            ),
        ),
        ColumnSpec(
            "sparse_numeric", gen.sparse(gen.real(0.0, 1000.0, decimals=2), missing_rate=0.15)
        ),
        ColumnSpec("free_text_short", gen.free_text(WORDLIST, 1, 6)),
        ColumnSpec("free_text_long", gen.free_text(WORDLIST, 15, 40, words_per_sentence=(6, 12))),
    ]
