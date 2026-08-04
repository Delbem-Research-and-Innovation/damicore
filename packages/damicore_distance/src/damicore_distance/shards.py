from __future__ import annotations

from collections.abc import Iterator


def iter_pair_shards(
    object_count: int,
    pairs_per_shard: int,
) -> Iterator[tuple[int, list[tuple[int, int]]]]:
    shard: list[tuple[int, int]] = []
    shard_index = 0
    for left in range(object_count):
        for right in range(left + 1, object_count):
            shard.append((left, right))
            if len(shard) == pairs_per_shard:
                yield shard_index, shard
                shard_index += 1
                shard = []
    if shard:
        yield shard_index, shard
