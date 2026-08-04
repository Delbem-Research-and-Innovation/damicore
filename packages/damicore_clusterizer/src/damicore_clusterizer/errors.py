from __future__ import annotations

from typing import Any


class ClusterizerError(Exception):
    def __init__(self, message: str, *, code: str = "clusterizer_error", **context: Any) -> None:
        super().__init__(message)
        self.code = code
        self.context = context
