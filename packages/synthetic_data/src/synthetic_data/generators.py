"""Per-column-type value generators.

Every generator factory returns a callable ``(rng: random.Random) -> object``
so the whole dataset can be produced from one seeded ``random.Random``
instance, threaded through by the engine (see ``synthetic_data.engine``).
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Sequence
from random import Random
from typing import Any

Generator = Callable[[Random], Any]


def sequential_natural(start: int = 0) -> Generator:
    """A natural number counting up from ``start`` on every call."""
    counter = itertools.count(start)

    def _generate(_rng: Random) -> int:
        return next(counter)

    return _generate


def integer(low: int, high: int) -> Generator:
    """A signed integer uniformly sampled from ``[low, high]``."""

    def _generate(rng: Random) -> int:
        return rng.randint(low, high)

    return _generate


def natural(low: int, high: int) -> Generator:
    """A natural number uniformly sampled from ``[low, high]`` (``low`` should be >= 0).

    A semantically-named wrapper over :func:`integer` — same sampling
    behavior, single source of truth for "sample an int in range".
    """
    return integer(low, high)


def real(low: float, high: float, decimals: int = 6) -> Generator:
    """A real number uniformly sampled from ``[low, high]``."""

    def _generate(rng: Random) -> float:
        return round(rng.uniform(low, high), decimals)

    return _generate


def scientific_real(min_magnitude: float, max_magnitude: float) -> Generator:
    """A signed real whose magnitude is log-uniform in ``[min_magnitude, max_magnitude]``.

    Produces values spanning many orders of magnitude, exercising
    scientific-notation-adjacent parsing.
    """
    log_low = math.log10(min_magnitude)
    log_high = math.log10(max_magnitude)

    def _generate(rng: Random) -> float:
        magnitude = 10 ** rng.uniform(log_low, log_high)
        sign = rng.choice([-1, 1])
        return sign * magnitude

    return _generate


def categorical(values: Sequence[str], weights: Sequence[float] | None = None) -> Generator:
    """A category sampled from ``values``, optionally skewed by ``weights``."""

    def _generate(rng: Random) -> str:
        return rng.choices(values, weights=weights, k=1)[0]

    return _generate


def free_text(
    wordlist: Sequence[str],
    min_words: int,
    max_words: int,
    words_per_sentence: tuple[int, int] | None = None,
) -> Generator:
    """Word-salad free text sampled from ``wordlist``.

    When ``words_per_sentence`` is given, words are grouped into
    capitalized, period-terminated chunks to look sentence-like without any
    grammar/NLP dependency.
    """

    def _generate(rng: Random) -> str:
        n_words = rng.randint(min_words, max_words)
        words = [rng.choice(wordlist) for _ in range(n_words)]
        if words_per_sentence is None:
            return " ".join(words)

        sentences: list[str] = []
        index = 0
        while index < len(words):
            span = rng.randint(*words_per_sentence)
            chunk = words[index : index + span]
            if not chunk:
                # A zero-length span (e.g. words_per_sentence=(0, ...)) would
                # otherwise loop forever: `index` never advances past an empty
                # chunk. Stop instead of hanging.
                break
            chunk[0] = chunk[0].capitalize()
            sentences.append(" ".join(chunk) + ".")
            index += span
        return " ".join(sentences)

    return _generate


def sparse(inner: Generator, missing_rate: float, missing_value: str = "") -> Generator:
    """Wrap ``inner`` so it returns ``missing_value`` with probability ``missing_rate``."""

    def _generate(rng: Random) -> Any:
        if rng.random() < missing_rate:
            return missing_value
        return inner(rng)

    return _generate
