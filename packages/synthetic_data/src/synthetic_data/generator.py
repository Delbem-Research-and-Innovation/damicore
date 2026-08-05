from __future__ import annotations

import csv
from pathlib import Path
from random import Random
from string import ascii_lowercase

# Characters of shared, cluster-specific text per cell, against two characters of noise.
# The ratio is the point: DAMICORE separates objects by compressed size, so members of a
# cluster have to share actual content. An earlier form gave every cluster the same alphabet
# and differed only by rotating it, which left the signal inside the noise -- measured gzip
# NCD on the standard 24x8 fixture put same-group columns at 0.5689 and different-group at
# 0.5744, so the pipeline could not have recovered the groups the generator claimed.
_TOKEN_LENGTH = 24


def _cluster_token(axis: str, cluster: int) -> str:
    """Return a long string unique to (axis, cluster), stable across calls and platforms."""
    generator = Random(f"{axis}-{cluster}")
    return "".join(generator.choice(ascii_lowercase) for _ in range(_TOKEN_LENGTH))


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
    # Each cell carries its column's token and its row's token. A column then shares content
    # with every column congruent to it mod `clusters`, and likewise for rows, so both split
    # modes have structure a compressor can actually find. Making the cluster a function of
    # (column + row) instead would put every cluster's text in every column, separable only
    # by phase -- which compression does not see.
    column_tokens = [_cluster_token("column", cluster) for cluster in range(clusters)]
    row_tokens = [_cluster_token("row", cluster) for cluster in range(clusters)]

    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=delimiter, lineterminator="\n")
        writer.writerow(headers)
        for row_index in range(rows):
            row_token = row_tokens[row_index % clusters]
            writer.writerow(
                f"{column_tokens[column_index % clusters]}{row_token}{rng.randrange(100):02d}"
                for column_index in range(columns)
            )
    return destination.resolve()
