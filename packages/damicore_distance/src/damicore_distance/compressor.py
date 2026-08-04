from __future__ import annotations

import zlib
from collections.abc import Iterable
from pathlib import Path

from damicore_distance.errors import DistanceError


def compressed_size(paths: Iterable[Path], *, compressor: str, level: int, chunk_bytes: int) -> int:
    wbits = zlib.MAX_WBITS if compressor == "zlib" else 31
    stream = zlib.compressobj(level=level, wbits=wbits)
    total = 0
    try:
        for path in paths:
            with path.open("rb") as source:
                while chunk := source.read(chunk_bytes):
                    total += len(stream.compress(chunk))
        total += len(stream.flush())
    except OSError as exc:
        raise DistanceError(f"Could not compress object: {exc}", code="compression_error") from exc
    return total
