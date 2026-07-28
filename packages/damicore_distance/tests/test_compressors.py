import pytest

from damicore_distance.compressors import Compressor, get_compressed_size

_COMPRESSIBLE = b"a" * 1000


@pytest.mark.unit
def test_get_compressed_size_returns_positive_integer() -> None:
    result = get_compressed_size(_COMPRESSIBLE, Compressor.GZIP)
    assert result > 0


@pytest.mark.unit
def test_get_compressed_size_level_9_smaller_than_level_1() -> None:
    size_level_1 = get_compressed_size(_COMPRESSIBLE, Compressor.GZIP, compression_level=1)
    size_level_9 = get_compressed_size(_COMPRESSIBLE, Compressor.GZIP, compression_level=9)
    assert size_level_9 < size_level_1


@pytest.mark.unit
def test_get_compressed_size_raises_for_unsupported_compressor() -> None:
    with pytest.raises(ValueError, match="Unsupported compressor"):
        get_compressed_size(b"data", "bzip2")  # type: ignore[arg-type]
