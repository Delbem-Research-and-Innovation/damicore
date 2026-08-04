from __future__ import annotations

from damicore_distance.errors import DistanceError


def normalized_compression_distance(cx: int, cy: int, cxy: int) -> float:
    denominator = max(cx, cy)
    if denominator == 0:
        raise DistanceError("NCD denominator is zero", code="distance_computation_error")
    return (cxy - min(cx, cy)) / denominator
