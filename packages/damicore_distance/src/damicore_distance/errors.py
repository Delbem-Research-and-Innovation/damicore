from __future__ import annotations


class DistanceError(Exception):
    def __init__(self, message: str, *, code: str = "distance_error", **context: object) -> None:
        super().__init__(message)
        self.code = code
        self.context = context
