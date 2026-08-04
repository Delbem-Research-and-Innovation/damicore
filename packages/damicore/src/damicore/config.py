from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResourceLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_objects: int = Field(default=1_000, gt=0)
    max_pairs: int = Field(default=500_000, gt=0)
    max_matrix_bytes: int = Field(default=536_870_912, gt=0)
    max_working_memory_bytes: int = Field(default=536_870_912, gt=0)
    required_free_disk_factor: float = Field(default=1.25, ge=1.0)


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    workers: int | Literal["auto"] = "auto"
    csv_chunk_rows: int = Field(default=50_000, gt=0)
    compression_chunk_bytes: int = Field(default=4_194_304, gt=0)
    pairs_per_shard: int = Field(default=10_000, gt=0)
    resume: bool = True
    reuse_completed: bool = True
    pandas_materialization_limit_bytes: int = Field(default=268_435_456, gt=0)
    limits: ResourceLimits = Field(default_factory=ResourceLimits)

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
