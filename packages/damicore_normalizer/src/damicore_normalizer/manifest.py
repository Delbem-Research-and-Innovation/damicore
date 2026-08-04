from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ObjectDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    object_id: str
    label: str
    relative_path: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("relative_path")
    @classmethod
    def _relative_path_is_contained(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("relative_path must be a contained POSIX path")
        return value


class NormalizationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    delimiter: str = Field(min_length=1, max_length=1)
    encoding: str
    split: Literal["columns", "rows"]


class NormalizationManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[1]
    input: NormalizationInput
    objects: tuple[ObjectDescriptor, ...]


class NormalizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    manifest_path: Path
    object_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    objects: tuple[ObjectDescriptor, ...]
