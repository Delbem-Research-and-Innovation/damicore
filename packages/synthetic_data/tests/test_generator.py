from pathlib import Path

import pytest

from synthetic_data import generate_csv

pytestmark = pytest.mark.unit


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
