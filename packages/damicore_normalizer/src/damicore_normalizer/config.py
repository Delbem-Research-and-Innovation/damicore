from __future__ import annotations

import codecs
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NormalizationConfig(BaseModel):
    """Configuration for deterministic CSV normalization."""

    model_config = ConfigDict(frozen=True)

    split: Literal["columns", "rows"] = "columns"
    delimiter: str = ","
    encoding: str = "utf-8"
    chunk_rows: int = Field(default=50_000, gt=0)
    max_open_files: int = Field(default=64, gt=0)

    @field_validator("delimiter")
    @classmethod
    def _validate_delimiter(cls, value: str) -> str:
        if len(value) != 1:
            raise ValueError("delimiter must contain exactly one Unicode character")
        return value

    @field_validator("encoding")
    @classmethod
    def _validate_encoding(cls, value: str) -> str:
        codecs.lookup(value)
        return value
