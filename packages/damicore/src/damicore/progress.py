from __future__ import annotations

from collections.abc import Callable

from tqdm.auto import tqdm


def distance_progress(
    enabled: bool,
) -> tuple[Callable[[int, int, str], None] | None, Callable[[], None]]:
    if not enabled:
        return None, lambda: None
    bar = tqdm(total=0, unit="pair", desc="distance")

    def update(completed: int, total: int, _message: str) -> None:
        bar.total = total
        bar.n = completed
        bar.refresh()

    return update, bar.close
