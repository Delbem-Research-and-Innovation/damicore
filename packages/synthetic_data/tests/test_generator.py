import csv
import zlib
from itertools import combinations
from pathlib import Path

import pytest

from synthetic_data import generate_csv

pytestmark = pytest.mark.unit


def _objects(path: Path, axis: str) -> list[bytes]:
    """Return the canonical bytes DAMICORE would compress: one object per column, or per row."""
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    body = rows[1:]
    if axis == "rows":
        return ["".join(row).encode("utf-8") for row in body]
    return ["".join(row[index] for row in body).encode("utf-8") for index in range(len(rows[0]))]


def _ncd(left: bytes, right: bytes) -> float:
    """Normalized Compression Distance, computed exactly as damicore_distance does it.

    Recomputed here from the standard library rather than imported: synthetic_data is test
    infrastructure and must not depend on a stage package.
    """

    def compressed(payload: bytes) -> int:
        stream = zlib.compressobj(level=6, wbits=31)
        return len(stream.compress(payload)) + len(stream.flush())

    cx, cy = compressed(left), compressed(right)
    return (compressed(left + right) - min(cx, cy)) / max(cx, cy)


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


# Both split modes are exercised: the generator must produce controllable groups of columns
# AND of rows, and the pipeline is run over both. The standard e2e fixture shape is included.
@pytest.mark.parametrize(
    ("axis", "rows", "columns", "clusters"),
    [
        pytest.param("columns", 24, 8, 2, id="columns-standard-e2e-fixture"),
        pytest.param("columns", 12, 6, 3, id="columns-three-groups"),
        pytest.param("rows", 24, 8, 2, id="rows-standard-e2e-fixture"),
        pytest.param("rows", 12, 6, 3, id="rows-three-groups"),
    ],
)
def test_cluster_members_are_measurably_closer_under_ncd(
    tmp_path: Path, axis: str, rows: int, columns: int, clusters: int
) -> None:
    """The fixture must carry structure the pipeline can actually recover, and NCD is how it
    looks. Asserting that group members merely share a label would certify a property no
    compressor can see -- which is what an earlier version of this test did, while the
    measured separation sat inside the noise.
    """
    path = generate_csv(
        tmp_path / "clustered.csv", rows=rows, columns=columns, clusters=clusters, seed=42
    )
    objects = _objects(path, axis)
    within = [
        _ncd(objects[i], objects[j])
        for i, j in combinations(range(len(objects)), 2)
        if i % clusters == j % clusters
    ]
    between = [
        _ncd(objects[i], objects[j])
        for i, j in combinations(range(len(objects)), 2)
        if i % clusters != j % clusters
    ]
    assert within and between
    assert max(within) < min(between)


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
