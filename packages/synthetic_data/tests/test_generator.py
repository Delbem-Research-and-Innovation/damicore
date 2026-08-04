import pytest

from synthetic_data import generate_csv


def test_generate_csv_is_streaming_and_deterministic(tmp_path):
    first = generate_csv(tmp_path / "first.csv", rows=20, columns=5, clusters=2, seed=17)
    second = generate_csv(tmp_path / "second.csv", rows=20, columns=5, clusters=2, seed=17)
    different = generate_csv(tmp_path / "different.csv", rows=20, columns=5, clusters=2, seed=18)

    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() != different.read_bytes()
    assert len(first.read_text(encoding="utf-8").splitlines()) == 21


def test_generate_csv_validates_dimensions(tmp_path):
    for arguments in (
        {"rows": 0, "columns": 2, "clusters": 1},
        {"rows": 2, "columns": 1, "clusters": 1},
        {"rows": 2, "columns": 2, "clusters": 0},
    ):
        try:
            generate_csv(tmp_path / "bad.csv", seed=1, **arguments)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid dimensions must fail")
    with pytest.raises(ValueError):
        generate_csv(tmp_path / "bad.csv", rows=2, columns=2, clusters=3, seed=1)
    with pytest.raises(ValueError):
        generate_csv(
            tmp_path / "bad.csv",
            rows=2,
            columns=2,
            clusters=1,
            seed=1,
            delimiter="::",
        )
