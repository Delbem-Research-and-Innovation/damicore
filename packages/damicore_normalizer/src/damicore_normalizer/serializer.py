from __future__ import annotations

import json
from collections.abc import Sequence


def serialize_cell(value: str) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def serialize_row(values: Sequence[str]) -> bytes:
    return (json.dumps(list(values), ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
