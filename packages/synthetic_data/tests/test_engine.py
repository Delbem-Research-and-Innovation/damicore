import csv
from pathlib import Path

import pytest

from synthetic_data.engine import ColumnSpec, write_csv
from synthetic_data.generators import natural


@pytest.mark.unit
def test_write_csv_creates_parent_directories_and_header(tmp_path: Path) -> None:
    schema = [ColumnSpec("value", natural(0, 10))]
    output_path = tmp_path / "nested" / "out.csv"

    write_csv(schema, n_rows=5, seed=1, output_path=output_path)

    assert output_path.exists()
    with output_path.open(encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        assert reader.fieldnames == ["value"]
        rows = list(reader)

    assert len(rows) == 5
    assert all(0 <= int(row["value"]) <= 10 for row in rows)
