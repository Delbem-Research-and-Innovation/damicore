import csv
from pathlib import Path

import pytest

from synthetic_data import generate_csv

pytestmark = pytest.mark.unit


def _column_label_patterns(path: Path, delimiter: str = ",") -> list[tuple[str, ...]]:
    """Return each column's sequence of cluster labels, header excluded."""
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream, delimiter=delimiter))
    body = rows[1:]
    return [tuple(row[index].split(":")[0] for row in body) for index in range(len(rows[0]))]


def test_generate_csv_is_streaming_and_deterministic(tmp_path: Path) -> None:
    first = generate_csv(tmp_path / "first.csv", rows=20, columns=5, clusters=2, seed=17)
    second = generate_csv(tmp_path / "second.csv", rows=20, columns=5, clusters=2, seed=17)
    different = generate_csv(tmp_path / "different.csv", rows=20, columns=5, clusters=2, seed=18)

    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() != different.read_bytes()
    assert len(first.read_text(encoding="utf-8").splitlines()) == 21


# Each row is one dimension constraint the generator must enforce, so a regression names the
# constraint it broke instead of failing an opaque loop at its first bad case.
@pytest.mark.parametrize(
    ("rows", "columns", "clusters"),
    [
        pytest.param(0, 2, 1, id="no-rows"),
        pytest.param(2, 1, 1, id="one-column"),
        pytest.param(2, 2, 0, id="no-clusters"),
        pytest.param(2, 2, 3, id="more-clusters-than-rows"),
    ],
)
def test_generate_csv_rejects_invalid_dimensions(
    tmp_path: Path, rows: int, columns: int, clusters: int
) -> None:
    with pytest.raises(ValueError):
        generate_csv(tmp_path / "bad.csv", rows=rows, columns=columns, clusters=clusters, seed=1)


@pytest.mark.parametrize(
    ("columns", "clusters"),
    [
        pytest.param(6, 3, id="six-columns-three-clusters"),
        pytest.param(8, 2, id="the-standard-e2e-fixture-shape"),
        pytest.param(5, 1, id="single-cluster-degenerates-to-one-group"),
    ],
)
def test_generated_columns_form_exactly_the_requested_cluster_groups(
    tmp_path: Path, columns: int, clusters: int
) -> None:
    """The generator exists to produce data with findable structure, so the fixture must
    actually carry it: columns split into exactly `clusters` groups by their label sequence,
    and columns an exact multiple of `clusters` apart belong to the same group. Determinism
    alone would still hold for structureless noise, so it cannot stand in for this."""
    path = generate_csv(
        tmp_path / "clustered.csv", rows=12, columns=columns, clusters=clusters, seed=42
    )
    patterns = _column_label_patterns(path)

    assert len(set(patterns)) == clusters
    for index in range(columns):
        assert patterns[index] == patterns[index % clusters]


def test_generate_csv_rejects_a_multi_character_delimiter(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        generate_csv(
            tmp_path / "bad.csv",
            rows=2,
            columns=2,
            clusters=1,
            seed=1,
            delimiter="::",
        )
