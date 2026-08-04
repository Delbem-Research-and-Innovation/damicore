from __future__ import annotations

import csv
from pathlib import Path
from random import Random


def generate_csv(
    path: str | Path,
    *,
    rows: int,
    columns: int,
    clusters: int,
    seed: int,
    delimiter: str = ",",
) -> Path:
    """Generate a deterministic clustered CSV fixture without buffering all rows."""
    if rows < 1 or columns < 2 or clusters < 1:
        raise ValueError("rows and clusters must be positive; columns must be at least two")
    if clusters > min(rows, columns):
        raise ValueError("clusters cannot exceed rows or columns")
    if len(delimiter) != 1:
        raise ValueError("delimiter must contain exactly one character")

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rng = Random(seed)
    headers = [f"feature_{index + 1:06d}" for index in range(columns)]

    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=delimiter, lineterminator="\n")
        writer.writerow(headers)
        for row_index in range(rows):
            row_cluster = row_index % clusters
            writer.writerow(
                f"cluster_{(column_index % clusters + row_cluster) % clusters}:"
                f"{rng.randrange(10_000):04d}"
                for column_index in range(columns)
            )
    return destination.resolve()
