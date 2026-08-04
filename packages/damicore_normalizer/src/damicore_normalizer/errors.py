from __future__ import annotations


class NormalizerError(Exception):
    """Base error raised by the standalone normalizer package."""

    def __init__(self, message: str, *, code: str = "normalizer_error", **context: object) -> None:
        super().__init__(message)
        self.code = code
        self.context = context
