import os
from enum import StrEnum

import numpy as np
from pydantic import BaseModel, Field

from damicore_distance.compressors import Compressor, get_compressed_size
from damicore_distance.io import (
    export_ncd_to_csv,
    get_file_data,
    get_files_from_directory,
)


def _ncd(cx: int, cy: int, cxy: int) -> float:
    """Calculate Normalized Compression Distance (NCD).

    Parameters
    ----------
    cx : int
        Compressed size of file x.
    cy : int
        Compressed size of file y.
    cxy : int
        Compressed size of concatenated files x and y.

    Returns
    -------
    float
        NCD value between 0 and 1, where lower values indicate higher similarity.
    """
    max_c = max(cx, cy)
    ncd = (cxy - min(cx, cy)) / max_c if max_c != 0 else 0

    return max(0.0, min(1.0, ncd))


def ncd_matrix(
    input_dir: str, compressor: Compressor, compression_level: int = 9
) -> tuple[np.ndarray, list[str]]:
    """Compute the NCD distance matrix for all files in a directory.

    Parameters
    ----------
    input_dir : str
        Path to the directory containing the files to be compared.
    compressor : Compressor
        The compressor object/enum used to calculate compressed sizes.
    compression_level : int, default=9
        The compression level to be applied (1-9).

    Returns
    -------
        tuple[np.ndarray, list[str]]
            A tuple containing the NCD distance matrix and the list of
            filenames corresponding to the rows/columns of the matrix.
    """
    filenames = sorted(get_files_from_directory(input_dir))
    files = [os.path.join(input_dir, f) for f in filenames]
    n = len(files)

    matrix = np.zeros((n, n), dtype=np.float32)

    x_sizes = [
        get_compressed_size(get_file_data(file), compressor, compression_level) for file in files
    ]

    for x in range(n):
        for y in range(x + 1, n):
            file_x, file_y = files[x], files[y]
            c_xy = get_compressed_size(
                get_file_data(file_x) + get_file_data(file_y),
                compressor,
                compression_level,
            )

            ncd = _ncd(x_sizes[x], x_sizes[y], c_xy)
            matrix[x][y] = ncd
            matrix[y][x] = ncd

    return matrix, filenames


class AlgorithmType(StrEnum):
    NCD = "ncd"


class MetricStrategy(BaseModel):
    """Defines the strategy for computing the distance matrix.

    Attributes
    ----------
    algorithm : AlgorithmType
        The algorithm to be used for computing the distance matrix (e.g., NCD).
    compressor : Compressor
        The compressor to be used for computing the compressed sizes of files.
    compression_level : int
        The compression level to be used by the compressor, an integer
        between 1 and 9, where higher values indicates better compression.
    """

    algorithm: AlgorithmType
    compressor: Compressor
    compression_level: int = Field(default=9, ge=1, le=9)


class DistanceMatrixInput(BaseModel):
    """Input contract for computing distance matrix.

    Attributes
    ----------
    input_directory : str
        The directory containing the files to be compared.
    metric_strategy : MetricStrategy
        The strategy to be used for calculating the distance matrix,
        including the algorithm, compressor, and compression level.
    output_destination : str
        The destination where the resulting distance matrix will be stored.
    """

    input_directory: str
    metric_strategy: MetricStrategy
    output_destination: str


class StatusType(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class DistanceMatrixOutput(BaseModel):
    """
    Output contract for distance matrix computation results.

    Attributes
    ----------
    status : StatusType
        The status of the distance matrix computation (e.g., "success", "error").
    input_directory : str
        The directory that was analyzed for distance matrix computation.
    total_files_analyzed : int
        The total number of files that were analyzed in the input directory.
    matrix_dimensions : str
        The dimensions of the computed distance matrix (N x N),
        excluding CSV headers/indices (e.g., "10x10").
    metric_used : str
        The metric/algorithm used for computing the distance matrix (e.g., "NCD").
    compressor_used : str
        The compressor used for computing the compressed sizes (e.g., "gzip").
    output_file_path : str
        The file path where the resulting distance matrix was stored.
    """

    status: StatusType
    input_directory: str
    total_files_analyzed: int
    matrix_dimensions: str
    metric_used: str
    compressor_used: str
    output_file_path: str


def compute_distance_matrix(
    input_contract: DistanceMatrixInput | str,
) -> DistanceMatrixOutput:
    """Compute the distance matrix based on the provided input contract.

    The input can be either a JSON string or a DistanceMatrixInput object.

    Parameters
    ----------
    input_contract : DistanceMatrixInput | str
        The input contract containing the necessary information to compute
        the distance matrix. It can be a JSON string or a DistanceMatrixInput
        object.

    Returns
    -------
    DistanceMatrixOutput
        An object containing the results of the distance matrix computation,
        including status, input directory, total files analyzed, matrix dimensions,
        metric used, compressor used, and output file path.

    Examples
    --------
    >>> input_contract = DistanceMatrixInput(
    ...     input_directory="path/to/files",
    ...     metric_strategy=MetricStrategy(
    ...         algorithm=AlgorithmType.NCD,
    ...         compressor=Compressor.GZIP,
    ...         compression_level=9
    ...     ),
    ...     output_destination="path/to/output.csv"
    ... )

        with JSON input:

    >>> input_contract = {
    ...     "input_directory": "path/to/files",
    ...     "metric_strategy": {
    ...         "algorithm": "ncd",
    ...         "compressor": "gzip",
    ...         "compression_level": 9
    ...     },
    ...     "output_destination": "path/to/output.csv"
    ... }

    >>> compute_distance_matrix(input_contract)
    DistanceMatrixOutput(
        status=StatusType.SUCCESS,
        input_directory="path/to/files",
        total_files_analyzed=10,
        matrix_dimensions="10x10",
        metric_used="ncd",
        compressor_used="gzip",
        output_file_path="path/to/output.csv"
    )
    """
    if isinstance(input_contract, str):
        input_data = DistanceMatrixInput.model_validate_json(input_contract)
    else:
        input_data = input_contract

    match input_data.metric_strategy.algorithm:
        case AlgorithmType.NCD:
            matrix, filenames = ncd_matrix(
                input_data.input_directory,
                input_data.metric_strategy.compressor,
                input_data.metric_strategy.compression_level,
            )

            export_ncd_to_csv(matrix, filenames, input_data.output_destination)

            return DistanceMatrixOutput(
                status=StatusType.SUCCESS,
                input_directory=input_data.input_directory,
                total_files_analyzed=len(filenames),
                matrix_dimensions=f"{matrix.shape[0]}x{matrix.shape[1]}",
                metric_used=input_data.metric_strategy.algorithm.value,
                compressor_used=input_data.metric_strategy.compressor.value,
                output_file_path=input_data.output_destination,
            )
        case _:
            raise NotImplementedError(
                f"Algorithm {input_data.metric_strategy.algorithm} not implemented."
            )
