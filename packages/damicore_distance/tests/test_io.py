import csv
import pathlib

import numpy as np
import pytest

from damicore_distance.io import export_ncd_to_csv, get_file_data, get_files_from_directory


@pytest.mark.unit
def test_get_files_from_directory_returns_filenames(tmp_path: pathlib.Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"aaa")
    (tmp_path / "b.txt").write_bytes(b"bbb")

    result = get_files_from_directory(str(tmp_path))

    assert set(result) == {"a.txt", "b.txt"}


@pytest.mark.unit
def test_get_files_from_directory_raises_for_nonexistent_path() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        get_files_from_directory("/nonexistent/path/that/does/not/exist")


@pytest.mark.unit
def test_get_file_data_returns_bytes(tmp_path: pathlib.Path) -> None:
    file = tmp_path / "sample.bin"
    file.write_bytes(b"hello world")

    assert get_file_data(str(file)) == b"hello world"


@pytest.mark.unit
def test_get_file_data_raises_for_nonexistent_file() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        get_file_data("/nonexistent/file.txt")


@pytest.mark.unit
def test_export_ncd_to_csv_writes_correct_headers_and_values(tmp_path: pathlib.Path) -> None:
    matrix = np.array([[0.0, 0.5], [0.5, 0.0]], dtype=np.float32)
    filenames = ["a.txt", "b.txt"]
    output_path = str(tmp_path / "matrix.csv")

    export_ncd_to_csv(matrix, filenames, output_path)

    with open(output_path) as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["", "a.txt", "b.txt"]
    assert rows[1][0] == "a.txt"
    assert rows[2][0] == "b.txt"
    assert float(rows[1][2]) == 0.5
    assert float(rows[2][1]) == 0.5


@pytest.mark.unit
def test_export_ncd_to_csv_creates_intermediate_directories(tmp_path: pathlib.Path) -> None:
    matrix = np.array([[0.0]], dtype=np.float32)
    output_path = str(tmp_path / "nested" / "deep" / "matrix.csv")

    export_ncd_to_csv(matrix, ["a.txt"], output_path)

    assert pathlib.Path(output_path).exists()
