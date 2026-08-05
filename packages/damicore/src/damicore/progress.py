from __future__ import annotations

from collections.abc import Callable

from damicore_distance.api import ProgressCallback
from tqdm.auto import tqdm


def distance_progress(
    enabled: bool,
) -> tuple[ProgressCallback | None, Callable[[], None]]:
    if not enabled:
        return None, lambda: None
    bar = tqdm(total=0, unit="pair", desc="distance")

    def update(completed: int, total: int, message: str) -> None:  # noqa: ARG001
        del message  # the bar renders its own description
        bar.total = total
        bar.n = completed
        bar.refresh()

    return update, bar.close
