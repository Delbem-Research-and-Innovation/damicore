"""Generic schema-driven dataset generation engine.

A schema is a sequence of :class:`ColumnSpec`. Feeding a schema, a row
count, and a seed into :func:`generate_rows` (or :func:`write_csv`) is the
one axis every synthetic dataset is built from — a new dataset is a new
schema, never new engine code.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import Any

from synthetic_data.generators import Generator


@dataclass(frozen=True)
class ColumnSpec:
    """One column: its name and the generator producing its values."""

    name: str
    generator: Generator


def generate_rows(schema: Sequence[ColumnSpec], n_rows: int, seed: int) -> Iterator[dict[str, Any]]:
    """Yield ``n_rows`` dicts keyed by column name, from one seeded RNG."""
    rng = Random(seed)
    for _ in range(n_rows):
        yield {column.name: column.generator(rng) for column in schema}


def write_csv(schema: Sequence[ColumnSpec], n_rows: int, seed: int, output_path: Path) -> None:
    """Generate ``n_rows`` rows from ``schema``/``seed`` and write them as CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [column.name for column in schema]
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in generate_rows(schema, n_rows, seed):
            writer.writerow(row)
