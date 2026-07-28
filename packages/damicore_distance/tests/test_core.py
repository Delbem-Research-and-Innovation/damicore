import json
import pathlib

import numpy as np
import pytest

from damicore_distance.compressors import Compressor
from damicore_distance.core import (
    AlgorithmType,
    DistanceMatrixInput,
    DistanceMatrixOutput,
    MetricStrategy,
    StatusType,
    _ncd,  # pyright: ignore[reportPrivateUsage]
    compute_distance_matrix,
    ncd_matrix,
)


@pytest.mark.unit
def test_ncd_returns_zero_for_identical_sizes() -> None:
    assert _ncd(100, 100, 100) == 0.0


@pytest.mark.unit
def test_ncd_clamps_to_one_when_result_exceeds_range() -> None:
    assert _ncd(10, 10, 1000) == 1.0


@pytest.mark.unit
def test_ncd_clamps_to_zero_when_result_is_negative() -> None:
    assert _ncd(100, 100, 50) == 0.0


@pytest.mark.unit
def test_ncd_returns_zero_when_max_c_is_zero() -> None:
    assert _ncd(0, 0, 0) == 0.0


@pytest.mark.unit
def test_ncd_matrix_returns_n_by_n_symmetric_matrix(tmp_path: pathlib.Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"hello world" * 10)
    (tmp_path / "b.txt").write_bytes(b"hello earth" * 10)
    (tmp_path / "c.txt").write_bytes(b"x" * 100)

    matrix, filenames = ncd_matrix(str(tmp_path), Compressor.GZIP)

    assert matrix.shape == (3, 3)
    assert len(filenames) == 3
    np.testing.assert_array_equal(matrix, matrix.T)


@pytest.mark.unit
def test_ncd_matrix_diagonal_is_zero(tmp_path: pathlib.Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"hello world" * 10)
    (tmp_path / "b.txt").write_bytes(b"hello earth" * 10)

    matrix, _ = ncd_matrix(str(tmp_path), Compressor.GZIP)

    np.testing.assert_array_equal(np.diag(matrix), np.zeros(2, dtype=np.float32))


@pytest.mark.unit
def test_compute_distance_matrix_accepts_pydantic_input(tmp_path: pathlib.Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"hello world" * 10)
    (tmp_path / "b.txt").write_bytes(b"hello earth" * 10)
    output_path = str(tmp_path / "output.csv")

    input_contract = DistanceMatrixInput(
        input_directory=str(tmp_path),
        metric_strategy=MetricStrategy(
            algorithm=AlgorithmType.NCD,
            compressor=Compressor.GZIP,
        ),
        output_destination=output_path,
    )

    result = compute_distance_matrix(input_contract)

    assert isinstance(result, DistanceMatrixOutput)
    assert result.status == StatusType.SUCCESS
    assert result.total_files_analyzed == 2
    assert result.matrix_dimensions == "2x2"
    assert result.metric_used == AlgorithmType.NCD
    assert result.compressor_used == Compressor.GZIP
    assert result.output_file_path == output_path


@pytest.mark.unit
def test_compute_distance_matrix_accepts_json_string(tmp_path: pathlib.Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"hello world" * 10)
    (tmp_path / "b.txt").write_bytes(b"hello earth" * 10)
    output_path = str(tmp_path / "output.csv")

    json_input = json.dumps(
        {
            "input_directory": str(tmp_path),
            "metric_strategy": {
                "algorithm": "ncd",
                "compressor": "gzip",
                "compression_level": 9,
            },
            "output_destination": output_path,
        }
    )

    result = compute_distance_matrix(json_input)

    assert result.status == StatusType.SUCCESS


@pytest.mark.unit
def test_compute_distance_matrix_raises_for_unsupported_algorithm(tmp_path: pathlib.Path) -> None:
    strategy = MetricStrategy.model_construct(
        algorithm="unsupported_algo",  # type: ignore[arg-type]  # bypass Pydantic validation to reach the defensive case _ branch
        compressor=Compressor.GZIP,
        compression_level=9,
    )
    input_contract = DistanceMatrixInput.model_construct(
        input_directory=str(tmp_path),
        metric_strategy=strategy,
        output_destination=str(tmp_path / "out.csv"),
    )

    with pytest.raises(NotImplementedError):
        compute_distance_matrix(input_contract)
