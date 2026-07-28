import csv
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from synthetic_data.cli import app

runner = CliRunner()


@pytest.mark.unit
def test_generate_writes_requested_rows_and_reports_success(tmp_path: Path) -> None:
    output_path = tmp_path / "out.csv"

    result = runner.invoke(
        app,
        ["--rows", "10", "--seed", "1", "--output", str(output_path)],
    )

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["status"] == "success"
    assert report["rows"] == 10
    assert report["columns"] == 16
    assert output_path.exists()

    with output_path.open(encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert len(rows) == 10


@pytest.mark.unit
def test_generate_defaults_to_temp_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["--rows", "3", "--seed", "1"])

    assert result.exit_code == 0
    assert (tmp_path / ".temp" / "synthetic_data" / "mixed_16col.csv").exists()
