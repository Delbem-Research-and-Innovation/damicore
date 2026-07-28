import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from damicore_tree_builder.cli import app

runner = CliRunner()


@pytest.mark.unit
def test_build_command_creates_newick_file_and_reports_success(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    matrix_path.write_text(
        ",A,B,C\nA,0,5,9\nB,5,0,10\nC,9,10,0\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "tree.nwk"

    # Typer collapses a single-command app onto the app itself (verified this
    # session via the real console script), so no "build" subcommand token
    # is needed — confirmed via `damicore-tree-builder --help`.
    result = runner.invoke(
        app,
        ["--input", str(matrix_path), "--output", str(output_path)],
    )

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["status"] == "success"
    assert output_path.exists()


@pytest.mark.unit
def test_build_command_reports_error_for_missing_input(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"
    output_path = tmp_path / "tree.nwk"

    result = runner.invoke(
        app,
        ["--input", str(missing_path), "--output", str(output_path)],
    )

    assert result.exit_code == 1
    report = json.loads(result.stdout)
    assert report["status"] == "error"
    assert not output_path.exists()
