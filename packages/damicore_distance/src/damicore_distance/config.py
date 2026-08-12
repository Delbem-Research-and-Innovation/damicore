from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DistanceConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    compressor: Literal["zlib", "gzip"] = "zlib"
    compression_level: int = Field(default=6, ge=0, le=9)
    compression_chunk_bytes: int = Field(default=4_194_304, gt=0)
    workers: int | Literal["auto"] = "auto"
    pairs_per_shard: int = Field(default=10_000, gt=0)
    resume: bool = True
    save_diagnostics: bool = False

    @field_validator("workers")
    @classmethod
    def _validate_workers(cls, value: int | str) -> int | str:
        if isinstance(value, int) and value < 1:
            raise ValueError("workers must be at least one")
        return value

    @property
    def effective_workers(self) -> int:
        if isinstance(self.workers, int):
            return self.workers
        return min(4, max(1, (os.cpu_count() or 1) - 1))
