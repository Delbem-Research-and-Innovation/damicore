import gzip
from enum import StrEnum


class Compressor(StrEnum):
    GZIP = "gzip"


def get_compressed_size(data: bytes, compressor: Compressor, compression_level: int = 9) -> int:
    """
    Get the size of the compressed data for a given file using the specified compressor.

    Parameters
    ----------
        data : bytes
            The data to be compressed.
        compressor : Compressor
            The compressor to use for compression.
        compression_level : int, optional
            1 for fastest, 9 for best compression. Defaults to 9.

    Returns
    -------
        int
            The size of the compressed data in bytes.

    Raises
    ------
        ValueError
            If the specified compressor is not supported.
    """
    match compressor:
        case Compressor.GZIP:
            return len(gzip.compress(data, compresslevel=compression_level))
        case _:
            raise ValueError(f"Unsupported compressor: {compressor}")
