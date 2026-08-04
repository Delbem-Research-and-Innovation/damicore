from __future__ import annotations

from typing import Any


class TreeBuilderError(Exception):
    def __init__(self, message: str, *, code: str = "tree_builder_error", **context: Any) -> None:
        super().__init__(message)
        self.code = code
        self.context = context
