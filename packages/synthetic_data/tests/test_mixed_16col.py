import pytest

from synthetic_data.engine import generate_rows
from synthetic_data.schemas.mixed_16col import SKU_CODES, build_schema

EXPECTED_COLUMNS = [
    "row_id",
    "small_natural",
    "large_natural",
    "bounded_age",
    "small_int",
    "wide_int",
    "probability_float",
    "wide_float",
    "scientific_float",
    "status_categorical",
    "sku_categorical",
    "flag_categorical",
    "near_constant",
    "sparse_numeric",
    "free_text_short",
    "free_text_long",
]


@pytest.mark.unit
def test_schema_has_16_columns_with_expected_names() -> None:
    schema = build_schema()

    assert len(schema) == 16
    assert [column.name for column in schema] == EXPECTED_COLUMNS


@pytest.mark.unit
def test_generate_rows_yields_requested_row_count() -> None:
    schema = build_schema()

    rows = list(generate_rows(schema, n_rows=200, seed=1))

    assert len(rows) == 200
    assert all(set(row.keys()) == set(EXPECTED_COLUMNS) for row in rows)


@pytest.mark.unit
def test_row_id_is_sequential_starting_at_zero() -> None:
    schema = build_schema()

    rows = list(generate_rows(schema, n_rows=50, seed=1))

    assert [row["row_id"] for row in rows] == list(range(50))


@pytest.mark.unit
def test_natural_and_integer_columns_stay_in_bounds() -> None:
    schema = build_schema()

    rows = list(generate_rows(schema, n_rows=500, seed=2))

    for row in rows:
        assert 0 <= row["small_natural"] <= 100
        assert 0 <= row["large_natural"] <= 10_000_000
        assert 0 <= row["bounded_age"] <= 120
        assert -50 <= row["small_int"] <= 50
        assert -1_000_000_000 <= row["wide_int"] <= 1_000_000_000


@pytest.mark.unit
def test_float_columns_stay_in_bounds() -> None:
    schema = build_schema()

    rows = list(generate_rows(schema, n_rows=500, seed=3))

    for row in rows:
        assert 0.0 <= row["probability_float"] <= 1.0
        assert -1_000_000.0 <= row["wide_float"] <= 1_000_000.0
        magnitude = abs(row["scientific_float"])
        assert 1e-9 <= magnitude <= 1e9


@pytest.mark.unit
def test_categorical_columns_draw_from_expected_vocabularies() -> None:
    schema = build_schema()

    rows = list(generate_rows(schema, n_rows=1000, seed=4))

    assert {row["status_categorical"] for row in rows} <= {
        "active",
        "inactive",
        "pending",
        "archived",
    }
    assert {row["flag_categorical"] for row in rows} <= {"yes", "no"}
    assert {row["sku_categorical"] for row in rows} <= set(SKU_CODES)
    assert {row["near_constant"] for row in rows} <= {"baseline", "alt_a", "alt_b", "alt_c"}


@pytest.mark.unit
def test_near_constant_column_is_dominated_by_one_value() -> None:
    schema = build_schema()

    rows = list(generate_rows(schema, n_rows=2000, seed=5))
    values = [row["near_constant"] for row in rows]

    assert values.count("baseline") / len(values) > 0.85


@pytest.mark.unit
def test_sparse_numeric_column_has_missing_values() -> None:
    schema = build_schema()

    rows = list(generate_rows(schema, n_rows=2000, seed=6))
    missing_count = sum(1 for row in rows if row["sparse_numeric"] == "")

    assert 0 < missing_count / len(rows) < 0.30


@pytest.mark.unit
def test_free_text_columns_are_nonempty_and_within_word_counts() -> None:
    schema = build_schema()

    rows = list(generate_rows(schema, n_rows=200, seed=7))

    for row in rows:
        short_words = row["free_text_short"].split()
        assert 1 <= len(short_words) <= 6

        long_text = row["free_text_long"]
        assert long_text.endswith(".")
        long_words = long_text.replace(".", "").split()
        assert 15 <= len(long_words) <= 40


@pytest.mark.unit
def test_same_seed_produces_identical_rows() -> None:
    rows_a = list(generate_rows(build_schema(), n_rows=100, seed=42))
    rows_b = list(generate_rows(build_schema(), n_rows=100, seed=42))

    assert rows_a == rows_b


@pytest.mark.unit
def test_different_seeds_produce_different_rows() -> None:
    rows_a = list(generate_rows(build_schema(), n_rows=100, seed=42))
    rows_b = list(generate_rows(build_schema(), n_rows=100, seed=43))

    assert rows_a != rows_b
